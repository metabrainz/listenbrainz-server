import logging
import time
from datetime import datetime
from collections import defaultdict
from py4j.protocol import Py4JJavaError

import listenbrainz_spark
from listenbrainz_spark import config, utils, path

from listenbrainz_spark.exceptions import (PathNotFoundException,
                                           FileNotFetchedException,
                                           ViewNotRegisteredException,
                                           SparkSessionNotInitializedException,
                                           RecommendationsNotGeneratedException,
                                           RatingOutOfRangeException)

from listenbrainz_spark.recommendations.train_models import get_model_path
from listenbrainz_spark.recommendations.candidate_sets import _is_empty_dataframe

from pyspark.sql import Row
from flask import current_app
import pyspark.sql.functions as func
from pyspark.sql.window import Window
from pyspark.sql.functions import col, udf, row_number
from pyspark.sql.types import DoubleType
from pyspark.mllib.recommendation import MatrixFactorizationModel


class RecommendationParams:

    def __init__(self, recordings_df, model, top_artist_candidate_set_df, similar_artist_candidate_set_df,
                 recommendation_top_artist_limit, recommendation_similar_artist_limit):
        self.recordings_df = recordings_df
        self.model = model
        self.top_artist_candidate_set_df = top_artist_candidate_set_df
        self.similar_artist_candidate_set_df = similar_artist_candidate_set_df
        self.recommendation_top_artist_limit = recommendation_top_artist_limit
        self.recommendation_similar_artist_limit = recommendation_similar_artist_limit
        self.ratings_beyond_range = []
        self.similar_artist_not_found = []
        self.top_artist_not_found = []
        self.top_artist_rec_not_generated = []
        self.similar_artist_rec_not_generated = []


def get_most_recent_model_id():
    """ Get model id of recently created model.

        Returns:
            model_id (str): Model identification string.
    """
    try:
        model_metadata = utils.read_files_from_HDFS(path.MODEL_METADATA)
    except PathNotFoundException as err:
        current_app.logger.error(str(err), exc_info=True)
        raise
    except FileNotFetchedException as err:
        current_app.logger.error(str(err), exc_info=True)
        raise

    latest_ts = model_metadata.select(func.max('model_created').alias('model_created')).take(1)[0].model_created
    model_id = model_metadata.select('model_id') \
                             .where(col('model_created') == latest_ts).take(1)[0].model_id

    return model_id


def load_model():
    """ Load model from given path in HDFS.
    """
    model_id = get_most_recent_model_id()
    dest_path = get_model_path(model_id)
    try:
        model = MatrixFactorizationModel.load(listenbrainz_spark.context, dest_path)
        return model
    except Py4JJavaError as err:
        current_app.logger.error('Unable to load model "{}"\n{}\nAborting...'.format(model_id, str(err.java_exception)),
                                 exc_info=True)
        raise


def get_recording_mbids(params: RecommendationParams, recommendation_df, users_df):
    """ Get recording mbids corresponding to recommended recording ids sorted on rating.

        Args:
            params: RecommendationParams class object.
            recommendation_df: Dataframe of recommended recording ids and corresponding ratings.
            users_df : user_name and user_id of active users.

        Returns:
            dataframe of recommended recording mbids and related info.
    """
    df = params.recordings_df.join(recommendation_df, 'recording_id', 'inner') \
                                             .select('rating',
                                                     'mb_recording_mbid',
                                                     'user_id')

    recording_mbids_df = df.join(users_df, 'user_id', 'inner')

    window = Window.partitionBy('user_name').orderBy(col('rating').desc())

    df = recording_mbids_df.withColumn('rank', row_number().over(window))

    return df


def get_recommendations(candidate_set, params: RecommendationParams, limit):
    """ Generate recommendations from the candidate set.

        Args:
            candidate_set (rdd): RDD of user_id and recording_id.
            params: RecommendationParams class object.
            limit (int): Number of recommendations to be generated.

        Returns:
            df: dataframe of user, product and rating
    """
    recommendations = params.model.predictAll(candidate_set).takeOrdered(limit, lambda product: -product.rating)

    if len(recommendations) == 0:
        raise RecommendationsNotGeneratedException('Recommendations not generated!')

    df = listenbrainz_spark.session.createDataFrame(recommendations, schema=None)

    return df


