import os
from datetime import datetime
from textwrap import dedent
from typing import List

from dateutil.relativedelta import relativedelta
from pyspark.sql import DataFrame, functions

import listenbrainz_spark
from listenbrainz_spark import hdfs_connection
from listenbrainz_spark.listens.cache import get_deleted_listens_df, get_deleted_users_listen_history_df
from listenbrainz_spark.path import LISTENBRAINZ_NEW_DATA_DIRECTORY, LISTENBRAINZ_INTERMEDIATE_STATS_DIRECTORY, \
    INCREMENTAL_DUMPS_SAVE_PATH, DELETED_LISTENS_SAVE_PATH, DELETED_USER_LISTEN_HISTORY_SAVE_PATH
from listenbrainz_spark.schema import listens_new_schema
from listenbrainz_spark.utils import read_files_from_HDFS


def get_listen_files_list() -> List[str]:
    """ Get list of name of parquet files containing the listens.
    The list of file names is in order of newest to oldest listens.
    """
    files = hdfs_connection.client.list(LISTENBRAINZ_NEW_DATA_DIRECTORY)
    has_incremental = False
    file_names = []

    for file in files:
        # handle incremental dumps separately because later we want to sort
        # based on numbers in file name
        if file == "incremental.parquet":
            has_incremental = True
            continue
        if file in {"delete.parquet", "deleted-user-listen-history.parquet", "incremental-users.parquet"} :
            continue
        if file.endswith(".parquet"):
            file_names.append(file)

    # parquet files which come from full dump are named as 0.parquet, 1.parquet so
    # on. listens are stored in ascending order of listened_at. so higher the number
    # in the name of the file, newer the listens. Therefore, we sort the list
    # according to numbers in name of parquet files, in reverse order to start
    # loading newer listens first.
    file_names.sort(key=lambda x: int(x.split(".")[0]), reverse=True)

    # all incremental dumps are stored in incremental.parquet. these are the newest
    # listens. but an incremental dump might not always exist for example at the time
    # when a full dump has just been imported. so check if incremental dumps are
    # present, if yes then add those to the start of list
    if has_incremental:
        file_names.insert(0, "incremental.parquet")

    return file_names


def get_listens_from_dump(start: datetime, end: datetime, include_incremental=True, remove_deleted=False) -> DataFrame:
    """ Load listens with listened_at between from_ts and to_ts from HDFS in a spark dataframe.

        Args:
            start: minimum time to include a listen in the dataframe
            end: maximum time to include a listen in the dataframe
            include_incremental: if True, also include listens from incremental dumps
            remove_deleted: if True, also remove deleted listens from the dataframe

        Returns:
            dataframe of listens with listened_at between start and end
    """
    df = listenbrainz_spark.session.createDataFrame([], listens_new_schema)

    if hdfs_connection.client.status(LISTENBRAINZ_INTERMEDIATE_STATS_DIRECTORY, strict=False):
        full_df = get_intermediate_stats_df(start, end)
        df = df.union(full_df)

    if include_incremental and hdfs_connection.client.status(INCREMENTAL_DUMPS_SAVE_PATH, strict=False):
        inc_df = read_files_from_HDFS(INCREMENTAL_DUMPS_SAVE_PATH)
        df = df.union(inc_df)

    df = filter_listens_by_range(df, start, end)

    if remove_deleted:
        df = filter_deleted_listens(df)

    return df


def filter_listens_by_range(listens_df: DataFrame, start: datetime, end: datetime) -> DataFrame:
    """ Filter listens dataframe to only keep listens with listened_at between start and end. """
    if start:
        listens_df = listens_df.where(f"listened_at >= to_timestamp('{start}')")
    if end:
        listens_df = listens_df.where(f"listened_at <= to_timestamp('{end}')")
    return listens_df


def filter_deleted_listens(listens_df: DataFrame) -> DataFrame:
    """ Filter listens dataframe to remove listens that have been deleted from LB db. """
    if hdfs_connection.client.status(DELETED_LISTENS_SAVE_PATH, strict=False):
        delete_df = get_deleted_listens_df()
        listens_df = listens_df \
            .join(delete_df, ["user_id", "listened_at", "recording_msid", "created"], "anti") \
            .select(*listens_df.columns)

    if hdfs_connection.client.status(DELETED_USER_LISTEN_HISTORY_SAVE_PATH, strict=False):
        delete_df2 = get_deleted_users_listen_history_df()
        listens_df = listens_df \
            .join(delete_df2, ["user_id"], "left_outer") \
            .where((delete_df2.max_created.isNull()) | (listens_df.created >= delete_df2.max_created)) \
            .select(*listens_df.columns)

    return listens_df


def get_intermediate_stats_df(start: datetime, end: datetime):
    if start is None and end is None:
        where_clause = ""
    else:
        filters = []
        current = start
        step = relativedelta(months=1)
        while current <= end:
            filters.append(f"(year = {current.year} AND month = {current.month})")
            current += step
        where_clause = "where (\n       " + "\n    OR ".join(filters) + "\n       )"

    query = dedent(f"""\
        select listened_at
             , created
             , user_id
             , recording_msid
             , artist_name
             , artist_credit_id
             , release_name
             , release_mbid
             , recording_name
             , recording_mbid
             , artist_credit_mbids
          from parquet.`{LISTENBRAINZ_INTERMEDIATE_STATS_DIRECTORY}`
    """) + where_clause
    return listenbrainz_spark.sql_context.sql(query)


def get_latest_listen_ts() -> datetime:
    """" Get the listened_at time of the latest listen present
     in the imported dumps
     """
    latest_listen_file = get_listen_files_list()[0]
    df = read_files_from_HDFS(
        os.path.join(LISTENBRAINZ_NEW_DATA_DIRECTORY, latest_listen_file)
    )
    return df \
        .select('listened_at') \
        .agg(functions.max('listened_at').alias('latest_listen_ts'))\
        .collect()[0]['latest_listen_ts']
