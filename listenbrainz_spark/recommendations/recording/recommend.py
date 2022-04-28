"""
This script is responsible for generating recommendations for the users. The general flow is as follows:

The best_model saved in HDFS is loaded with the help of model_id which is fetched from model_metadata_df.
`spark_user_id` and `recording_id` are fetched from top_artist_candidate_set_df and are given as input to the
recommender. An RDD of `user`, `product` and `rating` is returned from the recommender which is later converted to
a dataframe by filtering top X (an int supplied as an argument to the script) recommendations for all users sorted on rating
and fields renamed as `spark_user_id`, `recording_id` and `rating`. The ratings are scaled so that they lie between 0 and 1.
This dataframe is joined with recordings_df on recording_id to get the recording mbids which are then sent over the queue.

The same process is done for similar artist candidate set.
"""

import logging
import time

import pyspark.sql
import pyspark.sql.functions as func
from py4j.protocol import Py4JJavaError
from pyspark.ml.recommendation import ALSModel
from pyspark.sql.functions import col, row_number
from pyspark.sql.types import DoubleType
from pyspark.sql.window import Window

import listenbrainz_spark
from listenbrainz_spark import utils, path
from listenbrainz_spark.exceptions import (PathNotFoundException,
                                           FileNotFetchedException,
                                           SparkSessionNotInitializedException,
                                           RecommendationsNotGeneratedException,
                                           EmptyDataframeExcpetion)
from listenbrainz_spark.recommendations.recording.candidate_sets import _is_empty_dataframe
from listenbrainz_spark.recommendations.recording.train_models import get_model_path

logger = logging.getLogger(__name__)


class RecommendationParams:

    def __init__(self, recordings_df, model_id, model_html_file, model, top_artist_candidate_set_df,
                 similar_artist_candidate_set_df, recommendation_top_artist_limit, recommendation_similar_artist_limit):
        self.recordings_df = recordings_df
        self.model_id = model_id
        self.model_html_file = model_html_file
        self.model = model
        self.top_artist_candidate_set_df = top_artist_candidate_set_df
        self.similar_artist_candidate_set_df = similar_artist_candidate_set_df
        self.recommendation_top_artist_limit = recommendation_top_artist_limit
        self.recommendation_similar_artist_limit = recommendation_similar_artist_limit


def get_most_recent_model_meta():
    """ Get model id of recently created model.

        Returns:
            model_id (str): Model identification string.
    """
    utils.read_files_from_HDFS(path.RECOMMENDATION_RECORDING_MODEL_METADATA).createOrReplaceTempView("model_metadata")
    meta = listenbrainz_spark.sql_context.sql("""
        SELECT model_id, model_html_file
          FROM model_metadata
      ORDER BY model_created DESC
         LIMIT 1
    """).collect()[0]
    return meta.model_id, meta.model_html_file


def load_model(model_id):
    """ Load model from given path in HDFS.
    """
    dest_path = get_model_path(model_id)
    try:
        return ALSModel.load(dest_path)
    except Py4JJavaError as err:
        logger.error('Unable to load model "{}"\n{}\nAborting...'.format(model_id, str(err.java_exception)),
                                 exc_info=True)
        raise


def get_recording_mbids(params: RecommendationParams, recommendation_df, users_df):
    """ Get recording mbids corresponding to recommended recording ids sorted on rating.

        Args:
            params: RecommendationParams class object.
            recommendation_df: Dataframe of spark_user_id, recording id and rating.
            users_df : user_id and spark_user_id of active users.

        Returns:
            dataframe of recommended recording mbids and related info.
    """
    df = params.recordings_df.join(recommendation_df, 'recording_id', 'inner') \
                             .select('rating',
                                     'recording_mbid',
                                     'spark_user_id')

    recording_mbids_df = df.join(users_df, 'spark_user_id', 'inner')

    window = Window.partitionBy('user_id').orderBy(col('rating').desc())

    df = recording_mbids_df.withColumn('rank', row_number().over(window)) \
                           .select('recording_mbid',
                                   'rank',
                                   'rating',
                                   'spark_user_id',
                                   'user_id')

    return df