def get_scale_rating_udf(rating):
    """ Get user defined function (udf) to scale ratings so that they fall in the
        range: 0.0 -> 1.0.

        Args:
            rating (float): score given to recordings by CF.
    """
    scaled_rating = (rating / 2.0) + 0.5

    return round(min(max(scaled_rating, -1.0), 1.0), 3)


def scale_rating(df):
    """ Scale the ratings column of dataframe so that they fall in the
        range: 0.0 -> 1.0.

        Args:
            df: Dataframe to scale.

        Returns:
            df: Dataframe with scaled column.
    """
    scaling_udf = udf(get_scale_rating_udf, DoubleType())

    df = df.withColumn("scaled_rating", scaling_udf(df.rating)) \
           .select(col('product').alias('recording_id'),
                   col('user').alias('user_id'),
                   col('scaled_rating').alias('rating'))

    return df


def get_candidate_set_rdd_for_user(candidate_set_df, user_id):
    """ Get candidate set RDD for a given user.

        Args:
            candidate_set_df: A dataframe of user_id and recording_id for all users.
            user_id (int): user id of the user.

        Returns:
            candidate_set_rdd: An RDD of user_id and recording_id for a given user.
    """
    candidate_set_user_df = candidate_set_df.select('user_id', 'recording_id') \
                                            .where(col('user_id') == user_id)

    if _is_empty_dataframe(candidate_set_user_df):
        raise IndexError

    candidate_set_rdd = candidate_set_user_df.rdd.map(lambda r: (r['user_id'], r['recording_id']))

    return candidate_set_rdd


def get_recommendations_for_user(user_id, user_name, params: RecommendationParams):
    """ Get recommended recordings which belong to top artists and artists similar to top
        artists listened to by the user.

        Args:
            user_id (int): user id of the user.
            user_name (str): User name of the user.
            params: RecommendationParams class object.

        Returns:
            top_artist_rec_user_df: dataframe of recommended recordings of top artist.
            imilar_artist_rec_user_df: dataframe of recommended recordings of similar artist.
    """
    ts = time.monotonic()
    top_artist_rec_user_df = None
    try:
        top_artist_candidate_set_user = get_candidate_set_rdd_for_user(params.top_artist_candidate_set_df, user_id)
        top_artist_rec_user_df = get_recommendations(top_artist_candidate_set_user, params,
                                                     params.recommendation_top_artist_limit)

        current_app.logger.info('{} listens in top artist candidate set for {}'
                                .format(top_artist_candidate_set_user.count(), user_name))
        current_app.logger.info('Took {:.2f}sec to generate top artist recommendations for {}'
                                .format(time.monotonic() - ts, user_name))
    except IndexError:
        params.top_artist_not_found.append(user_name)
    except RecommendationsNotGeneratedException:
        params.top_artist_rec_not_generated.append(user_name)

    ts = time.monotonic()
    similar_artist_rec_user_df = None
    try:
        similar_artist_candidate_set_user = get_candidate_set_rdd_for_user(params.similar_artist_candidate_set_df, user_id)
        similar_artist_rec_user_df = get_recommendations(similar_artist_candidate_set_user, params,
                                                         params.recommendation_similar_artist_limit)

        current_app.logger.info('{} listens in similar artist candidate set for {}'
                                .format(similar_artist_candidate_set_user.count(), user_name))
        current_app.logger.info('Took {:.2f}sec to generate similar artist recommendations for {}'
                                .format(time.monotonic() - ts, user_name))
    except IndexError:
        params.similar_artist_not_found.append(user_name)
    except RecommendationsNotGeneratedException:
        params.similar_artist_rec_not_generated.append(user_name)

    return top_artist_rec_user_df, similar_artist_rec_user_df


