from typing import Optional

from pyspark import StorageLevel
from pyspark.sql import DataFrame

from data.postgres.recording_writer import get_recording_writer_cache_query
from listenbrainz_spark import config
from listenbrainz_spark.path import RECORDING_WRITER_DATAFRAME
from listenbrainz_spark.postgres.utils import save_pg_table_to_hdfs
from listenbrainz_spark.utils import read_files_from_HDFS

_RECORDING_WRITER_CACHE = "recording_writer_cache"
_recording_writer_df: Optional[DataFrame] = None


def create_recording_writer_cache():
    """ Import recording-writer mapping from postgres to HDFS.

    This cache maps recording_mbid to writer (composer/lyricist/writer) MBIDs
    by traversing: recording -> work -> artist relationships in MusicBrainz.
    """
    query = get_recording_writer_cache_query()
    save_pg_table_to_hdfs(query, RECORDING_WRITER_DATAFRAME)
    unpersist_recording_writer_cache()


def get_recording_writer_cache():
    """ Read the recording-writer cache from HDFS and create a Spark SQL view
    if one doesn't already exist. Returns the view name. """
    global _recording_writer_df
    if _recording_writer_df is None:
        _recording_writer_df = read_files_from_HDFS(RECORDING_WRITER_DATAFRAME)
        _recording_writer_df.persist(StorageLevel.DISK_ONLY)
        _recording_writer_df.createOrReplaceTempView(_RECORDING_WRITER_CACHE)
    return _RECORDING_WRITER_CACHE


def unpersist_recording_writer_cache():
    global _recording_writer_df
    if _recording_writer_df is not None:
        _recording_writer_df.unpersist()
        _recording_writer_df = None
