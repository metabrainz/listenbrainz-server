from typing import Optional

from pandas import DataFrame

from listenbrainz_spark.path import INCREMENTAL_DUMPS_SAVE_PATH, INCREMENTAL_USERS_DF, DELETED_LISTENS_SAVE_PATH, \
    DELETED_USER_LISTEN_HISTORY_SAVE_PATH
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
        _incremental_listens_df = read_files_from_HDFS(INCREMENTAL_DUMPS_SAVE_PATH)
        _incremental_listens_df.persist()
    return _incremental_listens_df


def get_incremental_users_df() -> DataFrame:
    global _incremental_users_df
    if _incremental_users_df is None:
        _incremental_users_df = read_files_from_HDFS(INCREMENTAL_USERS_DF)
        _incremental_users_df.persist()
    return _incremental_users_df


def get_deleted_listens_df() -> DataFrame:
    global _deleted_listens_df
    if _deleted_listens_df is None:
        _deleted_listens_df = read_files_from_HDFS(DELETED_LISTENS_SAVE_PATH)
        _deleted_listens_df.persist()
    return _deleted_listens_df


def get_deleted_users_listen_history_df() -> DataFrame:
    global _deleted_users_listen_history_df
    if _deleted_users_listen_history_df is None:
        _deleted_users_listen_history_df = read_files_from_HDFS(DELETED_USER_LISTEN_HISTORY_SAVE_PATH)
        _deleted_users_listen_history_df.persist()
    return _deleted_users_listen_history_df
