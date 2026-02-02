import os
import os.path
from datetime import datetime
from textwrap import dedent
from typing import Optional

from dateutil.relativedelta import relativedelta
from pyspark.sql import functions, DataFrame

import listenbrainz_spark
from listenbrainz_spark import hdfs_connection
from listenbrainz_spark.listens.cache import get_incremental_listens_df, \
    get_deleted_listens_df, get_deleted_users_listen_history_df
from listenbrainz_spark.listens.metadata import get_listens_metadata
from listenbrainz_spark.schema import listens_new_schema


def incremental_listens_exist() -> bool:
    """ Check if incremental listens dump exists """
    metadata = get_listens_metadata()
    incremental_location = os.path.join(metadata.location, "incremental")
    return hdfs_connection.client.status(incremental_location, strict=False)


def get_listens_from_dump(start: datetime = None, end: datetime = None,
                          include_incremental: bool = True, remove_deleted: bool = False) -> DataFrame:
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

    metadata = get_listens_metadata()
    base_listens_location = os.path.join(metadata.location, "base")

    if hdfs_connection.client.status(base_listens_location, strict=False):
        full_df = get_base_listens_df(base_listens_location, start, end)
        df = df.union(full_df)

    if include_incremental and incremental_listens_exist():
        df = df.union(get_incremental_listens_df())

    df = filter_listens_by_range(df, start, end)

    if remove_deleted:
        df = filter_deleted_listens(df, metadata.location)

    return df


def filter_listens_by_range(listens_df: DataFrame, start: Optional[datetime], end: Optional[datetime]) -> DataFrame:
    """ Filter listens dataframe to only keep listens with listened_at between start and end. """
    if start:
        listens_df = listens_df.where(f"listened_at >= to_timestamp('{start}')")
    if end:
        listens_df = listens_df.where(f"listened_at <= to_timestamp('{end}')")
    return listens_df


def filter_deleted_listens(listens_df: DataFrame, location: str) -> DataFrame:
    """ Filter listens dataframe to remove listens that have been deleted from LB db. """
    deleted_listens_save_path = os.path.join(location, "deleted-listens")
    if hdfs_connection.client.status(deleted_listens_save_path, strict=False):
        delete_df = get_deleted_listens_df()
        if not delete_df.isEmpty():
            listens_df = listens_df \
                .join(delete_df, ["user_id", "listened_at", "recording_msid", "created"], "anti") \
                .select(*listens_df.columns)

    deleted_user_listen_history_save_path = os.path.join(location, "deleted-user-listen-history")
    if hdfs_connection.client.status(deleted_user_listen_history_save_path, strict=False):
        delete_df2 = get_deleted_users_listen_history_df()
        if not delete_df2.isEmpty():
            listens_df = listens_df \
                .join(delete_df2, ["user_id"], "left_outer") \
                .where((delete_df2.max_created.isNull()) | (listens_df.created >= delete_df2.max_created)) \
                .select(*listens_df.columns)

    return listens_df


def get_base_listens_df(location, start: datetime, end: datetime):
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
          from parquet.`{location}`
    """) + where_clause
    return listenbrainz_spark.session.sql(query)


def get_latest_listen_ts() -> datetime:
    """ Get the max listened_at timestamp present in the imported listens dumps """
    metadata = get_listens_metadata()
    base_latest_listen_ts = metadata.max_listened_at

    if incremental_listens_exist():
        inc_latest_listen_ts = get_incremental_listens_df() \
            .select("listened_at") \
            .agg(functions.max("listened_at").alias("inc_latest_listen_ts"))\
            .collect()[0]["inc_latest_listen_ts"]
        return max(base_latest_listen_ts, inc_latest_listen_ts)

    return base_latest_listen_ts
