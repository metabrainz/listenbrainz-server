"""
This script is responsible for processing user listening history, creating, and saving the dataframes to be used
in training the model. The general flow is as follows:

Get timestamp (from_date, to_date) to fetch user listening history. We fetch the timestamp (to_date) of latest listen in spark,
go back X days and get the updated timestamp (from_date) from where we should start fetching listens.
The timestamp of fetched listens belongs to [from_date.month, to_date.month]

The listens are fetched from HDFS and the listens without recording_mbid are removed to get partial_listens_df. This
dataframe is then filtered and listens from users whose total listen count is below a given threshold are removed.
The dataframe created is saved to HDFS.

Distinct users are filtered from partial_listens_df and each user is assigned a unique identification number called
 spark_user_id. The dataframe created is called users_df and is saved to HDFS.

Distinct recordings are filtered from partial_listens_df and each recording is assigned a unique identification number
 called the recording_id. The dataframe created is called recordings_df and is saved to HDFS.

recording_mbid and user_id are filtered from partial_listened_df. The dataframe created is called listens_df.

users_df, listens_df and recordings_df are used to get the number of times a user has listened to a recording for all users.
This number is called count. The dataframe created is called playcounts_df and is saved to HDFS.

A UUID is generated for every run of the script to identify dataframe metadata (users_count, recording_count etc).
The dataframe_id (UUID) along with dataframe metadata are stored to HDFS.

Note: All the dataframes except the dataframe_metadata overwrite the existing dataframes in HDFS.
"""

import logging
import time
from datetime import datetime, timezone

import pyspark.sql.functions as func
from markupsafe import Markup
from pyspark.sql.functions import rank, col
from pyspark.sql.window import Window

import listenbrainz_spark
from data.model.user_cf_recommendations_recording_message import UserCreateDataframesMessage
from listenbrainz_spark import path, utils, schema
from listenbrainz_spark.exceptions import (SparkSessionNotInitializedException,
                                           DataFrameNotAppendedException,
                                           DataFrameNotCreatedException,
                                           SparkException)
from listenbrainz_spark.recommendations.dataframe_utils import (get_dataframe_id,
                                                                save_dataframe,
                                                                get_dates_to_train_data)
from listenbrainz_spark.listens.data import get_listens_from_dump

logger = logging.getLogger(__name__)

# Some useful dataframe fields/columns.
# complete_listens_df, partial_listens_df: see listen_schema in schema.py
#
# listens_df:
#   [
#       'recording_mbid',
#       'user_id'
#   ]
#
# recordings_df:
#   [
#       'artist_credit_id',
#       'recording_mbid',
#       'recording_id',
#   ]
#
# users_df:
#   [
#       'user_id',
#       'spark_user_id'
#   ]
#
# playcounts_df:
#   [
#       'spark_user_id',
#       'recording_id',
#       'count'
#   ]

# where the zero line of our confidence function is
ZERO_POINT = 30

# listen counts are capped to this value
MAX_PLAYCOUNT = 20

# the playcount value to use if playcount = 1
ONE_PLAYCOUNT_CONFIDENCE = ZERO_POINT - MAX_PLAYCOUNT / 2


def save_dataframe_metadata_to_hdfs(metadata: dict, df_metadata_path: str):
    """ Save dataframe metadata.

        Args:
            metadata (dict): metadata dataframe to append.
            df_metadata_path (str): path where metadata dataframe should be saved.
    """
    # Convert metadata to row object.
    metadata_row = schema.convert_dataframe_metadata_to_row(metadata)
    try:
        # Create dataframe from the row object.
        dataframe_metadata = utils.create_dataframe(metadata_row, schema.dataframe_metadata_schema)
    except DataFrameNotCreatedException as err:
        logger.error(str(err), exc_info=True)
        raise

    try:
        # Append the dataframe to existing dataframe if already exists or create a new one.
        utils.append(dataframe_metadata, df_metadata_path)
    except DataFrameNotAppendedException as err:
        logger.error(str(err), exc_info=True)
        raise


def describe_listencount_transformer(use_transformed_listencounts):
    """ Returns a human-readable description of the algorithm used to transform listen counts """
    if use_transformed_listencounts:
        return Markup("""
        <table>
            <tr>
                <th>Playcount</th>
                <th>Transformed Listencount</th>
            </tr>
            <tr>
                <td>0</td>
                <td>0</td>
            </tr>
            <tr>
                <td>1</td>
                <td>20</td>
            </tr>
            <tr>
                <td>2 &lt;= x &lt;= 20</td>
                <td>x + 20</td>
            </tr>
            <tr>
                <td> &gt; 20</td>
                <td>50</td>
            </tr>
        </table>
    """)
    else:
        return "No transformation applied to listen counts"


