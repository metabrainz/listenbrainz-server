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
from listenbrainz_spark import config, utils
from listenbrainz_spark.sql import get_user_id
from listenbrainz_spark.exceptions import SQLException
from listenbrainz_spark.sql import recommend_queries as sql
from listenbrainz_spark.recommendations.utils import save_html

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

def get_recommended_recordings(candidate_set, limit, recordings_df, model):
    """ Get list of recommended recordings from the candidate set

        Args:
            candidate_set (rdd): RDD with elements as:
                [
                    'user_id', 'recording_id'
                ]
            limit (int): Number of recommendations to be generated.
            recordings_df (dataframe): Columns can be depicted as:
                [
                    'track_name', 'recording_msid', 'artist_name', 'artist_msid', 'release_name',
                    'release_msid', 'recording_id'
                ]
            model (parquet): Best model after training.

        Returns:
            recommended_recordings (list): [
                    ('xxx', 'xxx', 'xxx', 'xxx', 'xxx', 'xxx', 'xxx'),
                    ...
                    ('xxx', 'xxx', 'xxx', 'xxx', 'xxx', 'xxx', 'xxx')
                ]
    """
    recommendations = model.predictAll(candidate_set).takeOrdered(limit, lambda product: -product.rating)
    recommended_recording_ids = [(recommendations[i].product) for i in range(len(recommendations))]
    if len(recommended_recording_ids) == 1:
        recommendations_df = sql.get_recordings(tuple(recommended_recording_ids[0]))
    else:
        recommendations_df = sql.get_recordings(tuple(recommended_recording_ids))
    recommended_recordings = []
    for row in recommendations_df.collect():
        rec = (row.track_name, row.recording_msid, row.artist_name, row.artist_msid, row.release_name, row.release_msid)
        recommended_recordings.append(rec)
    return recommended_recordings

def recommend_user(user_name, model, recordings_df):
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
    user_id = get_user_id(user_name)

    top_artists_recordings = sql.get_top_artists_recordings(user_id)
    top_artists_candidate_set = top_artists_recordings.rdd.map(lambda r: (r['user_id'], r['recording_id']))
    top_artists_recommended_recordings = get_recommended_recordings(top_artists_candidate_set, config \
        .RECOMMENDATION_TOP_ARTIST_LIMIT, recordings_df, model)
    user_recommendations['top_artists_recordings'] = top_artists_recommended_recordings

    similar_artists_recordings = sql.get_similar_artists_recordings(user_id)
    similar_artists_candidate_set = similar_artists_recordings.rdd.map(lambda r : (r['user_id'], r['recording_id']))
    similar_artists_recommended_recordings = get_recommended_recordings(similar_artists_candidate_set,
        config.RECOMMENDATION_SIMILAR_ARTIST_LIMIT, recordings_df, model)
    user_recommendations['similar_artists_recordings'] = similar_artists_recommended_recordings
    return user_recommendations

def get_recommendations(user_names, recordings_df, model):
    """ Generate recommendations for users.

        Args:
            user_names (list): User name of users for whom recommendations shall be generated.
            model: Best model after training.
            recordings_df (dataframe): Columns can be depicted as:
                [
                    'track_name', 'recording_msid', 'artist_name', 'artist_msid', 'release_name',
                    'release_msid', 'recording_id'
                ]

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
            user_recommendations = recommend_user(user_name, model, recordings_df)
            user_recommendations['time'] = '{:.2f}'.format((time() - t0) / 60)
            logging.info('Recommendations for "{}" generated'.format(user_name))
            recommendations[user_name] = user_recommendations
        except TypeError as err:
            logging.error('{}: Invalid user name. User "{}" does not exist.'.format(type(err).__name__,user_name))
        except SQLException as err:
            logging.error('{}\nRecommendations for "{}" not generated'.format(err, user_name))
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
    column = ('Track Name', 'Recording MSID', 'Artist Name', 'Artist MSID', 'Release Name', 'Release MSID')
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
    except Py4JJavaError as err:
        logging.error('{}\n{}\nAborting...'.format(str(err), err.java_exception))
        sys.exit(-1)

    try:
        # path where dataframes are stored.
        path = os.path.join(config.HDFS_CLUSTER_URI, 'data', 'listenbrainz', 'recommendation-engine', 'dataframes')
        users_df = utils.read_files_from_HDFS(path + '/users_df.parquet')
        recordings_df = utils.read_files_from_HDFS(path + '/recordings_df.parquet')

        # path where candidate sets are stored.
        path = os.path.join(config.HDFS_CLUSTER_URI, 'data', 'listenbrainz', 'recommendation-engine', 'candidate-set')
        top_artists_candidate_df = utils.read_files_from_HDFS(path + '/top_artists.parquet')
        similar_artists_candidate_df = utils.read_files_from_HDFS(path + '/similar_artists.parquet')
    except AnalysisException as err:
        logging.error('{}\n{}\nAborting...'.format(str(err), err.stackTrace))
        sys.exit(-1)
    except Py4JJavaError as err:
        logging.error('{}\n{}\nAborting...'.format(str(err), err.java_exception))
        sys.exit(-1)

    try:
        utils.register_dataframe(users_df, 'user')
        utils.register_dataframe(top_artists_candidate_df, 'top_artist')
        utils.register_dataframe(similar_artists_candidate_df, 'similar_artist')
        utils.register_dataframe(recordings_df, 'recording')
    except Py4JJavaError as err:
        logging.error('{}\n{}\nAborting...'.format(str(err), err.java_exception))
        sys.exit(-1)

    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'recommendation-metadata.json')
    with open(path, 'r') as f:
        recommendation_metadata = json.load(f)
        best_model_id = recommendation_metadata['best_model_id']
        user_names = recommendation_metadata['user_name']

    best_model_path = os.path.join('/', 'data', 'listenbrainz', 'recommendation-engine', 'best-model', '{}' \
        .format(best_model_id))

    logging.info('Loading model...')
    t0 = time()
    try:
        model = load_model(config.HDFS_CLUSTER_URI + best_model_path)
    except Py4JJavaError as err:
        logging.error('Unable to load model "{}": {}\n{}\nAborting...'.format(best_model_id, type(err).__name__,
            str(err.java_exception)))
        sys.exit(-1)
    time_['load_model'] = '{:.2f}'.format((time() - t0) / 60)

    # an action must be called to persist data in memory
    recordings_df.count()
    recordings_df.persist()

    t0 = time()
    recommendations = get_recommendations(user_names, recordings_df, model)
    time_['total_recommendation_time'] = '{:.2f}'.format((time() - t0) / 3600)

    # persisted data must be cleared from memory after usage to avoid OOM
    recordings_df.unpersist()

    if SAVE_RECOMMENDATION_HTML:
        get_recommendation_html(recommendations, time_, best_model_id, ti)
