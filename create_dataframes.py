import listenbrainz_spark
import os
import sys
import logging
import time

from listenbrainz_spark import config
from pyspark.sql import Row, SparkSession
from datetime import datetime
from listenbrainz_spark.stats import run_query
from listenbrainz_spark.recommendations import train_models, recommend
from time import sleep

def prepare_user_data(table):
    t0 = time.time()
    users_df = run_query("""
            SELECT user_name
                  , row_number() over (ORDER BY "user_name") as user_id
             From (SELECT DISTINCT user_name FROM %s)
        """ % (table))
    print("Number of rows in users df: ",users_df.count())
    t = "%.2f" % (time.time() - t0)
    print("Users data prepared in %ss" % (t))
    return users_df

def prepare_listen_data(table):
    t0 = time.time()
    listens_df = run_query("""
            SELECT listened_at
                 , track_name
                 , recording_msid
                 , user_name
             From %s
        """ % (table))
    print("Number of rows in listens df:",listens_df.count())
    t = "%.2f" % (time.time() - t0)
    print("Listens data prepared in %ss" % (t))
    return listens_df

def prepare_recording_data(table):
    t0 = time.time()
    recordings_df = run_query("""
            SELECT track_name
                 , recording_msid
                 , artist_name
                 , artist_msid
                 , release_name
                 , release_msid
                 , row_number() over (ORDER BY "recording_msid") AS recording_id
             From (SELECT DISTINCT recording_msid, track_name, artist_name, artist_msid, release_name, release_msid FROM %s)
        """ % (table))
    print("Number of rows in recording df:",recordings_df.count())
    t = "%.2f" % (time.time() - t0)
    print("Recording data prepared in %ss" % (t))
    return recordings_df

def get_playcounts_data(listens_df, users_df, recordings_df):
    t0 = time.time()
    listens_df.createOrReplaceTempView('listen')
    users_df.createOrReplaceTempView('user')
    recordings_df.createOrReplaceTempView('recording')
    playcounts_df = run_query("""
        SELECT user_id,
               recording_id,
               count(recording_id) as count
          FROM listen
    INNER JOIN user
            ON listen.user_name = user.user_name
    INNER JOIN recording
            ON recording.recording_msid = listen.recording_msid
      GROUP BY user_id, recording_id
      ORDER BY user_id
    """)
    print("Number of rows in playcounts df:",playcounts_df.count())
    t = "%.2f" % (time.time() - t0)
    print("Playcount data prepared in %ss" % (t))
    return playcounts_df

if __name__ == '__main__':

    t0 = time.time()
    listenbrainz_spark.init_spark_session('Create_Dataframe')
    df = None
    for y in range(config.starting_year, config.ending_year + 1):
        for m in range(config.starting_month, config.ending_month + 1):
            try:
                month = listenbrainz_spark.sql_context.read.parquet('{}/data/listenbrainz/{}/{}.parquet'.format(config.HDFS_CLUSTER_URI, y, m))
                df = df.union(month) if df else month
            except Exception as err:
                logging.error("Cannot read files from HDFS: %s / %s. Aborting." % (type(err).__name__, str(err)))
                continue

    df.printSchema()
    print("Registering Dataframe...")
    date = datetime.utcnow()
    table = 'df_to_train_{}'.format(datetime.strftime(date, '%Y_%m_%d'))
    df.createOrReplaceTempView(table)
    t = "%.2f" % (time.time() - t0)
    print("Dataframe registered in %ss" % (t))

    print("Preparing user data...")
    users_df = prepare_user_data(table)
    print("Load data dump...")
    listens_df = prepare_listen_data(table)
    print("Prepare recording dump...")
    recordings_df = prepare_recording_data(table)
    print("Get playcounts...")
    playcounts_df = get_playcounts_data(listens_df, users_df, recordings_df)
    lb_dump_time_window = ("{}-{}".format(config.starting_year, "%02d" % config.starting_month), "{}-{}".format(config.ending_year, "%02d" % config.ending_month))

    for attempt in range(config.MAX_RETRIES):
        try:
            train_models.main(playcounts_df, lb_dump_time_window)
            break
        except Exception as err:
            sleep(config.TIME_BEFORE_RETRIES)
            if attempt == config.MAX_RETRIES - 1:
                raise SystemExit("%s.Aborting..." % (str(err)))
            logging.error("Unable to train the model: %s. Retrying in %ss." % (type(err).__name__,config.TIME_BEFORE_RETRIES))
    recommend.main(users_df, playcounts_df, recordings_df, t0)
