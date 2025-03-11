import os
from typing import Optional

from pyspark.sql import DataFrame

from listenbrainz_spark.listens.metadata import get_listens_metadata
from listenbrainz_spark.utils import read_files_from_HDFS

_incremental_listens_df: Optional[DataFrame] = None
_incremental_users_df: Optional[DataFrame] = None
_deleted_listens_df: Optional[DataFrame] = None
_deleted_users_listen_history_df: Optional[DataFrame] = None


def unpersist_incremental_df():
    global _incremental_listens_df, _incremental_users_df
    if _incremental_listens_df is not None:
        _incremental_listens_df.unpersist()
        _incremental_listens_df = None
    if _incremental_users_df is not None:
        _incremental_users_df.unpersist()
        _incremental_users_df = None


def unpersist_deleted_df():
    global _deleted_listens_df, _deleted_users_listen_history_df
    if _deleted_listens_df is not None:
        _deleted_listens_df.unpersist()
        _deleted_listens_df = None
    if _deleted_users_listen_history_df is not None:
        _deleted_users_listen_history_df.unpersist()
        _deleted_users_listen_history_df = None


def get_incremental_listens_df() -> DataFrame:
    """ Loads all listens imported from incremental dumps

    Filter on listened_at after loading the dataframe to restrict on desired date range.
    """
    global _incremental_listens_df
    if _incremental_listens_df is None:
        listens_location = get_listens_metadata().location
        inc_listens_location = os.path.join(listens_location, "incremental")
        _incremental_listens_df = read_files_from_HDFS(inc_listens_location)
        _incremental_listens_df.persist()
    return _incremental_listens_df


def get_incremental_users_df() -> DataFrame:
    global _incremental_users_df
    if _incremental_users_df is None:
        listens_location = get_listens_metadata().location
        inc_users_location = os.path.join(listens_location, "incremental-users")
        _incremental_users_df = read_files_from_HDFS(inc_users_location)
        _incremental_users_df.persist()
    return _incremental_users_df


def get_deleted_listens_df() -> DataFrame:
    global _deleted_listens_df
    if _deleted_listens_df is None:
        listens_location = get_listens_metadata().location
        deleted_listens_location = os.path.join(listens_location, "deleted-listens")
        _deleted_listens_df = read_files_from_HDFS(deleted_listens_location)
        _deleted_listens_df.persist()
    return _deleted_listens_df


def get_deleted_users_listen_history_df() -> DataFrame:
    global _deleted_users_listen_history_df
    if _deleted_users_listen_history_df is None:
        listens_location = get_listens_metadata().location
        deleted_user_listen_history_location = os.path.join(listens_location, "deleted-user-listen-history")
        _deleted_users_listen_history_df = read_files_from_HDFS(deleted_user_listen_history_location)
        _deleted_users_listen_history_df.persist()
    return _deleted_users_listen_history_df