def save_playcounts_df(listens_df, recordings_df, users_df, metadata, save_path):
    """ Save final dataframe of aggregated listen counts and transformed listen counts.

    First calculate listen counts of a user per recording, then apply a transformation on the
    listen count for tuning algorithms. For instance, The transformed listen counts will be passed
    to spark ALS algorithm as ratings which will use it to calculate confidence values.

        Args:
            listens_df (dataframe): Dataframe containing recording_mbids corresponding to a user.
            recordings_df (dataframe): Dataframe containing distinct recordings and corresponding
                                       mbids and names.
            users_df (dataframe): Dataframe containing user names and user ids.
            metadata (dict): metadata dataframe to append.
            save_path: path where playcounts_df should be saved.
    """
    # listens_df is joined with users_df on user_id.
    # The output is then joined with recording_df on recording_mbid.
    # The next step uses groupBy which create groups on spark_user_id and recording_id and counts the number of recording_ids.
    # This dataframe tells us about the number of times a user has listend to a particular track for all users.
    playcounts_df = listens_df.join(users_df, 'user_id', 'inner') \
                              .join(recordings_df, 'recording_mbid', 'inner') \
                              .groupBy('spark_user_id', 'recording_id') \
                              .agg(func.count('recording_id').alias('playcount'))
    playcounts_df.createOrReplaceTempView("playcounts")

    transformed_listencounts = listenbrainz_spark.session.sql(f"""
            SELECT spark_user_id
                 , recording_id
                 , playcount
                 , float(
                    CASE
                        WHEN playcount = 0 THEN 0
                        WHEN playcount = 1 THEN {ONE_PLAYCOUNT_CONFIDENCE}
                        ELSE {ZERO_POINT} + LEAST(playcount, 20)
                    END) AS transformed_listencount
              FROM playcounts
    """)

    metadata['playcounts_count'] = playcounts_df.count()
    save_dataframe(transformed_listencounts, save_path)


def get_threshold_listens_df(mapped_listens_df, mapped_listens_path: str, threshold: int):
    """ Threshold mapped listens dataframe

        Args:
            mapped_listens_df (dataframe): listens mapped with msid_mbid_mapping.
            mapped_listens_path: Path to store mapped listens.
            threshold: minimum number of listens a user should have to be saved in the dataframe.
        Returns:
             threshold_listens_df: mapped listens dataframe after dropping data below threshold
    """
    threshold_users_df = mapped_listens_df \
        .groupBy('user_id') \
        .agg(func.count('user_id').alias('listen_count')) \
        .where('listen_count > {}'.format(threshold)) \
        .collect()
    threshold_users = [x.user_id for x in threshold_users_df]
    threshold_listens_df = mapped_listens_df.where(col('user_id').isin(threshold_users))
    save_dataframe(threshold_listens_df, mapped_listens_path)
    return threshold_listens_df


def get_listens_df(mapped_listens_df, metadata):
    """ Prepare listens dataframe.

        Args:
            mapped_listens_df (dataframe): listens mapped with msid_mbid_mapping.

        Returns:
            listens_df : Dataframe containing recording_mbids corresponding to a user.
    """
    listens_df = mapped_listens_df.select('recording_mbid', 'user_id')
    metadata['listens_count'] = listens_df.count()
    return listens_df


def get_recordings_df(mapped_listens_df, metadata, save_path):
    """ Prepare recordings dataframe.

        Args:
            mapped_listens_df (dataframe): listens mapped with msid_mbid_mapping.
            save_path (str): path where recordings_df should be saved

        Returns:
            recordings_df: Dataframe containing distinct recordings and corresponding
                mbids and names.
    """
    recording_window = Window.orderBy('recording_mbid')

    recordings_df = mapped_listens_df \
        .select(
            'artist_credit_id',
            'recording_mbid',
        ) \
        .distinct() \
        .withColumn('recording_id', rank().over(recording_window))

    metadata['recordings_count'] = recordings_df.count()
    save_dataframe(recordings_df, save_path)
    return recordings_df