def filter_recommendations_on_rating(df, limit):
    """ Filter top X recommendations for each user on rating where X = limit.

        Args:
            df: Dataframe of user, product and rating.
            limit (int): Number of recommendations to be filtered for each user.

        Returns:
            recommendation_df: Dataframe of spark_user_id, recording_id and rating.
    """
    window = Window.partitionBy('spark_user_id').orderBy(col('prediction').desc())

    recommendation_df = df.withColumn('rank', row_number().over(window)) \
                          .where(col('rank') <= limit) \
                          .select(col('prediction').alias('rating'),
                                  col('recording_id'),
                                  col('spark_user_id'))

    return recommendation_df


def generate_recommendations(candidate_set, params: RecommendationParams, limit):
    """ Generate recommendations from the candidate set.

        Args:
            candidate_set (rdd): RDD of spark_user_id and recording_id.
            params: RecommendationParams class object.
            limit (int): Number of recommendations to be filtered for each user.

        Returns:
            recommendation_df: Dataframe of spark_user_id, recording_id and rating.
    """
    recommendations = params.model.transform(candidate_set)

    if _is_empty_dataframe(recommendations):
        raise RecommendationsNotGeneratedException('Recommendations not generated!')

    recommendation_df = filter_recommendations_on_rating(recommendations, limit)

    return recommendation_df


def get_scale_rating_udf(rating):
    """ Get user defined function (udf) to scale ratings so that they fall in the
        range: 0.0 -> 1.0.

        Args:
            rating (float): score given to recordings by CF.

        Returns:
            rating udf.
    """
    scaled_rating = (rating / 2.0) + 0.5

    return round(min(max(scaled_rating, -1.0), 1.0), 3)


def scale_rating(df: pyspark.sql.DataFrame):
    """ Scale the ratings column of dataframe so that they fall in the
        range: 0.0 -> 1.0.

        Args:
            df: Dataframe to scale.

        Returns:
            df: Dataframe with scaled rating.
    """
    scaling_udf = func.udf(get_scale_rating_udf, DoubleType())

    df = df.withColumn("scaled_rating", scaling_udf(df.rating)) \
           .select(col('recording_id'),
                   col('spark_user_id'),
                   col('scaled_rating').alias('rating'))

    return df


def get_candidate_set_rdd_for_user(candidate_set_df, users):
    """ Get candidate set RDD for a given user.

        Args:
            candidate_set_df: A dataframe of spark_user_id and recording_id for all users.
            users: list of user names to generate recommendations for.

        Returns:
            candidate_set_rdd: An RDD of spark_user_id and recording_id for a given user.
    """
    if users:
        candidate_set_user_df = candidate_set_df.select('spark_user_id', 'recording_id') \
                                                .where(col('user_id').isin(users))
    else:
        candidate_set_user_df = candidate_set_df.select('spark_user_id', 'recording_id')

    if _is_empty_dataframe(candidate_set_user_df):
        raise EmptyDataframeExcpetion('Empty Candidate sets!')

    return candidate_set_user_df


def get_user_name_and_user_id(params: RecommendationParams, users):
    """ Get users from top artist candidate set.

        Args:
            params: RecommendationParams class object.
            users = list of users names to generate recommendations.

        Returns:
            users_df: dataframe of user id and user names.
    """
    if len(users) == 0:
        users_df = params.top_artist_candidate_set_df.select('spark_user_id', 'user_id').distinct()

    else:
        users_df = params.top_artist_candidate_set_df.select('spark_user_id', 'user_id') \
                                                     .where(params.top_artist_candidate_set_df.user_id.isin(users)) \
                                                     .distinct()

    if _is_empty_dataframe(users_df):
        raise EmptyDataframeExcpetion('No active users found!')

    return users_df


def check_for_ratings_beyond_range(top_artist_rec_df, similar_artist_rec_df):
    """ Check if rating in top_artist_rec_df and similar_artist_rec_df does not belong to [-1, 1].

        Args:
            top_artist_rec_df (dataframe): Top artist recommendations for all users.
            similar_artist_rec_df (dataframe): Similar artist recommendations for all users.

        Returns:
            a tuple of booleans (max out of range, min out of range)
    """
    max_rating = top_artist_rec_df.select(func.max('rating').alias('rating')).take(1)[0].rating

    max_rating = max(similar_artist_rec_df.select(func.max('rating').alias('rating')).take(1)[0].rating, max_rating)

    min_rating = top_artist_rec_df.select(func.min('rating').alias('rating')).take(1)[0].rating

    min_rating = min(similar_artist_rec_df.select(func.min('rating').alias('rating')).take(1)[0].rating, min_rating)

    if max_rating > 1.0:
        logger.info('Some ratings are greater than 1 \nMax rating: {}'.format(max_rating))

    if min_rating < -1.0:
        logger.info('Some ratings are less than -1 \nMin rating: {}'.format(min_rating))

    return max_rating > 1.0, min_rating < -1.0


