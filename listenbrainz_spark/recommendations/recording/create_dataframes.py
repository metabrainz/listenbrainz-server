"""
This script is responsible for processing user listening history, creating, and saving the dataframes to be used
in training the model. The general flow is as follows:

Get timestamp (from_date, to_date) to fetch user listening history. We fetch the timestamp (to_date) of latest listen in spark,
go back X days and get the updated timestamp (from_date) from where we should start fetching listens.
The timestamp of fetched listens belongs to [from_date.month, to_date.month]

The listens are fetched from HDFS. We refer to dataframe of these listens as partial_listens_df since they have not been mapped to the
mapping yet!

The artist_name and track_name fields of partial_listens_df are converted to artist_name_matchable and track_name_matchable
respectively by removing accents, removing punctuations and whitespaces, and converting to lowercase.

The partial_listens_df is joined with mapping_df (msid->mbid mapping) on artist_name_matchable and track_name_matchable to
get the mapped_listens_df. The dataframe created is saved to HDFS.

Distinct users are filtered from mapped_listens_df and each user is assigned a unique identification number called user_id.
The dataframe created is called users_df and is saved to HDFS.

Distinct recordings are filtered from mapped_listens_df and each recording is assigned a unique identification number called the
recording_id. The dataframe created is called recordings_df and is saved to HDFS.

mb_recording_mbid and user_name is filtered from mapped_listened_df. The dataframe created is called listens_df.

users_df, listens_df and recordings_df are used to get the number of times a user has listened to a recording for all users.
This number is called count. The dataframe created is called playcounts_df and is saved to HDFS.

A UUID is generated for every run of the script to identify dataframe metadata (users_count, recording_count etc).
The dataframe_id (UUID) along with dataframe metadata are stored to HDFS.

Note: All the dataframes except the dataframe_metadata overwrite the existing dataframes in HDFS.
"""

import logging
import time
from datetime import datetime
from collections import defaultdict
from pydantic import ValidationError

import listenbrainz_spark
import listenbrainz_spark.utils.mapping as mapping_utils
from listenbrainz_spark import path, utils, schema
from listenbrainz_spark.exceptions import (SparkSessionNotInitializedException,
                                           DataFrameNotAppendedException,
                                           DataFrameNotCreatedException)

from data.model.user_missing_musicbrainz_data import UserMissingMusicBrainzDataRecord
from data.model.user_cf_recommendations_recording_message import (UserCreateDataframesMessage,
                                                                  UserMissingMusicBrainzDataMessage)

from listenbrainz_spark.recommendations.dataframe_utils import (get_dataframe_id,
                                                                save_dataframe,
                                                                get_dates_to_train_data,
                                                                get_mapped_artist_and_recording_mbids,
                                                                get_listens_for_training_model_window)
import pyspark.sql.functions as func
from pyspark.sql import Row
from pyspark.sql.window import Window
from pyspark.sql.functions import rank, col, row_number

# Some useful dataframe fields/columns.
# partial_listens_df:
#   [
#       'artist_msid',
#       'artist_mbids',
#       'artist_name',
#       'listened_at',
#       'recording_msid',
#       'recording_mbid'
#       'release_mbid',
#       'release_msid',
#       'release_name',
#       'tags',
#       'track_name',
#       'user_name'
#   ]
#
# mapped_listens_df:
#   [
#       'listened_at',
#       'mb_artist_credit_id',
#       'mb_artist_credit_mbids',
#       'mb_recording_mbid',
#       'mb_release_mbid',
#       'msb_artist_credit_name_matchable',
#       'msb_recording_name_matchable',
#       'user_name'
#   ]
#
# listens_df:
#   [
#       'recording_mbid',
#       'user_name'
#   ]
#
# recordings_df:
#   [
#       'mb_artist_credit_id',
#       'mb_artist_credit_mbids',
#       'mb_recording_mbid',
#       'mb_release_mbid',
#       'msb_artist_credit_name_matchable',
#       'msb_recording_name_matchable'
#   ]
#
# users_df:
#   [
#       'user_name',
#       'user_id'
#   ]
#
# playcounts_df:
#   [
#       'user_id',
#       'recording_id',
#       'count'
#   ]


# The following var defines the string of which the dataframe id is made up of.
# An UUID will be appended to the string to generate a dataframe id.
DATAFRAME_ID_PREFIX = 'listenbrainz-dataframe-recording-recommendations'


def save_dataframe_metadata_to_hdfs(metadata):
    """ Save dataframe metadata.
    """
    # Convert metadata to row object.
    metadata_row = schema.convert_dataframe_metadata_to_row(metadata)
    try:
        # Create dataframe from the row object.
        dataframe_metadata = utils.create_dataframe(metadata_row, schema.dataframe_metadata_schema)
    except DataFrameNotCreatedException as err:
        logging.error(str(err), exc_info=True)
        raise

    try:
        # Append the dataframe to existing dataframe if already exists or create a new one.
        utils.append(dataframe_metadata, path.RECOMMENDATION_RECORDING_DATAFRAME_METADATA)
    except DataFrameNotAppendedException as err:
        logging.error(str(err), exc_info=True)
        raise


