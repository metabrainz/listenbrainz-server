import os
import sys
import uuid
import logging
from time import time
from datetime import datetime
from py4j.protocol import Py4JJavaError

import listenbrainz_spark
from listenbrainz_spark import path, stats, utils, config, schema
from listenbrainz_spark.recommendations.utils import save_html
from listenbrainz_spark.exceptions import SQLException, FileNotSavedException, FileNotFetchedException, \
    SparkSessionNotInitializedException, DataFrameNotAppendedException, DataFrameNotCreatedException

from flask import current_app
import pyspark.sql.functions as func
from pyspark.sql.window import Window
from pyspark.sql.functions import rank
from pyspark.sql.utils import AnalysisException

# dataframe html is generated when set to true
SAVE_DATAFRAME_HTML = True

def generate_best_model_id(metadata):
    """ Generate best model id.
    """
    metadata['model_id'] = '{}-{}'.format(config.MODEL_ID_PREFIX, uuid.uuid4())

def save_dataframe(df, dest_path):
    """ Save dataframe to HDFS.

        Args:
            df (dataframe): Dataframe to save.
            dest_path (str): HDFS path to save dataframe.
    """
    try:
        utils.save_parquet(df, dest_path)
    except FileNotSavedException as err:
        current_app.logger.error(str(err), exc_info=True)
        sys.exit(-1)

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
        dataframe_metadata = utils.create_dataframe([metadata_row], schema.model_metadata_schema)
    except DataFrameNotCreatedException as err:
        current_app.logger.error(str(err), exc_info=True)
        sys.exit(-1)

    try:
        # Append the dataframe to existing dataframe if already exist or create a new one.
        utils.append(dataframe_metadata, path.MODEL_METADATA)
    except DataFrameNotAppendedException as err:
        current_app.logger.error(str(err), exc_info=True)
        sys.exit(-1)

def get_dates_to_train_data():
    """ Get window to fetch listens to train data.

        Returns:
            from_date (datetime): Date from which start fetching listens.
            to_date (datetime): Date upto which fetch listens.
    """
    to_date = datetime.utcnow()
    from_date = stats.adjust_days(to_date, config.TRAIN_MODEL_WINDOW)
    # shift to the first of the month
    from_date = stats.replace_days(from_date, 1)
    return to_date, from_date

def get_listens_for_training_model_window(to_date, from_date, metadata, dest_path):
    """  Prepare dataframe of listens of X days to train. Here X is a config value.

        Args:
            from_date (datetime): Date from which start fetching listens.
            to_date (datetime): Date upto which fetch listens.
            dest_path (str): HDFS path.

        Returns:
            A dataframe with columns as:
                [
                    artist_msid, artist_name, listened_at, recording_msid, release_mbid,
                    release_msid, release_name, tags, track_name, user_name
                ]
    """
    metadata['to_date'] = to_date
    metadata['from_date'] = from_date
    try:
        training_df = utils.get_listens(from_date, to_date, dest_path)
    except ValueError as err:
        current_app.logger.error(str(err), exc_info=True)
        sys.exit(-1)
    except FileNotFetchedException as err:
        current_app.logger.error(str(err), exc_info=True)
        sys.exit(-1)
    return utils.get_listens_without_artist_and_recording_mbids(training_df)

def get_mapped_artist_and_recording_mbids(partial_listens_df, recording_artist_mapping_df):
    """ Map recording msid->mbid and artist msid->mbids so that every listen has an mbid.

        Args:
            partial_listens_df (dataframe): Columns can be depicted as:
                [
                    'artist_msid', 'artist_name', 'listened_at', 'recording_msid', 'release_mbid',
                    'release_msid', 'release_name', 'tags', 'track_name', 'user_name'
                ]
            recording_artist_mapping_df (dataframe): Columns can be depicted as:
                [
                    'mb_artist_gids', 'msb_artist_msid', 'mb_recording_mbid', 'msb_recording_msid'
                ]

        Returns:
            mapped_df (dataframe): Dataframe with all the columns/fields that a typical listen has.
    """
    mapped_df = partial_listens_df.join(
        recording_artist_mapping_df,
            (partial_listens_df.recording_msid == recording_artist_mapping_df.msb_recording_msid) &
            (partial_listens_df.artist_msid == recording_artist_mapping_df.msb_artist_msid),
        'inner'
    )
    save_dataframe(mapped_df, path.MAPPED_LISTENS)
    return mapped_df