def create_messages(params, top_artist_rec_mbid_df, similar_artist_rec_mbid_df, active_user_count,
                    total_time, top_artist_rec_user_count, similar_artist_rec_user_count):
    """ Create messages to send the data to the webserver via RabbitMQ.

        Args:
            params: recommendation params to get model id and model url from
            top_artist_rec_mbid_df (dataframe): Top artist recommendations.
            similar_artist_rec_mbid_df (dataframe): Similar artist recommendations.
            active_user_count (int): Number of users active in the last week.
            total_time (float): Time taken in exceuting the whole script.
            top_artist_rec_user_count (int): Number of users for whom top artist recommendations were generated.
            similar_artist_rec_user_count (int): Number of users for whom similar artist recommendations were generated.

        Returns:
            messages: A list of messages to be sent via RabbitMQ
    """
    top_artist_rec_itr = top_artist_rec_mbid_df.toLocalIterator()

    user_rec = {}

    for row in top_artist_rec_itr:

        if user_rec.get(row.user_id) is None:
            user_rec[row.user_id] = {}

            user_rec[row.user_id]['top_artist'] = [
                {
                    "recording_mbid": row.recording_mbid,
                    "score": row.rating
                }
            ]
            user_rec[row.user_id]['similar_artist'] = []

        else:
            user_rec[row.user_id]['top_artist'].append(
                    {
                        "recording_mbid": row.recording_mbid,
                        "score": row.rating
                    }
            )

    similar_artist_rec_itr = similar_artist_rec_mbid_df.toLocalIterator()

    for row in similar_artist_rec_itr:

        if user_rec.get(row.user_id) is None:
            user_rec[row.user_id] = {}
            user_rec[row.user_id]['similar_artist'] = [
                {
                    "recording_mbid": row.recording_mbid,
                    "score": row.rating
                }
            ]

        else:
            user_rec[row.user_id]['similar_artist'].append(
                    {
                        "recording_mbid": row.recording_mbid,
                        "score": row.rating
                    }
            )

    for user_id, data in user_rec.items():
        messages = {
            'user_id': user_id,
            'type': 'cf_recommendations_recording_recommendations',
            'recommendations': {
                'top_artist': data.get('top_artist', []),
                'similar_artist': data.get('similar_artist', []),
                'model_id': params.model_id,
                'model_url': f"http://michael.metabrainz.org/{params.model_html_file}"
            }
        }
        yield messages

    yield {
            'type': 'cf_recommendations_recording_mail',
            'active_user_count': active_user_count,
            'top_artist_user_count': top_artist_rec_user_count,
            'similar_artist_user_count': similar_artist_rec_user_count,
            'total_time': '{:.2f}'.format(total_time / 3600)
    }


def get_recommendations_for_all(params: RecommendationParams, users):
    """ Get recommendations for all active users.

        Args:
            params: RecommendationParams class object.
            users = list of users names to generate recommendations.

        Returns:
            top_artist_rec_df: Top artist recommendations.
            similar_artist_rec_df: Similar artist recommendations.
    """
    try:
        top_artist_candidate_set_rdd = get_candidate_set_rdd_for_user(params.top_artist_candidate_set_df, users)
    except EmptyDataframeExcpetion:
        logger.error('Top artist candidate set not found for any user.', exc_info=True)
        raise

    try:
        similar_artist_candidate_set_rdd = get_candidate_set_rdd_for_user(params.similar_artist_candidate_set_df, users)
    except EmptyDataframeExcpetion:
        logger.error('Similar artist candidate set not found for any user.', exc_info=True)
        raise

    try:
        top_artist_rec_df = generate_recommendations(top_artist_candidate_set_rdd, params,
                                                     params.recommendation_top_artist_limit)
    except RecommendationsNotGeneratedException:
        logger.error('Top artist recommendations not generated for any user', exc_info=True)
        raise

    try:
        similar_artist_rec_df = generate_recommendations(similar_artist_candidate_set_rdd, params,
                                                         params.recommendation_similar_artist_limit)
    except RecommendationsNotGeneratedException:
        logger.error('Similar artist recommendations not generated for any user', exc_info=True)
        raise

    return top_artist_rec_df, similar_artist_rec_df


