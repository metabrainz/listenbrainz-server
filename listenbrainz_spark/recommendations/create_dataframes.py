import os
import sys
import uuid
import logging
from time import time
from datetime import datetime

import listenbrainz_spark
from listenbrainz_spark import config
from listenbrainz_spark.stats import run_query
from listenbrainz_spark.recommendations import utils

from pyspark.sql.utils import AnalysisException, ParseException, QueryExecutionException

def prepare_user_data(table):
    """ Prepare users dataframe to select distinct user names and assign
        each user a unique integer id.

        Args:
            table: Registered dataframe to run SQL queries.

        Returns:
            users_df: users dataframe with columns as:
                ['user_id', 'user_name']
    """
    users_df = run_query("""
            SELECT user_name
                  , row_number() over (ORDER BY 'user_name') as user_id
             From (SELECT DISTINCT user_name FROM %s)
        """ % (table))
    return users_df

def prepare_listen_data(table):
    """ Prepare listens dataframe to select all the listens from the
        registered dataframe.

        Args:
            table: Registered dataframe to run SQL queries.

        Returns:
            listens_df: listens dataframe with columns as:
                ['listened_at', 'track_name', 'recording_msid', 'user_name']
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
            table: Registered dataframe to run SQL queries.

        Returns:
            recordings_df: recordings dataframe with columns as:
                ['track_name', 'recording_msid', 'artist_name', 'artist_msid',
                'release_name', 'release_msid', 'recording_id']
    """
    recordings_df = run_query("""
            SELECT track_name
                 , recording_msid
                 , artist_name
                 , artist_msid
                 , release_name
                 , release_msid
                 , row_number() over (ORDER BY 'recording_msid') AS recording_id
             From (SELECT DISTINCT recording_msid, track_name, artist_name, artist_msid,
                    release_name, release_msid FROM %s)
        """ % (table))
    return recordings_df

