import os
import sys
import time
import json
import uuid
import logging
from time import time
from datetime import datetime
from collections import defaultdict

import listenbrainz_spark
from listenbrainz_spark import config
from listenbrainz_spark.stats import run_query
from listenbrainz_spark.recommendations import utils

from pyspark.sql.utils import AnalysisException
from pyspark.mllib.recommendation import MatrixFactorizationModel

def load_model(path):
    return MatrixFactorizationModel.load(listenbrainz_spark.context, path)

def get_user_id(user_name):
    """ Get user id using user name.

        Args:
            user_name: Name of the user.

        Returns:
            user_id: User id of the user.
    """
    result = run_query("""
        SELECT user_id
          FROM user
         WHERE user_name = '%s'
    """ % user_name)
    return result.first()['user_id']

def recommend_user(user_name, model, all_recordings, recordings_df):
    user_id = get_user_id(user_name)

    candidate_set = all_recordings.rdd.map(lambda r: r['recording_id'])
    recommendations = model.predictAll(candidate_set.map(lambda recording: (user_id, recording))).takeOrdered(              config.RECOMMENDATION_LIMIT, lambda product: -product.rating)
    recommended_recording_ids = [(recommendations[i].product) for i in range(len(recommendations))]

    recommendations_df = recordings_df[recordings_df.recording_id.isin(recommended_recording_ids)].collect()
    recommended_recordings = []

    for row in recommendations_df:
        rec = (row.track_name, row.recording_msid, row.artist_name, row.artist_msid, row.release_name, row.release_msid)
        recommended_recordings.append(rec)

    user_recommendations = defaultdict(dict)
    user_recommendations['recordings'] = recommended_recordings
    return user_recommendations

def main():
    ti = time()
    try:
        listenbrainz_spark.init_spark_session('Recommendations')
    except AttributeError as err:
        logging.error('Cannot initialize Spark Session: {} \n {}. Aborting...'.format(type(err).__name__,str(err)))
        sys.exit(-1)
    except Exception as err:
        logging.error('An error occurred while initializing Spark session: {} \n {}. Aborting...'.format(type(err)          .__name__,str(err)), exc_info=True)
        sys.exit(-1)

    try:
        path = os.path.join(config.HDFS_CLUSTER_URI, 'data', 'listenbrainz', 'recommendation-engine', 'dataframes')
        playcounts_df = listenbrainz_spark.sql_context.read.parquet(path + '/playcounts_df.parquet')
        users_df = listenbrainz_spark.sql_context.read.parquet(path + '/users_df.parquet')
        recordings_df = listenbrainz_spark.sql_context.read.parquet(path + '/recordings_df.parquet')
    except AnalysisException as err:
        logging.error('Cannot read parquet files from HDFS: {} \n {}'.format(type(err).__name__,str(err)))
        sys.exit(-1)
    except Exception as err:
        logging.error('An error occured while fetching parquets: {} \n {}. Aborting...'.format(type(err).__name__,
            str(err)), exc_info=True)
        sys.exit(-1)

    time_info = defaultdict(dict)
    time_info['dataframes'] = '{:.2f}'.format((time() - ti) / 60)
    try:
        users_df.createOrReplaceTempView('user')
        playcounts_df.createOrReplaceTempView('playcount')
    except AnalysisException as err:
        logging.error('Cannot register dataframes: {} \n {}. Aborting...'.format(type(err).__name__, str(err)))
        sys.exit(-1)
    except Exception as err:
        logging.error('An error occured while registering dataframes: {} \n {}. Aborting...'.format(type(err).__name__,      str(err)), exc_info=True)
        sys.exit(-1)

    t0 = time()
    all_recordings = recordings_df.select('recording_id')
    all_recordings.persist()
    all_recordings_count = '{:,}'.format(all_recordings.count())
    time_info['all_recordings'] = '{:.2f}'.format((time() - t0) / 60)

    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'recommendation-metadata.json')
    with open(path, 'r') as f:
        recommendation_metadata = json.load(f)
        best_model_id = recommendation_metadata['best_model_id']

    best_model_path = os.path.join('/', 'data', 'listenbrainz', 'recommendation-engine', 'best-model', '{}'.format(         best_model_id))

    logging.info('Loading model...')
    try:
        t0 = time()
        model = load_model(config.HDFS_CLUSTER_URI + best_model_path)
        time_info['load_model'] = '{:.2f}'.format((time() - t0) / 60)
    except Py4JJavaError as err:
        logging.error('Unable to load model: {} \n {}. Aborting...'.format(type(err).__name__,str(err)))
        sys.exit(-1)
    except Exception as err:
        logging.error('An error occured while loading model: {} \n {}. Aborting...'.format(type(err).__name__,
            str(err),exc_info=True))
        sys.exit(-1)

    path = os.path.join(os.path.dirname(os.path.abspath(__file__)),'recommendation-metadata.json')
    ts = time()
    with open(path) as f:
        recommendation_metadata = json.load(f)
        recommendations = defaultdict(dict)
        for user_name in recommendation_metadata['user_name']:
            try:
                t0 = time()
                user_recommendations = recommend_user(user_name, model, all_recordings, recordings_df)
                user_recommendations['total-time'] = '{:.2f}'.format((time() - t0) / 60)
                logging.info('Recommendations for "{}" generated'.format(user_name))
                recommendations[user_name] = user_recommendations
            except TypeError as err:
                logging.error('{}: Invalid user name. User "{}" does not exist.'.format(type(err).__name__,user_name))
            except Exception as err:
                logging.error('Recommendations for "{}" not generated.\n{}'.format(user_name, str(err)), exc_info=True)
    time_info['total_recommendation_time'] = '{:.2f}'.format((time() - ts) / 3600)

    all_recordings.unpersist()

    date = datetime.utcnow().strftime('%Y-%m-%d')
    recommendation_html = 'Recommendation-{}-{}.html'.format(uuid.uuid4(), date)
    column = ('Track Name', 'Recording MSID', 'Artist Name', 'Artist MSID', 'Release Name', 'Release MSID')
    context = {
        'recommendations' : recommendations,
        'column' : column,
        'total_time' : '{:.2f}'.format((time() - ti) / 3600),
        'time' : time_info,
        'best_model' : best_model_id,
        'all_recordings_count' : all_recordings_count,
    }
    utils.save_html(recommendation_html, context, 'recommend.html')
