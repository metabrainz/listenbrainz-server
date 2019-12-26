import os
import sys
import time
import json
import uuid
import logging
from time import time
from datetime import datetime
from collections import defaultdict
from py4j.protocol import Py4JJavaError

import listenbrainz_spark
from listenbrainz_spark import config, utils, path
from listenbrainz_spark.recommendations.candidate_sets import get_user_id
from listenbrainz_spark.exceptions import SQLException, SparkSessionNotInitializedException, PathNotFoundException, \
    FileNotFetchedException, ViewNotRegisteredException
from listenbrainz_spark.sql import recommend_queries as sql
from listenbrainz_spark.recommendations.utils import save_html

from flask import current_app
from pyspark.sql.functions import lit, col
from pyspark.sql.utils import AnalysisException
from pyspark.mllib.recommendation import MatrixFactorizationModel

# Recommendation HTML is generated if set to true.
SAVE_RECOMMENDATION_HTML = True

def load_model(path):
    """ Load best model from given path in HDFS.

        Args:
            path (str): Path where best model is stored.
    """
    return MatrixFactorizationModel.load(listenbrainz_spark.context, path)

def get_recommended_recordings(candidate_set, limit, recordings_df, model, mapped_listens):
    """ Get list of recommended recordings from the candidate set

        Args:
            candidate_set (rdd): RDD with elements as:
                [
                    'user_id', 'recording_id'
                ]
            limit (int): Number of recommendations to be generated.
            recordings_df (dataframe): Columns can be depicted as:
                [
                    'mb_recording_gid', 'mb_artist_credit_id', 'recording_id'
                ]
            model (parquet): Best model after training.
            mapped_listens (dataframe): Dataframe with all the columns/fields that a typical listen has.

        Returns:
            recommended_recordings (list): [
                    ('xxx', 'xxx', 'xxx', 'xxx', 'xxx', 'xxx', 'xxx'),
                    ...
                    ('xxx', 'xxx', 'xxx', 'xxx', 'xxx', 'xxx', 'xxx')
                ]
    """
    recommendations = model.predictAll(candidate_set).takeOrdered(limit, lambda product: -product.rating)
    recommended_recording_ids = [(recommendations[i].product) for i in range(len(recommendations))]

    df = recordings_df.select('mb_artist_credit_id', 'mb_recording_gid') \
        .where(recordings_df.recording_id.isin(recommended_recording_ids))

    # get the track_name and artist_name to make the HTML redable. This step will not be required when sending recommendations
    # to lemmy since gids are enough to recognize the track.
    recommendations_df = df.join(mapped_listens, ['mb_artist_credit_id', 'mb_recording_gid']) \
        .select('mb_artist_credit_id', 'artist_name', 'mb_recording_gid', 'track_name').distinct()

    recommended_recordings = []
    for row in recommendations_df.collect():
        rec = (row.track_name, row.artist_name, row.mb_recording_gid, row.mb_artist_credit_id)
        recommended_recordings.append(rec)
    return recommended_recordings

def recommend_user(user_name, model, recordings_df, users_df, top_artists_candidate_set,
    similar_artists_candidate_set, mapped_listens):
    """ Get recommended recordings which belong to top artists and artists similar to top
        artists listened to by the user.

        Args:
            user_name (str): User name of the user.
            model: Best model after training.
            recordings_df (dataframe): Columns can be depicted as:
                [
                    'track_name', 'recording_msid', 'artist_name', 'artist_msid', 'release_name',
                    'release_msid', 'recording_id'
                ]
            users_df (dataframe): Dataframe containing user names and user ids.
            top_artists_candidate_set (dataframe): Dataframe containing recording ids of top artists.
            similar_artists_candidate_set (dataframe): Dataframe containing recording ids of similar artists.
            mapped_listens (dataframe): Dataframe with all the columns/fields that a typical listen has.

        Returns:
            user_recommendations (dict): Dictionary can be depicted as:
                {
                    'top_artists_recordings': [
                        ('xxx', 'xxx', 'xxx', 'xxx', 'xxx', 'xxx', 'xxx'),
                        ...
                        ('xxx', 'xxx', 'xxx', 'xxx', 'xxx', 'xxx', 'xxx')
                    ]
                    'similar_artists_recordings' : [
                        ('xxx', 'xxx', 'xxx', 'xxx', 'xxx', 'xxx', 'xxx'),
                        ...
                        ('xxx', 'xxx', 'xxx', 'xxx', 'xxx', 'xxx', 'xxx')
                        ]
                }
    """
    user_recommendations = defaultdict(dict)
    user_id = get_user_id(users_df, user_name)

    top_artists_recordings_df = top_artists_candidate_set.select('user_id', 'recording_id') \
        .where(col('user_id') == user_id)
    top_artists_recordings_rdd = top_artists_recordings_df.rdd.map(lambda r: (r['user_id'], r['recording_id']))
    top_artists_recommended_recordings = get_recommended_recordings(top_artists_recordings_rdd, config \
        .RECOMMENDATION_TOP_ARTIST_LIMIT, recordings_df, model, mapped_listens)
    user_recommendations['top_artists_recordings'] = top_artists_recommended_recordings

    similar_artists_recordings_df = similar_artists_candidate_set.select('user_id', 'recording_id') \
        .where(col('user_id') == user_id)
    similar_artists_recordings_rdd = similar_artists_recordings_df.rdd.map(lambda r : (r['user_id'], r['recording_id']))
    similar_artists_recommended_recordings = get_recommended_recordings(similar_artists_recordings_rdd,
        config.RECOMMENDATION_SIMILAR_ARTIST_LIMIT, recordings_df, model,mapped_listens)
    user_recommendations['similar_artists_recordings'] = similar_artists_recommended_recordings
    return user_recommendations

