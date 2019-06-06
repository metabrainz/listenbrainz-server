import listenbrainz_spark
import os
import sys
import logging
import time
import uuid

from pyspark.sql.utils import QueryExecutionException, AnalysisException, ParseException
from listenbrainz_spark import config
from datetime import datetime
from listenbrainz_spark.stats import run_query
from listenbrainz_spark.recommendations import utils

def prepare_user_data(table):
    """ Prepare users dataframe to select distinct user names
        and assign each user a unique integer id.

        Args: 
            table: Registered dataframe to run SQL queries

        Returns: 
            users_df: users dataframe with columns as:
                user_id, user_name
    """
    users_df = run_query("""
            SELECT user_name
                  , row_number() over (ORDER BY "user_name") as user_id
             From (SELECT DISTINCT user_name FROM %s)
        """ % (table))
    return users_df

def prepare_listen_data(table):
    """ Prepare listens dataframe to select all the listens from
        the registered dataframe.

        Args: 
            table: Registered dataframe to run SQL queries

        Returns:
            listens_df: listens dataframe with columns as:
                listened_at, track_name, recording_msid, user_name   
    """
    listens_df = run_query("""
            SELECT listened_at
                 , track_name
                 , recording_msid
                 , user_name
             From %s
        """ % (table))
    return listens_df

def prepare_recording_data(table):
    """ Prepare recordings dataframe to select distinct recordings/tracks
        listened to and assign each recording a unique integer id.

        Args: 
            table: Registered dataframe to run SQL queries

        Returns:
            recordings_df: recordings dataframe with columns as:
                track_name, recording_msid, artist_name, artist_msid, 
                release_name, release_msid, recording_id
    """
    recordings_df = run_query("""
            SELECT track_name
                 , recording_msid
                 , artist_name
                 , artist_msid
                 , release_name
                 , release_msid
                 , row_number() over (ORDER BY "recording_msid") AS recording_id
             From (SELECT DISTINCT recording_msid, track_name, artist_name, artist_msid, 
                    release_name, release_msid FROM %s)
        """ % (table))
    return recordings_df

def get_playcounts_data(listens_df, users_df, recordings_df):
    """ Prepare playcounts dataframe by joining listens_df, users_df,
        recordings_df to select distinct tracks that a user has listened to
        for all the users along with listen count.

        Args:
            listens_df: Listens dataframe
            users_df: Users dataframe
            recordings_df: Recordings dataframe

        Returns:
            playcounts_df: playcounts dataframe with columns as:
                user_id, recording_id, count
    """
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
    return playcounts_df

