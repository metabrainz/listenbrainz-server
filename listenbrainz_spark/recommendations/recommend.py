import sys
import os
import time
import listenbrainz_spark
import json
import logging
import uuid

from pyspark.mllib.recommendation import MatrixFactorizationModel
from listenbrainz_spark import config
from listenbrainz_spark.stats import run_query
from listenbrainz_spark.recommendations import utils
from time import sleep
from collections import defaultdict
from datetime import datetime

def load_model(path):
    return MatrixFactorizationModel.load(listenbrainz_spark.context, path)

def get_user_id(user_name):
    result = run_query("""
        SELECT user_id
          FROM user
         WHERE user_name = '%s'
    """ % user_name)
    return result.first()['user_id']

def recommend_user(user_name, model, all_recordings, recordings_df, count):
    user_id = get_user_id(user_name)
    user_playcounts = run_query("""
        SELECT recording_id
          FROM playcount
         WHERE user_id = %d
    """ % user_id)

    candidate_recordings = all_recordings.subtract(user_playcounts) 
    candidate_recordings.limit(count)
    candidate_recordings = candidate_recordings.rdd.map(lambda r : r['recording_id'])

    recommendations = model.predictAll(candidate_recordings.map(lambda recording: (user_id, recording))).takeOrdered(50, lambda product: -product.rating)
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
    ti = time.time()
    try:
        listenbrainz_spark.init_spark_session('Recommendations')
    except Exception as err:
        raise SystemExit("Cannot initialize Spark Session: %s. Aborting..." % (str(err)))
    
    try:
        path = os.path.join('/', 'data', 'listenbrainz', 'recommendation-engine', 'dataframes')
        playcounts_df = listenbrainz_spark.sql_context.read.parquet(config.HDFS_CLUSTER_URI + path + '/playcounts_df.parquet')
        users_df = listenbrainz_spark.sql_context.read.parquet(config.HDFS_CLUSTER_URI + path + '/users_df.parquet')
        recordings_df = listenbrainz_spark.sql_context.read.parquet(config.HDFS_CLUSTER_URI + path + '/recordings_df.parquet')
    except Exception as err:
        raise SystemExit("Cannot read dataframes from HDFS: %s. Aborting..." % (str(err)))

    time_info = defaultdict(dict)
    t = "%2.f" % ((time.time() - ti) / 60)
    time_info['dataframes'] = t 
    users_df.createOrReplaceTempView('user')
    playcounts_df.createOrReplaceTempView('playcount')
    recordings_df.persist()
    count = recordings_df.count() // 2

    t0 = time.time()
    all_recordings = recordings_df.select('recording_id')
    all_recordings.persist()
    all_recordings_count = "{:,}".format(all_recordings.count())
    t = "%.2f" % ((time.time() - t0) / 60)
    time_info['all_recordings'] = t

    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'recommendation-metadata.json')
    with open(path, 'r') as f:
        recommendation_metadata = json.load(f)
        best_model_id = recommendation_metadata['best_model_id']

    best_model_path = os.path.join('/', 'data', 'listenbrainz', 'recommendation-engine', 'best_model', '{}'.format(best_model_id))
    
    print("Loading model...")
    for attempt in range(config.MAX_RETRIES):
        try:
            t0 = time.time()
            model = load_model(config.HDFS_CLUSTER_URI + best_model_path)
            t = "%.2f" % ((time.time() - t0) / 60)
            time_info['load_model'] = t
            break
        except Exception as err:
            sleep(config.TIME_BEFORE_RETRIES)
            if attempt == config.MAX_RETRIES - 1:
                raise SystemExit("%s.Aborting..." % (str(err)))
            logging.error("Unable to load model: %s.Retrying in %ss" % (str(err), config.TIME_BEFORE_RETRIES))

    path = os.path.join(os.path.dirname(os.path.abspath(__file__)),'recommendation-metadata.json')
    ts = time.time()
    with open(path) as f:
        recommendation_metadata = json.load(f)
        recommendations = {}
        for user_name in recommendation_metadata['user_name']:
            try:
                t0 = time.time()
                user_recommendations = recommend_user(user_name, model, all_recordings, recordings_df, count)
                t = "%.2f" % ((time.time() - t0) / 60)
                user_recommendations['total-time'] = t
                print("Recommendations for %s generated" % (user_name))
                recommendations[user_name] = user_recommendations
            except TypeError as err:
                logging.error("%s: Invalid user name. User \"%s\" does not exist." % (type(err).__name__,user_name))
            except Exception as err:
                logging.error("Recommendations for \"%s\" not generated.%s" % (user_name, str(err)))
    t = "%.2f" % ((time.time() - ts) / 3600)
    time_info['total_recommendation_time'] = t

    all_recordings.unpersist()
    recordings_df.unpersist()

    date = datetime.utcnow().strftime("%Y-%m-%d")
    recommendation_html = "Recommendation-%s-%s.html" % (uuid.uuid4(), date)
    column = ('Track Name', 'Recording MSID', 'Artist Name', 'Artist MSID', 'Release Name', 'Release MSID')
    context = {
        'recommendations' : recommendations,
        'column' : column,
        'total_time' : "%.2f" % ((time.time() - ti) / 3600),
        'time' : time_info,
        'best_model' : best_model_id,
        'all_recordings_count' : all_recordings_count,
    }
    utils.save_html(recommendation_html, context, 'recommend.html')