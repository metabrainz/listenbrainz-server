import os
import sys
import uuid
import logging
from time import time
from datetime import datetime
from py4j.protocol import Py4JJavaError

import listenbrainz_spark
from listenbrainz_spark import config, utils
from listenbrainz_spark.stats import adjusted_date
from listenbrainz_spark.exceptions import SQLException
from listenbrainz_spark.recommendations.utils import save_html
from listenbrainz_spark.sql import create_dataframes_queries as sql

from pyspark.sql.utils import AnalysisException

# dataframe html is generated when set to true
SAVE_DATAFRAME_HTML = True

def save_dataframe_html(users_df_time, recordings_df_time, playcounts_df_time, total_time):
    """ Prepare and save dataframe HTML.

        Args:
            users_df_time (str): Time taken to prepare and save users dataframe.
            recordings_df_time (str): Time taken to prepare and save recordings dataframe.
            playcounts_df_time (str): TIme taken to prepare and save playcounts dataframe.
            total_time (str): Time taken to execute the script.
    """
    date = datetime.utcnow().strftime('%Y-%m-%d')
    queries_html = 'Queries-{}-{}.html'.format(uuid.uuid4(), date)
    context = {
        'users_df_time' : users_df_time,
        'recordings_df_time' : recordings_df_time,
        'playcounts_df_time' : playcounts_df_time,
        'total_time' : total_time
    }
    save_html(queries_html, context, 'queries.html')

def training_data_window():
    # under the assumption that config.TRAIN_MODEL_WINDOW will always indicate months.
    training_df = None
    m = config.TRAIN_MODEL_WINDOW
    while m > 0:
        d = adjusted_date(-m)
        if d.month + m > 12:
            df = utils.get_listens(d.year, d.month, 13)
            training_df = training_df.union(df) if training_df else df
            m -= (13 - d.month)
        else:
            df = utils.get_listens(d.year, d.month, d.month + m)
            training_df = training_df.union(df) if training_df else df
            m -= (m - 1 + d.month)
    return training_df

def main():
    ti = time()
    try:
        listenbrainz_spark.init_spark_session('Create Dataframes')
    except AttributeError:
        logging.info('Aborting...')
        sys.exit(-1)

    try:
        df = training_data_window()
    except AttributeError:
        sys.exit(-1)

    if not df:
        logging.error('Parquet files containing listening history of past {} month(s) missing form HDFS'.format(
            config.TRAIN_MODEL_WINDOW))
        sys.exit(-1)

    logging.info('Registering Dataframe...')
    table = 'df_to_train_{}'.format(datetime.strftime(datetime.utcnow(), '%Y_%m_%d'))
    try:
        utils.register_dataframe(df, table)
    except AnalysisException:
        logging.info('Aborting...')
        sys.exit(-1)
    except AttributeError:
        logging.info('Aborting...')
        sys.exit(-1)
    logging.info('Files fetched from HDFS and dataframe registered in {}s'.format('{:.2f}'.format(time() - ti)))

    path = os.path.join(config.HDFS_CLUSTER_URI, 'data', 'listenbrainz', 'recommendation-engine', 'dataframes')

    logging.info('Preparing users data and saving to HDFS...')
    t0 = time()
    try:
        users_df = sql.prepare_user_data(table)
    except SQLException as err:
        logging.error('{}\nAborting...'.format(err))
        sys.exit(-1)

    try:
        utils.save_parquet(users_df, path + '/users_df.parquet')
    except Py4JJavaError:
        logging.info('Could not save users dataframe. Aborting...')
        sys.exit(-1)
    users_df_time = '{:.2f}'.format((time() - t0) / 60)

    logging.info('Preparing recordings data and saving to HDFS...')
    t0 = time()
    try:
        recordings_df = sql.prepare_recording_data(table)
    except SQLException as err:
        logging.error('{}\nAborting...'.format(err))
        sys.exit(-1)

    try:
        utils.save_parquet(recordings_df, path + '/recordings_df.parquet')
    except Py4JJavaError:
        logging.info('Could not save recordings dataframe. Aborting...')
        sys.exit(-1)
    recordings_df_time = '{:.2f}'.format((time() - t0) / 60)

    logging.info('Preparing listen data dump and playcounts, saving playcounts to HDFS...')
    t0 = time()
    try:
        listens_df = sql.prepare_listen_data(table)
    except SQLException as err:
        logging.error('{}\nAborting...'.format(err))
        sys.exit(-1)

    try:
        utils.register_dataframe(listens_df, 'listen')
        utils.register_dataframe(users_df, 'user')
        utils.register_dataframe(recordings_df, 'recording')
    except AnalysisException:
        logging.info('Aborting...')
        sys.exit(-1)
    except AttributeError:
        logging.info('Aborting...')
        sys.exit(-1)

    try:
        playcounts_df = sql.get_playcounts_data()
        playcounts_df.write.format('parquet').save(path + '/playcounts_df.parquet', mode='overwrite')
    except SQLException as err:
        logging.error('{}\nAborting...'.format(err))
        sys.exit(-1)

    try:
        utils.save_parquet(playcounts_df, path + '/playcounts_df.parquet')
    except Py4JJavaError:
        logging.info('Could not save playcounts dataframe. Aborting...')
        sys.exit(-1)
    playcounts_df_time = '{:.2f}'.format((time() - t0) / 60)
    total_time = '{:.2f}'.format((time() - ti) / 60)

    if SAVE_DATAFRAME_HTML:
        save_dataframe_html(users_df_time, recordings_df_time, playcounts_df_time, total_time)