def main():
    ti = time.time()
    try:
        listenbrainz_spark.init_spark_session('Create_Dataframe')
    except AttributeError as err:
        logging.error("Cannot initialize Spark Session: %s \n %s. Aborting..." % (type(err).__name__,str(err)), exc_info=True)
        sys.exit(-1)
    except Exception as err:
        logging.error("An error occurred: %s \n %s. Aborting..." % (type(err).__name__,str(err)), exc_info=True)
        sys.exit(-1)

    df = None
    for y in range(config.STARTING_YEAR, config.ENDING_YEAR + 1):
        for m in range(config.STARTING_MONTH, config.ENDING_MONTH + 1):
            try:
                month = listenbrainz_spark.sql_context.read.parquet('{}/data/listenbrainz/{}/{}.parquet'.format(config.HDFS_CLUSTER_URI, y, m))
                df = df.union(month) if df else month
            except AnalysisException as err:
                logging.error("Cannot read files from HDFS: %s \n %s" % (type(err).__name__,str(err)))
            except Exception as err:
                logging.error("An error occured while fecthing parquet: %s \n %s." % (type(err).__name__, str(err)))
                continue
    if df is None:
        raise SystemExit("Parquet files containing listening history from {}-{} to {}-{} missing from HDFS".format(config.STARTING_YEAR, 
                    "%02d" % config.STARTING_MONTH, config.ENDING_YEAR, "%02d" % config.ENDING_MONTH))
    
    print("\nRegistering Dataframe...")
    table = 'df_to_train_{}'.format(datetime.strftime(datetime.utcnow(), '%Y_%m_%d'))
    try:
        df.createOrReplaceTempView(table)
    except Exception as err:
        logging.error("Cannot register dataframe: %s \n %s. Aborting..." % (type(err).__name__, str(err)), exc_info=True)
        sys.exit(-1)
    t = "%.2f" % (time.time() - ti)
    print("Files fectched from HDFS and dataframe registered in %ss" % (t))

    dest_path = os.path.join('/', 'data', 'listenbrainz', 'recommendation-engine', 'dataframes')

    print("Preparing user data and saving to HDFS...")
    try:
        t0 = time.time()
        users_df = prepare_user_data(table)
        users_df.write.format('parquet').save(config.HDFS_CLUSTER_URI + dest_path  + '/users_df.parquet', mode='overwrite')
    except QueryExecutionException as err:
        logging.error("Failed to execute users query: %s \n %s. Aborting..." % (type(err).__name__, str(err)))
        sys.exit(-1)
    except AnalysisException as err:
        logging.error("Failed to analyse users query plan: %s \n %s. Aborting..." % (type(err).__name__, str(err)))
        sys.exit(-1)
    except ParseException as err:
        logging.error("Failed to parse SQL command: %s \n %s. Aborting..." % (type(err).__name__, str(err)))
        sys.exit(-1)
    except Exception as err:
        logging.error("An error occurred. %s \n %s. Aborting" % (type(err).__name__, str(err)), exc_info=True)
        sys.exit(-1)
    users_df_time = "%.2f" % ((time.time() - t0) / 60)

    print("Preparing recordings data and saving to HDFS...")
    try:
        t0 = time.time()
        recordings_df = prepare_recording_data(table)
        recordings_df.write.format('parquet').save(config.HDFS_CLUSTER_URI + dest_path + '/recordings_df.parquet', mode='overwrite')
    except QueryExecutionException as err:
        logging.error("Failed to execute recordings query: %s \n %s. Aborting..." % (type(err).__name__, str(err)))
        sys.exit(-1)
    except AnalysisException as err:
        logging.error("Failed to analyse recordings query plan: %s \n %s. Aborting..." % (type(err).__name__, str(err)))
        sys.exit(-1)
    except ParseException as err:
        logging.error("Failed to parse SQL command: %s \n %s. Aborting..." % (type(err).__name__, str(err)))
        sys.exit(-1)
    except Exception as err:
        logging.error("An error occurred. %s \n %s. Aborting..." % (type(err).__name__, str(err)), exc_info=True)
        sys.exit(-1)
    recordings_df_time =  "%.2f" % ((time.time() - t0) / 60)

    print("Preparing listen data dump and playcounts, saving playcounts to HDFS...")
    try:
        t0 = time.time()
        listens_df = prepare_listen_data(table)
        playcounts_df = get_playcounts_data(listens_df, users_df, recordings_df)
        playcounts_df.write.format('parquet').save(config.HDFS_CLUSTER_URI + dest_path + '/playcounts_df.parquet', mode='overwrite')
    except QueryExecutionException as err:
        logging.error("Failed to execute playcounts query: %s \n %s. Aborting..." % (type(err).__name__, str(err)))
        sys.exit(-1)
    except AnalysisException as err:
        logging.error("Failed to analyse playcounts query plan: %s \n %s. Aborting..." % (type(err).__name__, str(err)))
        sys.exit(-1)
    except ParseException as err:
        logging.error("Failed to parse SQL command: %s \n %s. Aborting..." % (type(err).__name__, str(err)))
        sys.exit(-1)
    except Exception as err:
        logging.error("An error occurred. %s \n %s. Aborting..." % (type(err).__name__, str(err)), exc_info=True)
        sys.exit(-1)
    playcounts_df_time = "%.2f" % ((time.time() - t0) / 60)
    
    total_time = "%.2f" % ((time.time() - ti) / 60)
    lb_dump_time_window = ("{}-{}".format(config.STARTING_YEAR, "%02d" % config.STARTING_MONTH), 
                    "{}-{}".format(config.ENDING_YEAR, "%02d" % config.ENDING_MONTH))
    date = datetime.utcnow().strftime("%Y-%m-%d")
    queries_html = 'Queries-%s-%s.html' % (uuid.uuid4(), date)
    context = {
        'users_df_time' : users_df_time,
        'recordings_df_time' : recordings_df_time,
        'playcounts_df_time' : playcounts_df_time,
        'lb_dump_time_window' : lb_dump_time_window,
        'total_time' : total_time
    }
    utils.save_html(queries_html, context, 'queries.html')
    