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

def recommend_user(user_name, model, recordings_map):
    user_id = get_user_id(user_name)
    user_playcounts = run_query("""
        SELECT user_id,
               recording_id,
               count
          FROM playcount
         WHERE user_id = %d
    """ % user_id)

    user_recordings = user_playcounts.rdd.map(lambda r: r['recording_id'])
    user_recordings.count()
    all_recordings =  recordings_map.keys()
    all_recordings.count()
    candidate_recordings = all_recordings.subtract(user_recordings)
    candidate_recordings.count()
    t0 = time.time()
    recommendations = model.predictAll(candidate_recordings.map(lambda recording: (user_id, recording))).takeOrdered(50, lambda product: -product.rating)
    recommended_recordings = [recordings_map.lookup(recommendations[i].product)[0] for i in range(len(recommendations))]
    t = "%.2f" % (time.time() - t0)
    return recommended_recordings, t

def main(users_df, playcounts_df, recordings_df, t0):
    users_df.createOrReplaceTempView('user')
    playcounts_df.createOrReplaceTempView('playcount')
    recordings_map = recordings_df.rdd.map(lambda r: (r['recording_id'], [r['track_name'], r['recording_msid'], r['artist_name'], r['artist_msid'], r['release_name'], r["release_msid"]]))
    recordings_map.count()
    date = datetime.utcnow().strftime("%Y-%m-%d")
    path = os.path.join('/', 'data', 'listenbrainz', 'listenbrainz-recommendation-mode-{}'.format(date))
    
    print("Loading model...")
    for attempt in range(config.MAX_RETRIES):
        try:
            model = load_model(config.HDFS_CLUSTER_URI + path)
            break
        except Exception as err:
            sleep(config.TIME_BEFORE_RETRIES)
            if attempt == config.MAX_RETRIES - 1:
                raise SystemExit("%s.Aborting..." % (str(err)))
            logging.error("Unable to load model: %s.Retrying in %ss" % (type(err).__name__, config.TIME_BEFORE_RETRIES))

    path = os.path.join(os.path.dirname(os.path.abspath(__file__)),'users.json')
    with open(path) as f:
        users = json.load(f)
        num_users = len(users['user_name'])
        recommendations = []
        for user_name in users['user_name']:
            try:
                recommended_recordings, t = recommend_user(user_name, model, recordings_map)
                print("Recommendations for %s generated" % (user_name))
                recommendations.append((user_name, t, recommended_recordings))
            except TypeError as err:
                logging.error("%s: Invalid user name. User \"%s\" does not exist." % (type(err).__name__,user_name))
            except Exception as err:
                logging.error("Recommendations for \"%s\" not generated.%s" % (user_name, str(err)))

    column = ['Track Name', 'Recording MSID', 'Artist Name', 'Artist MSID', 'Release Name', 'Release MSID']
    outputfile = 'Recommendations-%s.html' % (date)
    context = {
        'num_users' : num_users,
        'recommendations' : recommendations,
        'column' : column,
        'total_time' : int(time.time() - t0),
        'date' : date,
    }
    utils.save_html(outputfile, context, 'recommend.html')
    
            
            