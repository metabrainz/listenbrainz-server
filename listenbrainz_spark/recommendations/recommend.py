import sys
import os
import tempfile
import time
import listenbrainz_spark
import json
import logging

from pyspark.mllib.recommendation import MatrixFactorizationModel
from listenbrainz_spark import config
from datetime import datetime
from listenbrainz_spark.stats import run_query
from listenbrainz_spark.recommendations import utils
from time import sleep

def load_model(path):
    return MatrixFactorizationModel.load(listenbrainz_spark.context, path)

def get_user_id(user_name):
    result = run_query("""
        SELECT user_id
          FROM user
         WHERE user_name = '%s'
    """ % user_name)
    return result.first()['user_id']

def recommend_user(user_name, model, all_recordings, recordings_df):
    user_info = {}
    t0 = time.time()
    user_id = get_user_id(user_name)
    t = "%.2f" % ((time.time() - t0) / 60)
    user_info['get_user_id'] = t

    t0 = time.time()
    user_playcounts = run_query("""
        SELECT user_id,
               recording_id,
               count
          FROM playcount
         WHERE user_id = %d
    """ % user_id)
    t = "%.2f" % ((time.time() - t0) / 60)
    user_info['user-playcounts-time'] = t

    t0 = time.time()
    user_recordings = user_playcounts.rdd.map(lambda r: r['recording_id'])
    user_recordings_count = "{:,}".format(user_recordings.count())
    t = "%.2f" % ((time.time() - t0) / 60)
    user_info['user-recordings-time'] = t
    user_info['user-recordings-count'] = user_recordings_count

    t0 = time.time()
    candidate_recordings = all_recordings.subtract(user_recordings)
    candidate_recordings_count = "{:,}".format(candidate_recordings.count())
    t = "%.2f" % ((time.time() - t0) / 60)
    user_info['candidate-recordings-time'] = t
    user_info['candidate-recordings-count'] = candidate_recordings_count

    t0 = time.time()
    recommendations = model.predictAll(candidate_recordings.map(lambda recording: (user_id, recording))).takeOrdered(50, lambda product: -product.rating)
    recommended_recording_ids = [(recommendations[i].product) for i in range(len(recommendations))]
    t = "%.2f" % ((time.time() - t0) / 60)
    user_info['recommendations-time'] = t

    t0 = time.time()
    recommendations_df = recordings_df[recordings_df.recording_id.isin(recommended_recording_ids)].collect()
    t = "%.2f" % ((time.time() - t0) / 60)
    user_info['lookup-time'] = t

    recommended_recordings = []

    for row in recommendations_df:
        rec = (row.track_name, row.recording_msid, row.artist_name, row.artist_msid, row.release_name, row.release_msid)
        recommended_recordings.append(rec)

    user_info['recordings'] = recommended_recordings
    return user_info

def main(users_df, playcounts_df, recordings_df, ti, bestmodel_id):
    time_info = {}
    users_df.createOrReplaceTempView('user')
    playcounts_df.createOrReplaceTempView('playcount')

    t0 = time.time()
    all_recordings = recordings_df.rdd.map(lambda r: r['recording_id'])
    all_recordings_count = "{:,}".format(all_recordings.count())
    t = "%.2f" % ((time.time() - t0) / 60)
    time_info['all_recordings'] = t

    date = datetime.utcnow().strftime("%Y-%m-%d")
    path = os.path.join('/', 'data', 'listenbrainz', '{}'.format(bestmodel_id))
    
    print("Loading model...")
    for attempt in range(config.MAX_RETRIES):
        try:
            t0 = time.time()
            model = load_model(config.HDFS_CLUSTER_URI + path)
            t = "%.2f" % ((time.time() - t0) / 60)
            time_info['load_model'] = t
            break
        except Exception as err:
            sleep(config.TIME_BEFORE_RETRIES)
            if attempt == config.MAX_RETRIES - 1:
                raise SystemExit("%s.Aborting..." % (str(err)))
            logging.error("Unable to load model: %s.Retrying in %ss" % (str(err), config.TIME_BEFORE_RETRIES))

    path = os.path.join(os.path.dirname(os.path.abspath(__file__)),'users.json')
    ts = time.time()
    with open(path) as f:
        users = json.load(f)
        recommendations = {}
        for user_name in users['user_name']:
            try:
                t0 = time.time()
                user_info = recommend_user(user_name, model, all_recordings, recordings_df)
                t = "%.2f" % ((time.time() - t0) / 60)
                user_info['total-time'] = t
                print("Recommendations for %s generated" % (user_name))
                recommendations[user_name] = user_info
            except TypeError as err:
                logging.error("%s: Invalid user name. User \"%s\" does not exist." % (type(err).__name__,user_name))
            except Exception as err:
                logging.error("Recommendations for \"%s\" not generated.%s" % (user_name, str(err)))
    t = "%.2f" % ((time.time() - ts) / 3600)
    time_info['total_recommendation_time'] = t

    column = ('Track Name', 'Recording MSID', 'Artist Name', 'Artist MSID', 'Release Name', 'Release MSID')
    outputfile = 'Recommendations-%s.html' % (date)
    context = {
        'recommendations' : recommendations,
        'column' : column,
        'total_time' : "%.2f" % ((time.time() - ti) / 3600),
        'time' : time_info,
        'best_model' : bestmodel_id,
        'all_recordings_count' : all_recordings_count,
    }
    utils.save_html(outputfile, context, 'recommend.html')
    