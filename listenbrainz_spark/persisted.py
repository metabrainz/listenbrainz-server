from typing import Optional

from pandas import DataFrame

from listenbrainz_spark.path import INCREMENTAL_DUMPS_SAVE_PATH
from listenbrainz_spark.utils import read_files_from_HDFS

_incremental_listens_df: Optional[DataFrame] = None


def unpersist_incremental_listens_df():
    global _incremental_listens_df
    if _incremental_listens_df is not None:
        _incremental_listens_df.unpersist()
        _incremental_listens_df = None


def get_incremental_listens_df() -> DataFrame:
    global _incremental_listens_df
    if _incremental_listens_df is None:
        _incremental_listens_df = read_files_from_HDFS(INCREMENTAL_DUMPS_SAVE_PATH)
        _incremental_listens_df.persist()
    return _incremental_listens_df