def get_user_name_and_user_id(params: RecommendationParams, users):
    """ Get users from top artist candidate set.

        Args:
            params: RecommendationParams class object.
            users = list of users names to generate recommendations.

        Returns:
            users_df: dataframe of user id and user names.
    """
    if len(users) == 0:
        users_df = params.top_artist_candidate_set_df.select('user_id', 'user_name').distinct()

    else:
        users_df = params.top_artist_candidate_set_df.select('user_id', 'user_name') \
                                                     .where(params.top_artist_candidate_set_df.user_name.isin(users)) \
                                                     .distinct()
    return users_df


def check_for_ratings_beyond_range(top_artist_rec_df, similar_artist_rec_df):
    """ Check if rating in top_artist_rec_df and similar_artist_rec_df does not belong to [-1, 1].

        Args:
            top_artist_rec_df (dataframe): Top artist recommendations for all users.
            similar_artist_rec_df (dataframe): Similar artist recommendations for all users.
    """
    max_rating = top_artist_rec_df.select(func.max('rating').alias('rating')).take(1)[0].rating

    max_rating = max(similar_artist_rec_df.select(func.max('rating').alias('rating')).take(1)[0].rating, max_rating)

    min_rating = top_artist_rec_df.select(func.min('rating').alias('rating')).take(1)[0].rating

    min_rating = max(similar_artist_rec_df.select(func.min('rating').alias('rating')).take(1)[0].rating, min_rating)

    if max_rating > 1.0:
        current_app.logger.error('Some ratings are greater than 1 \nMax rating: {}'.format(max_rating))

    if min_rating < -1.0:
        current_app.logger.error('Some ratings are less than -1 \nMin rating: {}'.format(min_rating))


def create_messages(top_artist_rec_df, similar_artist_rec_df, user_count, total_time):
    """ Create messages to send the data to the webserver via RabbitMQ.

        Args:
            top_artist_rec_df (dataframe): Top artist recommendations.
            similar_artist_rec_df (dataframe): Similar artist recommendations.
            user_count (int): Number of users for whom recommendations are generated.
            total_time (str): Time taken to generate recommendations.

        Returns:
            messages: A list of messages to be sent via RabbitMQ
    """

    top_artist_rec_itr = top_artist_rec_df.toLocalIterator()

    user_rec = {}

    for row in top_artist_rec_itr:

        if user_rec.get(row.user_name) is None:
            user_rec[row.user_name] = {}
            user_rec[row.user_name]['top_artist'] = [[row.mb_recording_mbid, row.rating]]
            user_rec[row.user_name]['similar_artist'] = []

        else:
            user_rec[row.user_name]['top_artist'].append([row.mb_recording_mbid, row.rating])

    similar_artist_rec_itr = similar_artist_rec_df.toLocalIterator()

    for row in similar_artist_rec_itr:

        if user_rec.get(row.user_name) is None:
            user_rec[row.user_name] = {}
            user_rec[row.user_name]['similar_artist'] = [[row.mb_recording_mbid, row.rating]]

        else:
            user_rec[row.user_name]['similar_artist'].append([row.mb_recording_mbid, row.rating])

    for user_name, data in user_rec.items():
        messages = {
            'musicbrainz_id': user_name,
            'type': 'cf_recording_recommendations',
            'top_artist': data.get('top_artist', []),
            'similar_artist': data.get('similar_artist', [])
        }
        yield messages

    yield {
            'type': 'cf_recording_recommendations_mail',
            'user_count': user_count,
            'total_time': '{:.2f}'.format(total_time / 3600)
    }


