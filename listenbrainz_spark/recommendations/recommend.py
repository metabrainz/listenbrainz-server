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

from pyspark.sql import Row
from flask import current_app
import pyspark.sql.functions as func
from pyspark.sql.functions import col
from pyspark.mllib.recommendation import MatrixFactorizationModel
from pyspark.sql.types import StructField, StructType, FloatType, IntegerType


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


recommendation_schema = StructType([
    StructField('recording_id', IntegerType(), nullable=False),
    StructField('rating', FloatType(), nullable=False),
])


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


def get_recording_mbids(params: RecommendationParams, recommendation_df):
    """ Get recording mbids corresponding to recommended recording ids sorted on rating.

        Args:
            params: RecommendationParams class object.
            recommendation_df: Dataframe of recommended recording ids and corresponding ratings.

        Returns:
            dataframe of recording mbids.
    """
    recording_mbids_df = params.recordings_df.join(recommendation_df, 'recording_id', 'inner') \
                                             .orderBy(col('rating').desc()) \
                                             .select('mb_recording_mbid', 'rating')

    return recording_mbids_df


def generate_recommendations(candidate_set, params: RecommendationParams, limit):
    """
        Args:
            candidate_set (rdd): RDD of user_id and recording_id.
            params: RecommendationParams class object.
            limit (int): Number of recommendations to be generated.

        Returns:
            list of recommendations.
    """
    recommendations = params.model.predictAll(candidate_set).takeOrdered(limit, lambda product: -product.rating)
    return recommendations


def get_recommendation_df(recording_ids_and_ratings):
    """ Get dataframe from recommendation list.

        Args:
            recording_ids_and_ratings: List of recommended recording ids and ratings.

        Returns:
            df: dataframe of recommended recording ids and ratings.
    """
    df = None

    for entry in recording_ids_and_ratings:
        row = utils.create_dataframe(
            Row(
                recording_id=entry[0],
                rating=entry[1]
            ),
            schema=recommendation_schema
        )

        df = df.union(row) if df else row

    return df


def scale_ratings(mbids_and_ratings, params: RecommendationParams):
    """ Scale the ratings so that they fall on a range from 0.0 -> 1.0.

        Args:
            mbids_and_ratings: list of recommended recording mbids and ratings.
            params: RecommendationParams class object.
    """
    for row in mbids_and_ratings:
        rating = row[1]

        scaled_rating = (rating / 2.0) + 0.5

        if scaled_rating > 1.0 or scaled_rating < -1.0:
            params.ratings_beyond_range.append(rating)

        row[1] = round(min(max(scaled_rating, -1.0), 1.0), 3)