def get_data_missing_from_musicbrainz(partial_listens_df, msid_mbid_mapping_df):
    """ Get data that has been submitted to ListenBrainz but is missing from MusicBrainz.

        Args:
            partial_listens_df (dataframe): dataframe of listens.
            msid_mbid_mapping_df (dataframe): msid->mbid mapping. For columns refer to
                                              msid_mbid_mapping_schema in listenbrainz_spark/schema.py

        Returns:
            missing_musicbrainz_data_itr (iterator): Data missing from the MusicBrainz.
    """
    condition = [
        partial_listens_df.track_name_matchable == msid_mbid_mapping_df.msb_recording_name_matchable,
        partial_listens_df.artist_name_matchable == msid_mbid_mapping_df.msb_artist_credit_name_matchable
    ]

    df = partial_listens_df.join(msid_mbid_mapping_df, condition, 'left') \
                           .select('artist_msid',
                                   'artist_name',
                                   'listened_at',
                                   'recording_msid',
                                   'release_msid',
                                   'release_name',
                                   'track_name',
                                   'user_name') \
                           .where(col('msb_recording_name_matchable').isNull() &
                                  col('msb_artist_credit_name_matchable').isNull())

    logging.info('Number of (artist, recording) pairs missing from mapping: {}'.format(df.count()))
    window = Window.partitionBy('user_name').orderBy(col('listened_at').desc())

    # limiting listens to 200 for each user so that messages don't drop
    # Also, we don't want to overwhelm users with the data that they
    # have submitted to LB and should consider submitting to MB.
    # The data will be sorted on "listened_at"

    missing_musicbrainz_data_itr = df.groupBy('artist_msid',
                                              'artist_name',
                                              'recording_msid',
                                              'release_msid',
                                              'release_name',
                                              'track_name',
                                              'user_name') \
        .agg(func.max('listened_at').alias('listened_at')) \
        .withColumn('rank', row_number().over(window)) \
        .where(col('rank') <= 200) \
        .toLocalIterator()

    return missing_musicbrainz_data_itr


def save_playcounts_df(listens_df, recordings_df, users_df, metadata):
    """ Prepare and save playcounts dataframe.

        Args:
            listens_df : Dataframe containing recording_mbids corresponding to a user.
            recordings_df : Dataframe containing distinct recordings and corresponding
                                       mbids and names.
            users_df : Dataframe containing user names and user ids.
    """
    # listens_df is joined with users_df on user_name.
    # The output is then joined with recording_df on recording_mbid.
    # The final step uses groupBy which create groups on user_id and recording_id and counts the number of recording_ids.
    # The final dataframe tells us about the number of times a user has listend to a particular track for all users.
    playcounts_df = listens_df.join(users_df, 'user_name', 'inner') \
                              .join(recordings_df, 'mb_recording_mbid', 'inner') \
                              .groupBy('user_id', 'recording_id') \
                              .agg(func.count('recording_id').alias('count'))

    metadata['playcounts_count'] = playcounts_df.count()
    save_dataframe(playcounts_df, path.RECOMMENDATION_RECORDING_PLAYCOUNTS_DATAFRAME)


def get_listens_df(mapped_listens_df, metadata):
    """ Prepare listens dataframe.

        Args:
            mapped_listens_df (dataframe): listens mapped with msid_mbid_mapping.

        Returns:
            listens_df : Dataframe containing recording_mbids corresponding to a user.
    """
    listens_df = mapped_listens_df.select('mb_recording_mbid', 'user_name')
    metadata['listens_count'] = listens_df.count()
    return listens_df


def get_recordings_df(mapped_listens_df, metadata):
    """ Prepare recordings dataframe.

        Args:
            mapped_listens_df (dataframe): listens mapped with msid_mbid_mapping.

        Returns:
            recordings_df: Dataframe containing distinct recordings and corresponding
                mbids and names.
    """
    recording_window = Window.orderBy('mb_recording_mbid')

    recordings_df = mapped_listens_df.select('mb_artist_credit_id',
                                             'mb_artist_credit_mbids',
                                             'mb_recording_mbid',
                                             'mb_release_mbid',
                                             'msb_artist_credit_name_matchable',
                                             'msb_recording_name_matchable') \
                                     .distinct() \
                                     .withColumn('recording_id', rank().over(recording_window))

    metadata['recordings_count'] = recordings_df.count()
    save_dataframe(recordings_df, path.RECOMMENDATION_RECORDINGS_DATAFRAME)
    return recordings_df


def get_users_dataframe(mapped_listens_df, metadata):
    """ Prepare users dataframe

        Args:
            mapped_listens_df (dataframe): listens mapped with msid_mbid_mapping.

        Returns:
            users_df : Dataframe containing user names and user ids.
    """
    # We use window function to give rank to distinct user_names
    # Note that if user_names are not distinct rank would repeat and give unexpected results.
    user_window = Window.orderBy('user_name')
    users_df = mapped_listens_df.select('user_name').distinct() \
                                .withColumn('user_id', rank().over(user_window))

    metadata['users_count'] = users_df.count()
    save_dataframe(users_df, path.RECOMMENDATION_RECORDING_USERS_DATAFRAME)
    return users_df


