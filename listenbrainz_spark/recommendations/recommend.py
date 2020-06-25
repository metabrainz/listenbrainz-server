import sys
import os
import json
import logging
from time import time
from datetime import datetime
from collections import defaultdict
from py4j.protocol import Py4JJavaError

import listenbrainz_spark
from listenbrainz_spark import config, utils, path
from listenbrainz_spark.exceptions import (PathNotFoundException,
                                           FileNotFetchedException,
                                           ViewNotRegisteredException,
                                           SparkSessionNotInitializedException,
                                           RecommendationsNotGeneratedException)

from flask import current_app
from pyspark.sql.functions import col
from pyspark.sql.utils import AnalysisException
from pyspark.mllib.recommendation import MatrixFactorizationModel


class RecommendationParams:

    def __init__(self, recordings, model, top_artist_candidate_set, similar_artist_candidate_set,
                 recommendation_top_artist_limit, recommendation_similar_artist_limit):
        self.recordings = recordings
        self.model = model
        self.top_artist_candidate_set = top_artist_candidate_set
        self.similar_artist_candidate_set = similar_artist_candidate_set
        self.recommendation_top_artist_limit = recommendation_top_artist_limit
        self.recommendation_similar_artist_limit = recommendation_similar_artist_limit


def load_model(path):
    """ Load best model from given path in HDFS.

        Args:
            path (str): Path where best model is stored.
    """
    return MatrixFactorizationModel.load(listenbrainz_spark.context, path)


def get_recording_mbids(params, recommended_recording_ids):
    """ Get recording mbids corresponding to recommended recording ids.

        Args:
            params: RecommendationParams class object.
            recommended_recording_ids: list of recommended recording ids.

        Returns:
            dataframe of recording mbids.
    """
    recording_mbids = params.recordings.select('mb_recording_mbid')\
                                       .where(params.recordings.recording_id.isin(recommended_recording_ids))
    return recording_mbids


def generate_recommendations(candidate_set, params, limit):
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


def get_recommended_mbids(candidate_set, params, limit):
    """ Generate recommendations from the candidate set.

        Args:
            candidate_set (rdd): RDD of user_id and recording_id.
            params: RecommendationParams class object.
            limit (int): Number of recommendations to be generated.

        Returns:
            recommended_recordings_mbids: list of recommended recording mbids.
    """

    recommendations = generate_recommendations(candidate_set, params, limit)
    recommended_recording_ids = [(recommendations[i].product) for i in range(len(recommendations))]
    if len(recommended_recording_ids) == 0:
        raise RecommendationsNotGeneratedException('')

    recording_mbids = get_recording_mbids(params, recommended_recording_ids)

    recommended_recording_mbids = [row.mb_recording_mbid for row in recording_mbids.collect()]
    return recommended_recording_mbids


def get_candidate_set_rdd_for_user(candidate_set, user_id):
    """ Get candidate set RDD for a given user.

        Args:
            candidate_set: A dataframe of user_id and recording_id for all users.
            user_id (int): user id of the user.

        Returns:
            candidate_set_rdd: An RDD of user_id and recording_id for a given user.
    """
    candidate_set = candidate_set.select('user_id', 'recording_id') \
                                 .where(col('user_id') == user_id)
    try:
        candidate_set.take(1)[0]
    except IndexError:
        raise IndexError()

    candidate_set_rdd = candidate_set.rdd.map(lambda r: (r['user_id'], r['recording_id']))

    return candidate_set_rdd