def get_playcounts_data(listens_df, users_df, recordings_df):
    """ Prepare playcounts dataframe by joining listens_df, users_df and
        recordings_df to select distinct tracks that a user has listened to
        for all the users along with listen count.

        Args:
            listens_df: Listens dataframe.
            users_df: Users dataframe.
            recordings_df: Recordings dataframe.

        Returns:
            playcounts_df: playcounts dataframe with columns as:
                ['user_id', 'recording_id', 'count']
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
    ti = time()
    try:
        listenbrainz_spark.init_spark_session('Create_Dataframe')
    except AttributeError as err:
        logging.error('Cannot initialize Spark Session: {} \n {}. Aborting...'.format(type(err).__name__,str(err)))
        sys.exit(-1)
    except Exception as err:
        logging.error('An error occurred while initializing Spark session: {} \n {}. Aborting...'.format(
            type(err).__name__,str(err)), exc_info=True)
        sys.exit(-1)

    df = None
    missing_parquets = []
    for y in range(config.STARTING_YEAR, config.ENDING_YEAR + 1):
        for m in range(config.STARTING_MONTH, config.ENDING_MONTH + 1):
            try:
                month = listenbrainz_spark.sql_context.read.parquet('{}/data/listenbrainz/{}/{}.parquet'.format             (config.HDFS_CLUSTER_URI, y, m))
                df = df.union(month) if df else month
            except AnalysisException as err:
                missing_parquets.append('{}-{}'.format(y, '{:02d}'.format(m)))
                logging.error('Cannot read parquet files from HDFS: {} \n {}'.format(type(err).__name__,str(err)))
                continue
            except Exception as err:
                logging.error('An error occured while fetching \"/data/listenbrainz/{}/{}.parquet\": {} \n {}.              Aborting...'.format(y, m, type(err).__name__, str(err)), exc_info=True)
                sys.exit(-1)

    if not df:
        raise SystemExit("Parquet files from {}-{} to {}-{} are empty".format(config.STARTING_YEAR,'{:02d}'.format(         config.STARTING_MONTH), config.ENDING_YEAR, '{:02d}'.format(config.ENDING_MONTH)))

    logging.info('Registering Dataframe...')
    table = 'df_to_train_{}'.format(datetime.strftime(datetime.utcnow(), '%Y_%m_%d'))
    try:
        df.createOrReplaceTempView(table)
    except AnalysisException as err:
        logging.error('Cannot register dataframe: {} \n {}. Aborting...'.format(type(err).__name__, str(err)))
        sys.exit(-1)
    except Exception as err:
        logging.error('An error occured while registering dataframe: {} \n {}. Aborting...'.format(type(err).__name__,      str(err)), exc_info=True)
        sys.exit(-1)
    t = '{:.2f}'.format(time() - ti)
    logging.info('Files fectched from HDFS and dataframe registered in {}s'.format(t))

    dest_path = os.path.join(config.HDFS_CLUSTER_URI, 'data', 'listenbrainz', 'recommendation-engine',                      'dataframes')

    logging.info('Preparing users data and saving to HDFS...')
    try:
        t0 = time()
        users_df = prepare_user_data(table)
        users_df.write.format('parquet').save(dest_path + '/users_df.parquet', mode='overwrite')
    except QueryExecutionException as err:
        logging.error('Failed to execute users query: {} \n {}. Aborting...'.format(type(err).__name__, str(err)))
        sys.exit(-1)
    except AnalysisException as err:
        logging.error('Failed to analyse users query plan: {} \n {}. Aborting...'.format(type(err).__name__, str(err)))
        sys.exit(-1)
    except ParseException as err:
        logging.error("Failed to parse SQL command: {} \n {}. Aborting...".format(type(err).__name__, str(err)))
        sys.exit(-1)
    except Exception as err:
        logging.error('An error occurred while executing users query: {} \n {}. Aborting'.format(type(err).__name__,        str(err)), exc_info=True)
        sys.exit(-1)
    users_df_time = '{:.2f}'.format((time() - t0) / 60)

    logging.info('Preparing recordings data and saving to HDFS...')
    try:
        t0 = time()
        recordings_df = prepare_recording_data(table)
        recordings_df.write.format('parquet').save(dest_path + '/recordings_df.parquet', mode='overwrite')
    except QueryExecutionException as err:
        logging.error('Failed to execute recordings query: {} \n {}. Aborting...'.format(type(err).__name__, str(err)))
        sys.exit(-1)
    except AnalysisException as err:
        logging.error('Failed to analyse recordings query plan: {} \n {}. Aborting...'.format(type(err).__name__,           str(err)))
        sys.exit(-1)
    except ParseException as err:
        logging.error('Failed to parse SQL command: {} \n {}. Aborting...'.format(type(err).__name__, str(err)))
        sys.exit(-1)
    except Exception as err:
        logging.error('An error occurred while executing recordings query: {} \n {}. Aborting...'.format(type(err)          .__name__, str(err)), exc_info=True)
        sys.exit(-1)
    recordings_df_time =  '{:.2f}'.format((time() - t0) / 60)

    logging.info('Preparing listen data dump and playcounts, saving playcounts to HDFS...')
    try:
        t0 = time()
        listens_df = prepare_listen_data(table)
        playcounts_df = get_playcounts_data(listens_df, users_df, recordings_df)
        playcounts_df.write.format('parquet').save(dest_path + '/playcounts_df.parquet', mode='overwrite')
    except QueryExecutionException as err:
        logging.error('Failed to execute playcounts query: {} \n {}. Aborting...'.format(type(err).__name__, str(err)))
        sys.exit(-1)
    except AnalysisException as err:
        logging.error('Failed to analyse playcounts query plan: {} \n {}. Aborting...'.format(type(err).__name__,
            str(err)))
        sys.exit(-1)
    except ParseException as err:
        logging.error('Failed to parse SQL command: {} \n {}. Aborting...'.format(type(err).__name__, str(err)))
        sys.exit(-1)
    except Exception as err:
        logging.error('An error occurred. {} \n {}. Aborting...'.format(type(err).__name__, str(err)), exc_info=True)
        sys.exit(-1)
    playcounts_df_time = '{:.2f}'.format((time() - t0) / 60)

    total_time = '{:.2f}'.format((time() - ti) / 60)
    lb_dump_time_window = ('{}-{}'.format(config.STARTING_YEAR, '{:02d}'.format(config.STARTING_MONTH)),
        '{}-{}'.format(config.ENDING_YEAR, '{:02d}'.format(config.ENDING_MONTH)))
    date = datetime.utcnow().strftime('%Y-%m-%d')
    queries_html = 'Queries-{}-{}.html'.format(uuid.uuid4(), date)
    context = {
        'users_df_time' : users_df_time,
        'recordings_df_time' : recordings_df_time,
        'playcounts_df_time' : playcounts_df_time,
        'lb_dump_time_window' : lb_dump_time_window,
        'missing_parquets' : missing_parquets,
        'total_time' : total_time
    }
    utils.save_html(queries_html, context, 'queries.html')