def get_user_count(df):
    """ Get distinct user count from the given dataframe.
    """
    users_df = df.select('spark_user_id').distinct()
    return users_df.count()


def main(recommendation_top_artist_limit=None, recommendation_similar_artist_limit=None, users=None):

    try:
        listenbrainz_spark.init_spark_session('Recommendations')
    except SparkSessionNotInitializedException as err:
        logger.error(str(err), exc_info=True)
        raise

    try:
        recordings_df = utils.read_files_from_HDFS(path.RECOMMENDATION_RECORDINGS_DATAFRAME)
        top_artist_candidate_set_df = utils.read_files_from_HDFS(path.RECOMMENDATION_RECORDING_TOP_ARTIST_CANDIDATE_SET)
        similar_artist_candidate_set_df = utils.read_files_from_HDFS(path.RECOMMENDATION_RECORDING_SIMILAR_ARTIST_CANDIDATE_SET)
    except PathNotFoundException as err:
        logger.error(str(err), exc_info=True)
        raise
    except FileNotFetchedException as err:
        logger.error(str(err), exc_info=True)
        raise

    logger.info('Loading model...')
    model_id, model_html_file = get_most_recent_model_meta()
    model = load_model(model_id)

    # an action must be called to persist data in memory
    recordings_df.count()
    recordings_df.persist()

    params = RecommendationParams(recordings_df, model_id, model_html_file, model,
                                  top_artist_candidate_set_df, similar_artist_candidate_set_df,
                                  recommendation_top_artist_limit, recommendation_similar_artist_limit)

    try:
        # timestamp when the script was invoked
        ts_initial = time.monotonic()
        users_df = get_user_name_and_user_id(params, users)
        # Some users are excluded from the top_artist_candidate_set because of the limited data
        # in the mapping. Therefore, active_user_count may or may not be equal to number of users
        # active in the last week. Ideally, top_artist_candidate_set should give the active user count.
        active_user_count = users_df.count()
        users_df.persist()
        logger.info('Took {:.2f}sec to get active user count'.format(time.monotonic() - ts_initial))
    except EmptyDataframeExcpetion as err:
        logger.error(str(err), exc_info=True)
        raise

    logger.info('Generating recommendations...')
    ts = time.monotonic()
    top_artist_rec_df, similar_artist_rec_df = get_recommendations_for_all(params, users)
    logger.info('Recommendations generated!')
    logger.info('Took {:.2f}sec to generate recommendations for all active users'.format(time.monotonic() - ts))

    ts = time.monotonic()
    top_artist_rec_user_count = get_user_count(top_artist_rec_df)
    similar_artist_rec_user_count = get_user_count(similar_artist_rec_df)
    logger.info('Took {:.2f}sec to get top artist and similar artist user count'.format(time.monotonic() - ts))

    ts = time.monotonic()
    check_for_ratings_beyond_range(top_artist_rec_df, similar_artist_rec_df)

    top_artist_rec_scaled_df = scale_rating(top_artist_rec_df)
    similar_artist_rec_scaled_df = scale_rating(similar_artist_rec_df)
    logger.info('Took {:.2f}sec to scale the ratings'.format(time.monotonic() - ts))

    ts = time.monotonic()
    top_artist_rec_mbid_df = get_recording_mbids(params, top_artist_rec_scaled_df, users_df)
    similar_artist_rec_mbid_df = get_recording_mbids(params, similar_artist_rec_scaled_df, users_df)
    logger.info('Took {:.2f}sec to get mbids corresponding to recording ids'.format(time.monotonic() - ts))

    # persisted data must be cleared from memory after usage to avoid OOM
    recordings_df.unpersist()

    total_time = time.monotonic() - ts_initial
    logger.info('Total time: {:.2f}sec'.format(total_time))

    result = create_messages(params, top_artist_rec_mbid_df, similar_artist_rec_mbid_df, active_user_count,
                             total_time, top_artist_rec_user_count, similar_artist_rec_user_count)

    users_df.unpersist()

    return result
