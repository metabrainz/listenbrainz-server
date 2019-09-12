import os
import sys
import uuid
import logging
from time import time
from datetime import datetime
from py4j.protocol import Py4JJavaError

import listenbrainz_spark
from listenbrainz_spark import path
from listenbrainz_spark import stats
from listenbrainz_spark import utils
from listenbrainz_spark import config
from listenbrainz_spark.exceptions import SQLException, FileNotSavedException, FileNotFetchedException, ViewNotRegisteredException, SparkSessionNotInitializedException
from listenbrainz_spark.recommendations.utils import save_html
from listenbrainz_spark.sql import create_dataframes_queries as sql

from pyspark.sql.utils import AnalysisException

# dataframe html is generated when set to true
SAVE_DATAFRAME_HTML = False

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

def get_listens_for_training_model_window():
    """  Prepare dataframe of listens of X days to train. Here X is a config value.

        Returns:
            training_df (dataframe): Columns can de depicted as:
                [
                    artist_mbids, artist_msid, artist_name, listened_at, recording_mbid,
                    recording_msid, release_mbid, release_msid, release_name, tags, track_name, user_name
                ]
    """
    to_date = datetime.utcnow()
    from_date = stats.adjust_days(to_date, config.TRAIN_MODEL_WINDOW)
    # shift to the first of the month
    from_date = stats.replace_days(from_date, 1)

    try:
        training_df = utils.get_listens(from_date, to_date)
    except ValueError:
        raise
    except FileNotFetchedException:
        raise
    return training_df

def main():
    ti = time()
    try:
        listenbrainz_spark.init_spark_session('Create Dataframes')
    except SparkSessionNotInitializedException:
        raise

    df = get_listens_for_training_model_window()

    if not df:
        logging.error('Parquet files containing listening history of past {} days missing form HDFS'.format(
            config.TRAIN_MODEL_WINDOW))
        sys.exit(-1)

    logging.info('Registering Dataframe...')
    table = 'df_to_train_{}'.format(datetime.strftime(datetime.utcnow(), '%Y_%m_%d'))
    try:
        utils.register_dataframe(df, table)
    except ViewNotRegisteredException:
        raise
    logging.info('Files fetched from HDFS and dataframe registered in {}s'.format('{:.2f}'.format(time() - ti)))

    logging.info('Preparing users data and saving to HDFS...')
    t0 = time()
    try:
        users_df = sql.prepare_user_data(table)
    except SQLException:
        raise

    try:
        utils.save_parquet(users_df, path.USERS_DATAFRAME_PATH)
    except FileNotSavedException:
        raise
    users_df_time = '{:.2f}'.format((time() - t0) / 60)

    logging.info('Preparing recordings data and saving to HDFS...')
    t0 = time()
    try:
        recordings_df = sql.prepare_recording_data(table)
    except SQLException:
        raise

    try:
        utils.save_parquet(recordings_df, path.RECORDINGS_DATAFRAME_PATH)
    except FileNotSavedException:
        raise
    recordings_df_time = '{:.2f}'.format((time() - t0) / 60)

    logging.info('Preparing listen data dump and playcounts, saving playcounts to HDFS...')
    t0 = time()
    try:
        listens_df = sql.prepare_listen_data(table)
    except SQLException:
        raise

    try:
        utils.register_dataframe(listens_df, 'listen')
        utils.register_dataframe(users_df, 'user')
        utils.register_dataframe(recordings_df, 'recording')
    except ViewNotRegisteredException:
        raise

    try:
        playcounts_df = sql.get_playcounts_data()
    except SQLException:
        raise

    try:
        utils.save_parquet(playcounts_df, path.PLAYCOUNTS_DATAFRAME_PATH)
    except FileNotSavedException:
        raise
    playcounts_df_time = '{:.2f}'.format((time() - t0) / 60)
    total_time = '{:.2f}'.format((time() - ti) / 60)

    if SAVE_DATAFRAME_HTML:
        save_dataframe_html(users_df_time, recordings_df_time, playcounts_df_time, total_time)