def get_recommendations(user_names, recordings_df, model, users_df, top_artists_candidate_set,
    similar_artists_candidate_set, mapped_listens):
    """ Generate recommendations for users.

        Args:
            user_names (list): User name of users for whom recommendations shall be generated.
            model: Best model after training.
            recordings_df (dataframe): Columns can be depicted as:
                [
                    'mb_recording_gid', 'mb_artist_credit_id', 'recording_id'
                ]
            users_df (dataframe): Dataframe containing user names and user ids.
            top_artists_candidate_set (dataframe): Dataframe containing recording ids of top artists.
            similar_artists_candidate_set (dataframe): Dataframe containing recording ids of similar artists.
            mapped_listens (dataframe): Dataframe with all the columns/fields that a typical listen has.

        Returns:
            recommendations (dict): Dictionary can be depicted as:
                {
                    'user_name 1': {
                        'time': 'xx.xx',
                        'top_artists_recordings': [
                            ('xxx', 'xxx', 'xxx', 'xxx', 'xxx', 'xxx', 'xxx'),
                            ...
                            ('xxx', 'xxx', 'xxx', 'xxx', 'xxx', 'xxx', 'xxx')
                        ]
                        'similar_artists_recordings' : [
                            ('xxx', 'xxx', 'xxx', 'xxx', 'xxx', 'xxx', 'xxx'),
                            ...
                            ('xxx', 'xxx', 'xxx', 'xxx', 'xxx', 'xxx', 'xxx')
                        ]
                    }
                }
    """
    recommendations = defaultdict(dict)
    for user_name in user_names:
        try:
            t0 = time()
            user_recommendations = recommend_user(user_name, model, recordings_df, users_df, top_artists_candidate_set,
                similar_artists_candidate_set, mapped_listens)
            user_recommendations['time'] = '{:.2f}'.format((time() - t0) / 60)
            current_app.logger.info('Recommendations for "{}" generated'.format(user_name))
            recommendations[user_name] = user_recommendations
        except IndexError:
            current_app.logger.error('{} is new/invalid user.'.format(user_name))
    return recommendations

def get_recommendation_html(recommendations, time_, best_model_id, ti):
    """ Prepare and save recommendation HTML.

        Args:
            time_ (dict): Dictionary containing execution time information, can be depicted as:
                {
                    'load_model' : '3.09',
                    ...
                }
            best_model_id (str): Id of the model used for generating recommendations
            ti (str): Seconds since epoch when the script was run.
            recommendations (dict): Dictionary can be depicted as:
                {
                    'user_name 1': {
                        'time': 'xx.xx',
                        'top_artists_recordings': [
                            ('xxx', 'xxx', 'xxx', 'xxx', 'xxx', 'xxx', 'xxx'),
                            ...
                            ('xxx', 'xxx', 'xxx', 'xxx', 'xxx', 'xxx', 'xxx')
                        ]
                        'similar_artists_recordings' : [
                            ('xxx', 'xxx', 'xxx', 'xxx', 'xxx', 'xxx', 'xxx'),
                            ...
                            ('xxx', 'xxx', 'xxx', 'xxx', 'xxx', 'xxx', 'xxx')
                        ]
                    }
                }
    """
    date = datetime.utcnow().strftime('%Y-%m-%d')
    recommendation_html = 'Recommendation-{}-{}.html'.format(uuid.uuid4(), date)
    column = ('Track Name', 'Artist Name', 'MB_RECORDING_GID', 'MB_ARTIST_CREDIT_ID')
    context = {
        'recommendations' : recommendations,
        'column' : column,
        'total_time' : '{:.2f}'.format((time() - ti) / 3600),
        'time' : time_,
        'best_model' : best_model_id,
    }
    save_html(recommendation_html, context, 'recommend.html')

def main():
    ti = time()
    time_ = defaultdict(dict)
    try:
        listenbrainz_spark.init_spark_session('Recommendations')
    except SparkSessionNotInitializedException as err:
        current_app.logger.error(str(err), exc_info=True)
        sys.exit(-1)

    try:
        users_df = utils.read_files_from_HDFS(path.USERS_DATAFRAME_PATH)
        recordings_df = utils.read_files_from_HDFS(path.RECORDINGS_DATAFRAME_PATH)

        top_artists_candidate_set = utils.read_files_from_HDFS(path.TOP_ARTIST_CANDIDATE_SET)
        similar_artists_candidate_set = utils.read_files_from_HDFS(path.SIMILAR_ARTIST_CANDIDATE_SET)
        mapped_listens = utils.read_files_from_HDFS(path.MAPPED_LISTENS)
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
        user_names = recommendation_metadata['user_name']

    best_model_path = path.DATA_DIR + '/' + best_model_id

    current_app.logger.info('Loading model...')
    t0 = time()
    try:
        model = load_model(config.HDFS_CLUSTER_URI + best_model_path)
    except Py4JJavaError as err:
        current_app.logger.error('Unable to load model "{}"\n{}\nAborting...'.format(best_model_id, str(err.java_exception)),
            exc_info=True)
        sys.exit(-1)
    time_['load_model'] = '{:.2f}'.format((time() - t0) / 60)

    # an action must be called to persist data in memory
    recordings_df.count()
    recordings_df.persist()

    t0 = time()
    recommendations = get_recommendations(user_names, recordings_df, model, users_df, top_artists_candidate_set,
        similar_artists_candidate_set, mapped_listens)
    time_['total_recommendation_time'] = '{:.2f}'.format((time() - t0) / 3600)

    # persisted data must be cleared from memory after usage to avoid OOM
    recordings_df.unpersist()

    if SAVE_RECOMMENDATION_HTML:
        get_recommendation_html(recommendations, time_, best_model_id, ti)