def prepare_messages(missing_musicbrainz_data_itr, from_date, to_date, ti):
    """ Create messages to send the data to the webserver via RabbitMQ

        Args:
            missing_musicbrainz_data_itr (iterator): Data missing from the MusicBrainz.
            from_date (datetime): Date from which start fetching listens.
            to_date (datetime): Date upto which fetch listens.
            ti (datetime): Timestamp when the first func (main) of the script was called.

        Returns:
            messages: A list of messages to be sent via RabbitMQ
    """

    missing_musicbrainz_data = defaultdict(list)

    current_ts = str(datetime.utcnow())

    for row in missing_musicbrainz_data_itr:
        try:
            missing_musicbrainz_data[row.user_name].append(UserMissingMusicBrainzDataRecord(**
                {
                    'artist_msid': row.artist_msid,
                    'artist_name': row.artist_name,
                    'listened_at': str(row.listened_at),
                    'recording_msid': row.recording_msid,
                    'release_msid': row.release_msid,
                    'release_name': row.release_name,
                    'track_name': row.track_name,
                }
            ).dict())
        except ValidationError:
            logging.warning("""Invalid entry present in missing musicbrainz data for user: {user_name}, skipping"""
                                       .format(user_name=row.user_name), exc_info=True)

    total_time = '{:.2f}'.format((time.monotonic() - ti) / 60)
    try:
        messages = [UserCreateDataframesMessage(**{
            'type': 'cf_recommendations_recording_dataframes',
            'dataframe_upload_time': current_ts,
            'total_time': total_time,
            'from_date': str(from_date.strftime('%b %Y')),
            'to_date': str(to_date.strftime('%b %Y')),
        }).dict()]
    except ValidationError:
        logging.warning("Invalid entry present in dataframe creation message", exc_info=True)

    for user_name, data in missing_musicbrainz_data.items():
        try:
            messages.append(UserMissingMusicBrainzDataMessage(**{
                'type': 'missing_musicbrainz_data',
                'musicbrainz_id': user_name,
                'missing_musicbrainz_data': data,
                'source': 'cf'
            }).dict())
        except ValidationError:
            logging.warning("ValidationError while calculating missing_musicbrainz_data for {user_name}."
                                       "\nData: {data}".format(user_name=user_name, data=data), exc_info=True)

    return messages


def main(train_model_window=None):

    ti = time.monotonic()
    # dict to save dataframe metadata which would be later merged in model_metadata dataframe.
    metadata = {}
    # "updated" should always be set to False in this script.
    metadata['updated'] = False
    try:
        listenbrainz_spark.init_spark_session('Create Dataframes')
    except SparkSessionNotInitializedException as err:
        logging.error(str(err), exc_info=True)
        raise

    logging.info('Fetching listens to create dataframes...')
    to_date, from_date = get_dates_to_train_data(train_model_window)

    metadata['to_date'] = to_date
    metadata['from_date'] = from_date

    partial_listens_df = get_listens_for_training_model_window(to_date, from_date, path.LISTENBRAINZ_DATA_DIRECTORY)
    logging.info('Listen count from {from_date} to {to_date}: {listens_count}'
                            .format(from_date=from_date, to_date=to_date, listens_count=partial_listens_df.count()))

    logging.info('Loading mapping from HDFS...')
    df = utils.read_files_from_HDFS(path.MBID_MSID_MAPPING)
    msid_mbid_mapping_df = mapping_utils.get_unique_rows_from_mapping(df)
    logging.info('Number of distinct rows in the mapping: {}'.format(msid_mbid_mapping_df.count()))

    logging.info('Mapping listens...')
    mapped_listens_df = get_mapped_artist_and_recording_mbids(partial_listens_df, msid_mbid_mapping_df,
                                                              path.RECOMMENDATION_RECORDING_MAPPED_LISTENS)
    logging.info('Listen count after mapping: {}'.format(mapped_listens_df.count()))

    logging.info('Preparing users data and saving to HDFS...')
    users_df = get_users_dataframe(mapped_listens_df, metadata)

    logging.info('Preparing recordings data and saving to HDFS...')
    recordings_df = get_recordings_df(mapped_listens_df, metadata)

    logging.info('Preparing listen data dump and playcounts, saving playcounts to HDFS...')
    listens_df = get_listens_df(mapped_listens_df, metadata)

    save_playcounts_df(listens_df, recordings_df, users_df, metadata)

    metadata['dataframe_id'] = get_dataframe_id(DATAFRAME_ID_PREFIX)
    save_dataframe_metadata_to_hdfs(metadata)

    logging.info('Preparing missing MusicBrainz data...')
    missing_musicbrainz_data_itr = get_data_missing_from_musicbrainz(partial_listens_df, msid_mbid_mapping_df)

    messages = prepare_messages(missing_musicbrainz_data_itr, from_date, to_date, ti)

    return messages
