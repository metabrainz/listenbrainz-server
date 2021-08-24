import time
from collections import defaultdict
from datetime import datetime

import listenbrainz_spark.utils as utils
from listenbrainz_spark.exceptions import HDFSException
from listenbrainz_spark.path import LISTENBRAINZ_DATA_DIRECTORY, MBID_MSID_MAPPING
from listenbrainz_spark.stats import offset_days, offset_months, run_query


def get_latest_listen_ts():
    """ Get the timestamp of the latest timestamp present in spark cluster """
    now = datetime.now()
    while True:
        try:
            df = utils.get_listens(now, now, LISTENBRAINZ_DATA_DIRECTORY)
            break
        except HDFSException:
            now = offset_months(now, 1)

    df.createOrReplaceTempView('latest_listen_ts')
    result = run_query("SELECT MAX(listened_at) as max_timestamp FROM latest_listen_ts")
    rows = result.collect()
    return rows[0]['max_timestamp']


def filter_listens(df, from_date, to_date):
    """
    Filter the given dataframe to return listens which lie between from_date and to_date

    Args:
        df: Dataframe which has to filtered
        from_time(datetime): Start date
        to_time(datetime): End date

    Returns:
        result: DateFrame with listens which lie beween from_date and to_date
    """
    result = df.filter(df.listened_at.between(from_date, to_date))
    return result


def get_last_monday(date: datetime) -> datetime:
    """ Get date for Monday before 'date' """
    return offset_days(date, date.weekday())


def create_mapped_dataframe(listens_df):
    """
    Use artist credit recording pair from MSID-MBID mapping to improve stats quality

    Args:
        listens_df: The DataFrame to perform mapping upon

    Returns:
        result: DataFrame consisting of mapped list of listens
    """
    # Fetch mapping from HDFS
    msid_mbid_mapping_df = utils.get_unique_rows_from_mapping(utils.read_files_from_HDFS(MBID_MSID_MAPPING))

    # Create matchable fields from listens table
    matchable_df = utils.convert_text_fields_to_matchable(listens_df)

    join_condition = [
        listens_df.track_name_matchable == msid_mbid_mapping_df.msb_recording_name_matchable,
        listens_df.artist_name_matchable == msid_mbid_mapping_df.msb_artist_credit_name_matchable
    ]
    intermediate_df = listens_df.join(msid_mbid_mapping_df, join_condition, 'left')