def get_recommended_mbids(candidate_set, params: RecommendationParams, limit):
    """ Generate recommendations from the candidate set.

        Args:
            candidate_set (rdd): RDD of user_id and recording_id.
            params: RecommendationParams class object.
            limit (int): Number of recommendations to be generated.

        Returns:
            mbids_and_ratings: list of recommended recording mbids and ratings.
    """
    recommendations = generate_recommendations(candidate_set, params, limit)

    recording_ids_and_ratings = [[recommendations[i].product, recommendations[i].rating] for i in range(len(recommendations))]

    if len(recording_ids_and_ratings) == 0:
        raise RecommendationsNotGeneratedException('Recommendations not generated!')

    recommendation_df = get_recommendation_df(recording_ids_and_ratings)

    recording_mbids_df = get_recording_mbids(params, recommendation_df)

    mbids_and_ratings = [[row.mb_recording_mbid, round(row.rating, 3)] for row in recording_mbids_df.collect()]

    scale_ratings(mbids_and_ratings, params)

    return mbids_and_ratings


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
    try:
        candidate_set_user_df.take(1)[0]
    except IndexError:
        raise IndexError()

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
            user_recommendations_top_artist: list of recommended recordings of top artist.
            user_recommendations_similar_artist: list of recommended recordings of similar artist.
    """
    user_recommendations_top_artist = list()
    try:
        top_artist_candidate_set_user = get_candidate_set_rdd_for_user(params.top_artist_candidate_set_df, user_id)
        user_recommendations_top_artist = get_recommended_mbids(top_artist_candidate_set_user, params,
                                                                params.recommendation_top_artist_limit,)
    except IndexError:
        params.top_artist_not_found.append(user_name)
    except RecommendationsNotGeneratedException:
        params.top_artist_rec_not_generated.append(user_name)

    user_recommendations_similar_artist = list()
    try:
        similar_artist_candidate_set_user = get_candidate_set_rdd_for_user(params.similar_artist_candidate_set_df, user_id)
        user_recommendations_similar_artist = get_recommended_mbids(similar_artist_candidate_set_user, params,
                                                                    params.recommendation_similar_artist_limit,)
    except IndexError:
        params.similar_artist_not_found.append(user_name)
    except RecommendationsNotGeneratedException:
        params.similar_artist_rec_not_generated.append(user_name)

    return user_recommendations_top_artist, user_recommendations_similar_artist


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


def get_message_for_inactive_users(messages, active_users, users):
    """ Get message to send over rabbitMQ for inactive users.

        We'd want to update recommendations for requested users with empty list
        who are not active in the past week/month

        Args:
            messages: list of rabbitMQ messages for active users
            active_users: list of active user names
            users = list of users names for whom recommendations are requested.

        Returns:
            updated messages list with messages for inactive users.
    """
    inactive_users = [user_name for user_name in users if user_name not in active_users]

    for user_name in inactive_users:
        messages.append({
            'musicbrainz_id': user_name,
            'type': 'cf_recording_recommendations',
            'top_artist': [],
            'similar_artist': [],
        })

    return messages


def get_recommendations_for_all(params: RecommendationParams, users):
    """ Get recommendations for all active users.

        Args:
            params: RecommendationParams class object.
            users = list of users names to generate recommendations.

        Returns:
            messages (list): user recommendations.
    """
    # to log time elapsed in generating recommendations for all users.
    ts = time.monotonic()
    messages = []
    # users active in the last week/month.
    # users who are a part of top artist candidate set
    active_users = []
    current_app.logger.info('Generating recommendations...')
    # users for whom recommendations will be generated.
    users_df = get_user_name_and_user_id(params, users)
    users_df.persist()
    for row in users_df.collect():
        # to log time elapsed in generating recommendations for a user.
        ts_user = time.monotonic()
        user_name = row.user_name
        user_id = row.user_id
        active_users.append(user_name)

        user_recommendations_top_artist, user_recommendations_similar_artist = get_recommendations_for_user(
                                                                                    user_id,
                                                                                    user_name,
                                                                                    params)

        messages.append({
            'musicbrainz_id': user_name,
            'type': 'cf_recording_recommendations',
            'top_artist': user_recommendations_top_artist,
            'similar_artist': user_recommendations_similar_artist,
        })

        current_app.logger.info('Took {}sec to generate recommendations for {}'
                                .format('{:.2f}'.format(time.monotonic() - ts_user), user_name))

    current_app.logger.info('Recommendations Generated!')
    if users:
        messages = get_message_for_inactive_users(messages, active_users, users)

    if params.ratings_beyond_range:
        current_app.logger.error('{} ratings are beyond the expected range i.e rating > 1 or rating < -1'
                                 '\nMax rating: {}\nMin rating: {}'.format(len(params.ratings_beyond_range),
                                  max(params.ratings_beyond_range), min(params.ratings_beyond_range)))

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

    total_time = time.monotonic() - ts
    user_count = users_df.count()
    messages.append(
        {
            'type': 'cf_recording_recommendations_mail',
            'user_count': user_count,
            'total_time': '{:.2f}'.format(total_time / 3600)
        }
    )

    current_app.logger.info('Total time: {:.2f}hrs'.format(total_time / 3600))
    current_app.logger.info('Average time: {:.2f}sec'.format(total_time / user_count))
    users_df.unpersist()

    return messages


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

    messages = get_recommendations_for_all(params, users)
    # persisted data must be cleared from memory after usage to avoid OOM
    recordings_df.unpersist()

    return messages
