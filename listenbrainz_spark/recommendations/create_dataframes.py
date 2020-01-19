import os
import sys
import uuid
import logging
from time import time
from datetime import datetime
from py4j.protocol import Py4JJavaError

import listenbrainz_spark
from listenbrainz_spark import path, schema
from listenbrainz_spark import stats
from listenbrainz_spark import utils
from listenbrainz_spark import config
from listenbrainz_spark.exceptions import SQLException, FileNotSavedException, FileNotFetchedException, ViewNotRegisteredException, \
    SparkSessionNotInitializedException, DataFrameNotAppendedException, DataFrameNotCreatedException
from listenbrainz_spark.recommendations.utils import save_html
from listenbrainz_spark.sql import create_dataframes_queries as sql

from flask import current_app
from pyspark.sql.utils import AnalysisException

# dataframe html is generated when set to true
SAVE_DATAFRAME_HTML = False

def generate_best_model_id(metadata):
    """ Generate best model id.
    """
    metadata['model_id'] = '{}-{}'.format(config.MODEL_ID_PREFIX, uuid.uuid4())

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

def save_dataframe_metadata_to_HDFS(metadata):
    """ Save dataframe metadata to model_metadata dataframe.
    """
    # Convert metadata to row object.
    metadata_row = schema.convert_model_metadata_to_row(metadata)
    try:
        # Create dataframe from the row object.
        dataframe_metadata = utils.create_dataframe(metadata_row, schema.model_metadata_schema)
    except DataFrameNotCreatedException as err:
        current_app.logger.error(str(err), exc_info=True)
        sys.exit(-1)
    try:
        # Append the dataframe to existing dataframe if already exist or create a new one.
        utils.append(dataframe_metadata, path.MODEL_METADATA)
    except DataFrameNotAppendedException as err:
        current_app.logger.error(str(err), exc_info=True)
        sys.exit(-1)

def get_listens_for_training_model_window(metadata):
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

    metadata['to_date'] = to_date
    metadata['from_date'] = from_date
    try:
        training_df = utils.get_listens(from_date, to_date, config.HDFS_CLUSTER_URI + path.LISTENBRAINZ_DATA_DIRECTORY)
    except ValueError as err:
        current_app.logger.error(str(err), exc_info=True)
        sys.exit(-1)
    except FileNotFetchedException as err:
        current_app.logger.error(str(err), exc_info=True)
        sys.exit(-1)
    return training_df

def main():
    ti = time()
    # dict to save dataframe metadata which would be later merged in model_metadata dataframe.
    metadata = {}
    # "updated" should always be set to False in this script.
    metadata['updated'] = False
    try:
        listenbrainz_spark.init_spark_session('Create Dataframes')
    except SparkSessionNotInitializedException as err:
        current_app.logger.error(str(err), exc_info=True)
        sys.exit(-1)

    df = get_listens_for_training_model_window(metadata)

    if not df:
        current_app.logger.error('Parquet files containing listening history of past {} days missing form HDFS'.format(
            config.TRAIN_MODEL_WINDOW))
        sys.exit(-1)

    current_app.logger.info('Registering Dataframe...')
    table = 'df_to_train_{}'.format(datetime.strftime(datetime.utcnow(), '%Y_%m_%d'))
    try:
        utils.register_dataframe(df, table)
    except ViewNotRegisteredException as err:
        current_app.logger.error(str(err), exc_info=True)
        sys.exit(-1)
    current_app.logger.info('Files fetched from HDFS and dataframe registered in {}s'.format('{:.2f}'.format(time() - ti)))

    current_app.logger.info('Preparing users data and saving to HDFS...')
    t0 = time()
    try:
        users_df = sql.prepare_user_data(table)
    except SQLException as err:
        current_app.logger.error(str(err), exc_info=True)
        sys.exit(-1)
    metadata['users_count'] = users_df.count()

    try:
        utils.save_parquet(users_df, path.USERS_DATAFRAME_PATH)
    except FileNotSavedException as err:
        current_app.logger.error(str(err), exc_info=True)
        sys.exit(-1)
    users_df_time = '{:.2f}'.format((time() - t0) / 60)

    current_app.logger.info('Preparing recordings data and saving to HDFS...')
    t0 = time()
    try:
        recordings_df = sql.prepare_recording_data(table)
    except SQLException as err:
        current_app.logger.error(str(err), exc_info=True)
        sys.exit(-1)
    metadata['recordings_count'] = recordings_df.count()

    try:
        utils.save_parquet(recordings_df, path.RECORDINGS_DATAFRAME_PATH)
    except FileNotSavedException as err:
        current_app.logger.error(str(err), exc_info=True)
        sys.exit(-1)
    recordings_df_time = '{:.2f}'.format((time() - t0) / 60)

    current_app.logger.info('Preparing listen data dump and playcounts, saving playcounts to HDFS...')
    t0 = time()
    try:
        listens_df = sql.prepare_listen_data(table)
    except SQLException as err:
        current_app.logger.error(str(err), exc_info=True)
        sys.exit(-1)
    metadata['listens_count'] = listens_df.count()

    try:
        utils.register_dataframe(listens_df, 'listen')
        utils.register_dataframe(users_df, 'user')
        utils.register_dataframe(recordings_df, 'recording')
    except ViewNotRegisteredException as err:
        current_app.logger.error(str(err), exc_info=True)
        sys.exit(-1)

    try:
        playcounts_df = sql.get_playcounts_data()
    except SQLException as err:
        current_app.logger.error(str(err), exc_info=True)
        sys.exit(-1)
    metadata['playcounts_count'] = playcounts_df.count()

    try:
        utils.save_parquet(playcounts_df, path.PLAYCOUNTS_DATAFRAME_PATH)
    except FileNotSavedException as err:
        current_app.logger.error(str(err), exc_info=True)
        sys.exit(-1)
    playcounts_df_time = '{:.2f}'.format((time() - t0) / 60)
    total_time = '{:.2f}'.format((time() - ti) / 60)

    generate_best_model_id(metadata)
    save_dataframe_metadata_to_HDFS(metadata)

    if SAVE_DATAFRAME_HTML:
        save_dataframe_html(users_df_time, recordings_df_time, playcounts_df_time, total_time)