def get_playcounts_df(listens_df, recordings_df, users_df, metadata):
    """ Prepare playcounts dataframe.

        Args:
            listens_df (dataframe): Columns can be depicted as:
                [
                    'recording_mbid', 'user_name'
                ]
            recordings_df (dataframe): Columns can be depicted as:
                [
                    'recording_mbid', 'recording_id'
                ]
            users_df (dataframe): Columns can be depicted as:
                [
                    'user_name', 'user_id'
                ]
    """
    # listens_df is joined with users_df on user_name.
    # The output is then joined with recording_df on recording_mbid.
    # The final step uses groupBy which create groups on user_id and recording_id and count the number of recording_ids.
    # The final dataframe tells us about the number of times a user has listend to a particular track for all users.
    playcounts_df = listens_df.join(users_df, 'user_name', 'inner') \
        .join(recordings_df, 'mb_recording_gid', 'inner') \
        .groupBy('user_id', 'recording_id').agg(func.count('recording_id').alias('count'))

    metadata['playcounts_count'] = playcounts_df.count()
    save_dataframe(playcounts_df, path.PLAYCOUNTS_DATAFRAME_PATH)
    return playcounts_df

def get_listens_df(complete_listens_df, metadata):
    """ Prepare listens dataframe.

        Args:
            complete_listens_df (dataframe): Dataframe with all the columns/fields that a typical listen has.

        Returns:
            listens_df (dataframe): Columns can be depicted as:
                    [
                        'mb_recording_gid', 'user_name'
                    ]
    """
    listens_df = complete_listens_df.select('mb_recording_gid', 'user_name')
    metadata['listens_count'] = listens_df.count()
    return listens_df

def get_recordings_df(complete_listens_df, metadata):
    """ Prepare recordings dataframe.

        Args:
            complete_listens_df (dataframe): Dataframe with all the columns/fields that a typical listen has.

        Returns:
            recordings_df (dataframe): Columns can be depicted as:
                [
                    'mb_recording_gid', 'mb_artist_credit_id', 'recording_id'
                ]
    """
    recording_window = Window.orderBy('mb_recording_gid')
    recordings_df = complete_listens_df.select('mb_recording_gid', 'mb_artist_credit_id').distinct() \
        .withColumn('recording_id', rank().over(recording_window))

    metadata['recordings_count'] = recordings_df.count()
    save_dataframe(recordings_df, path.RECORDINGS_DATAFRAME_PATH)
    return recordings_df

def get_users_dataframe(complete_listens_df, metadata):
    """ Prepare users dataframe

        Args:
            complete_listens_df (dataframe): Dataframe with all the columns/fields that a typical listen has.

        Returns:
            users_df (dataframe): Columns can be depicted as:
                [
                    'user_name', 'user_id'
                ]
    """
    # We use window function to give rank to distinct user_names
    # Note that if user_names are not distinct rank would repeat and give unexpected results.
    user_window = Window.orderBy('user_name')
    users_df = complete_listens_df.select('user_name').distinct().withColumn('user_id', rank().over(user_window))

    metadata['users_count'] = users_df.count()
    save_dataframe(users_df, path.USERS_DATAFRAME_PATH)
    return users_df

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

    # Dataframe containing all columns except artist_mbids and recording_mbid
    to_date, from_date = get_dates_to_train_data()
    partial_listens_df = get_listens_for_training_model_window(to_date, from_date, metadata, path.LISTENBRAINZ_DATA_DIRECTORY)

    # Dataframe containing recording msid->mbid and artist msid->mbid mapping.
    recording_artist_mapping_df = utils.read_files_from_HDFS(path.RECORDING_ARTIST_MBID_MSID_MAPPING)

    # Dataframe containing all fields that a listen should have including artist_mbids and recording_msid.
    complete_listens_df = get_mapped_artist_and_recording_mbids(partial_listens_df, recording_artist_mapping_df)

    current_app.logger.info('Preparing users data and saving to HDFS...')
    t0 = time()
    users_df = get_users_dataframe(complete_listens_df, metadata)
    users_df_time = '{:.2f}'.format((time() - t0) / 60)

    current_app.logger.info('Preparing recordings data and saving to HDFS...')
    t0 = time()
    recordings_df = get_recordings_df(complete_listens_df, metadata)
    recordings_df_time = '{:.2f}'.format((time() - t0) / 60)

    current_app.logger.info('Preparing listen data dump and playcounts, saving playcounts to HDFS...')
    t0 = time()
    listens_df = get_listens_df(complete_listens_df, metadata)

    playcounts_df = get_playcounts_df(listens_df, recordings_df, users_df, metadata)
    playcounts_df_time = '{:.2f}'.format((time() - t0) / 60)
    total_time = '{:.2f}'.format((time() - ti) / 60)

    generate_best_model_id(metadata)
    save_dataframe_metadata_to_HDFS(metadata)

    if SAVE_DATAFRAME_HTML:
        save_dataframe_html(users_df_time, recordings_df_time, playcounts_df_time, total_time)