def get_recommendations_for_all(params: RecommendationParams, users):
    """ Get recommendations for all active users.

        Args:
            params: RecommendationParams class object.
            users = list of users names to generate recommendations.

        Returns:
            messages (list): user recommendations.
    """
    # users for whom recommendations will be generated.
    users_df = get_user_name_and_user_id(params, users)
    user_count = users_df.count()
    users_df.persist()

    top_artist_rec_df = None
    similar_artist_rec_df = None
    for row in users_df.collect():
        user_name = row.user_name
        user_id = row.user_id

        top_artist_rec_user_df, similar_artist_rec_user_df = get_recommendations_for_user(user_id, user_name, params)

        if top_artist_rec_user_df is not None:
            top_artist_rec_df = top_artist_rec_df.union(top_artist_rec_user_df) if top_artist_rec_df else top_artist_rec_user_df

        if similar_artist_rec_user_df is not None:
            similar_artist_rec_df = similar_artist_rec_df.union(similar_artist_rec_user_df) if similar_artist_rec_df \
                                                                                            else similar_artist_rec_user_df

    top_artist_rec_df = scale_rating(top_artist_rec_df)
    similar_artist_rec_df = scale_rating(similar_artist_rec_df)

    check_for_ratings_beyond_range(top_artist_rec_df, similar_artist_rec_df)

    top_artist_rec_mbid_df = get_recording_mbids(params, top_artist_rec_df, users_df)
    similar_artist_rec_mbid_df = get_recording_mbids(params, similar_artist_rec_df, users_df)

    users_df.unpersist()

    if params.top_artist_not_found:
        current_app.logger.error('Top artist candidate set not found for: \n"{}"\nYou might want to check the mapping.'
                                 .format(params.top_artist_not_found))

    if params.similar_artist_not_found:
        current_app.logger.error('Similar artist candidate set not found for: \n"{}"'
                                 '\nYou might want to check the artist relation.'.format(params.similar_artist_not_found))

    if params.top_artist_rec_not_generated:
        current_app.logger.error('Top artist recommendations not generated for: \n"{}"\nYou might want to check the training set'
                                 .format(params.top_artist_rec_not_generated))

    if params.similar_artist_rec_not_generated:
        current_app.logger.error('Similar artist recommendations not generated for: "{}"'
                                 '\nYou might want to check the training set'.format(params.similar_artist_rec_not_generated))

    return top_artist_rec_mbid_df, similar_artist_rec_mbid_df, user_count


def main(recommendation_top_artist_limit=None, recommendation_similar_artist_limit=None, users=None):

    try:
        listenbrainz_spark.init_spark_session('Recommendations')
    except SparkSessionNotInitializedException as err:
        current_app.logger.error(str(err), exc_info=True)
        raise

    try:
        recordings_df = utils.read_files_from_HDFS(path.RECORDINGS_DATAFRAME_PATH)
        top_artist_candidate_set_df = utils.read_files_from_HDFS(path.TOP_ARTIST_CANDIDATE_SET)
        similar_artist_candidate_set_df = utils.read_files_from_HDFS(path.SIMILAR_ARTIST_CANDIDATE_SET)
    except PathNotFoundException as err:
        current_app.logger.error(str(err), exc_info=True)
        raise
    except FileNotFetchedException as err:
        current_app.logger.error(str(err), exc_info=True)
        raise

    current_app.logger.info('Loading model...')
    model = load_model()

    # an action must be called to persist data in memory
    recordings_df.count()
    recordings_df.persist()

    params = RecommendationParams(recordings_df, model, top_artist_candidate_set_df,
                                  similar_artist_candidate_set_df,
                                  recommendation_top_artist_limit,
                                  recommendation_similar_artist_limit)

    current_app.logger.info('Generating recommendations...')
    ts = time.monotonic()
    top_artist_rec_df, similar_artist_rec_df, user_count = get_recommendations_for_all(params, users)
    total_time = time.monotonic() - ts
    current_app.logger.info('Recommendations Generated!')
    # persisted data must be cleared from memory after usage to avoid OOM
    recordings_df.unpersist()

    current_app.logger.info('Total time: {:.2f}sec'.format(total_time))

    if user_count == 0:
        current_app.logger.info("No active user found")
    else:
        current_app.logger.info('Average time: {:.2f}sec'.format(total_time / user_count))

    result = create_messages(top_artist_rec_df, similar_artist_rec_df, user_count, total_time)

    return result