def get_recommendations_for_user(user_id, user_name, params):
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
        top_artist_candidate_set_user = get_candidate_set_rdd_for_user(params.top_artist_candidate_set, user_id)
        user_recommendations_top_artist = get_recommended_mbids(top_artist_candidate_set_user, params,
                                                                params.recommendation_top_artist_limit)
    except IndexError:
        current_app.logger.info('Top artist candidate set not found for "{}"'.format(user_name))
    except RecommendationsNotGeneratedException:
        current_app.logger.info('Top artist recommendations not generated for "{}"'.format(user_name))

    user_recommendations_similar_artist = list()
    try:
        similar_artist_candidate_set_user = get_candidate_set_rdd_for_user(params.similar_artist_candidate_set, user_id)
        user_recommendations_similar_artist = get_recommended_mbids(similar_artist_candidate_set_user, params,
                                                                    params.recommendation_similar_artist_limit)
    except IndexError:
        current_app.logger.info('Similar artist candidate set not found for "{}"'.format(user_name))
    except RecommendationsNotGeneratedException:
        current_app.logger.info('Similar artist recommendations not generated for "{}"'.format(user_name))

    return user_recommendations_top_artist, user_recommendations_similar_artist


def get_users(params):
    """ Get users from top artist candidate set.

        Args:
            params: RecommendationParams class object.

        Returns:
            users: dataframe of user id and user names.
    """
    users = params.top_artist_candidate_set.select('user_id', 'user_name').distinct()
    return users


def get_recommendations_for_all(params):
    """ Get recommendations for all active users.

        Args:
            params: RecommendationParams class object.

        Returns:
            messages (list): user recommendations.
    """
    messages = []
    current_app.logger.info('Generating recommendations...')
    # active users in the last week/month.
    # users for whom recommendations will be generated.
    users = get_users(params)
    for row in users.collect():
        user_name = row.user_name
        user_id = row.user_id

        user_recommendations_top_artist, user_recommendations_similar_artist = get_recommendations_for_user(user_id,
                                                                                                            user_name,
                                                                                                            params)

        messages.append({
            'musicbrainz_id': user_name,
            'type': 'cf_recording_recommendations',
            'top_artist': user_recommendations_top_artist,
            'similar_artist': user_recommendations_similar_artist,
        })

    current_app.logger.info('Recommendations Generated!')
    return messages


def main(recommendation_top_artist_limit=None, recommendation_similar_artist_limit=None):

    if recommendation_top_artist_limit is None:
        current_app.logger.critical('Please provide top artist recommendations limit.')
        sys.exit(-1)

    if recommendation_similar_artist_limit is None:
        current_app.logger.critical('Please provide similar artist recommendations limit.')
        sys.exit(-1)

    try:
        listenbrainz_spark.init_spark_session('Recommendations')
    except SparkSessionNotInitializedException as err:
        current_app.logger.error(str(err), exc_info=True)
        sys.exit(-1)

    try:
        recordings = utils.read_files_from_HDFS(path.RECORDINGS_DATAFRAME_PATH)
        top_artist_candidate_set = utils.read_files_from_HDFS(path.TOP_ARTIST_CANDIDATE_SET)
        similar_artist_candidate_set = utils.read_files_from_HDFS(path.SIMILAR_ARTIST_CANDIDATE_SET)
    except PathNotFoundException as err:
        current_app.logger.error(str(err), exc_info=True)
        sys.exit(-1)
    except FileNotFetchedException as err:
        current_app.logger.error(str(err), exc_info=True)
        sys.exit(-1)

    metadata_file_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'recommendation-metadata.json')
    with open(metadata_file_path, 'r') as f:
        recommendation_metadata = json.load(f)
        best_model_id = recommendation_metadata['best_model_id']

    best_model_path = path.DATA_DIR + '/' + best_model_id

    current_app.logger.info('Loading model...')
    try:
        model = load_model(config.HDFS_CLUSTER_URI + best_model_path)
    except Py4JJavaError as err:
        current_app.logger.error('Unable to load model "{}"\n{}\nAborting...'.format(best_model_id, str(err.java_exception)),
                                 exc_info=True)
        sys.exit(-1)

    # an action must be called to persist data in memory
    recordings.count()
    recordings.persist()

    params = RecommendationParams(recordings, model, top_artist_candidate_set,
                                  similar_artist_candidate_set,
                                  recommendation_top_artist_limit,
                                  recommendation_similar_artist_limit)

    messages = get_recommendations_for_all(params)
    # persisted data must be cleared from memory after usage to avoid OOM
    recordings.unpersist()

    return messages