def get_users_dataframe(mapped_listens_df, metadata, save_path):
    """ Prepare users dataframe

        Args:
            mapped_listens_df (dataframe): listens mapped with msid_mbid_mapping.
            save_path (str): path where users_df should be saved

        Returns:
            users_df : Dataframe containing user names and user ids.
    """
    # We use window function to give rank to distinct user_names
    # Note that if user_names are not distinct rank would repeat and give unexpected results.
    user_window = Window.orderBy('user_id')
    users_df = mapped_listens_df.select('user_id').distinct() \
                                .withColumn('spark_user_id', rank().over(user_window))

    metadata['users_count'] = users_df.count()
    save_dataframe(users_df, save_path)
    return users_df


def calculate_dataframes(from_date, to_date, job_type, minimum_listens_threshold):
    if job_type == "recommendation_recording":
        paths = {
            "mapped_listens": path.RECOMMENDATION_RECORDING_MAPPED_LISTENS,
            "playcounts": path.RECOMMENDATION_RECORDING_TRANSFORMED_LISTENCOUNTS_DATAFRAME,
            "recordings": path.RECOMMENDATION_RECORDINGS_DATAFRAME,
            "users": path.RECOMMENDATION_RECORDING_USERS_DATAFRAME,
            "metadata": path.RECOMMENDATION_RECORDING_DATAFRAME_METADATA,
            "prefix": "listenbrainz-dataframe-recording-recommendations"
        }
    elif job_type == "similar_users":
        paths = {
            "mapped_listens": path.USER_SIMILARITY_MAPPED_LISTENS,
            "playcounts": path.USER_SIMILARITY_PLAYCOUNTS_DATAFRAME,
            "recordings": path.USER_SIMILARITY_RECORDINGS_DATAFRAME,
            "users": path.USER_SIMILARITY_USERS_DATAFRAME,
            "metadata": path.USER_SIMILARITY_METADATA_DATAFRAME,
            "prefix": "listenbrainz-dataframe-user-similarity"
        }
    else:
        raise SparkException("Invalid job_type parameter received for creating dataframes: " + job_type)

    # dict to save dataframe metadata which would be later merged in model_metadata dataframe.
    # "updated" should always be set to False in this script.
    metadata = {'updated': False, 'to_date': to_date, 'from_date': from_date}

    complete_listens_df = get_listens_from_dump(from_date, to_date)
    logger.info(f'Listen count from {from_date} to {to_date}: {complete_listens_df.count()}')

    logger.info('Discarding listens without mbids...')
    partial_listens_df = complete_listens_df.where(col('recording_mbid').isNotNull())
    logger.info(f'Listen count after discarding: {partial_listens_df.count()}')

    logger.info('Thresholding listens...')
    threshold_listens_df = get_threshold_listens_df(
        partial_listens_df,
        paths["mapped_listens"],
        minimum_listens_threshold
    )
    logger.info(f'Listen count after thresholding: {threshold_listens_df.count()}')

    logger.info('Preparing users data and saving to HDFS...')
    users_df = get_users_dataframe(threshold_listens_df, metadata, paths["users"])

    logger.info('Preparing recordings data and saving to HDFS...')
    recordings_df = get_recordings_df(threshold_listens_df, metadata, paths["recordings"])

    logger.info('Preparing listen data dump and playcounts, saving playcounts to HDFS...')
    listens_df = get_listens_df(threshold_listens_df, metadata)

    save_playcounts_df(listens_df, recordings_df, users_df, metadata, paths["playcounts"])

    metadata['dataframe_id'] = get_dataframe_id(paths["prefix"])
    save_dataframe_metadata_to_hdfs(metadata, paths["metadata"])
    return complete_listens_df


def main(train_model_window, job_type, minimum_listens_threshold=0):
    ti = time.monotonic()
    logger.info('Fetching listens to create dataframes...')
    to_date, from_date = get_dates_to_train_data(train_model_window)
    calculate_dataframes(from_date, to_date, job_type, minimum_listens_threshold)
    total_time = '{:.2f}'.format((time.monotonic() - ti) / 60)

    return [
        UserCreateDataframesMessage(
            type='cf_recommendations_recording_dataframes',
            dataframe_upload_time=str(datetime.now(timezone.utc)),
            total_time=total_time,
            from_date=str(from_date.strftime('%b %Y')),
            to_date=str(to_date.strftime('%b %Y')),
        ).dict()
    ]
