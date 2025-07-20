from typing import Optional

from pyspark import StorageLevel
from pyspark.sql import DataFrame

from data.postgres.release_group import get_release_group_metadata_cache_query
from listenbrainz_spark.path import RELEASE_GROUP_METADATA_CACHE_DATAFRAME
from listenbrainz_spark.postgres.utils import save_pg_table_to_hdfs
from listenbrainz_spark.utils import read_files_from_HDFS

_RELEASE_GROUP_METADATA_CACHE = "release_group_metadata_cache"
_release_group_metadata_df: Optional[DataFrame] = None


def create_release_group_metadata_cache():
    """ Import release groups with cover art data from postgres to HDFS """
    query = get_release_group_metadata_cache_query()
    save_pg_table_to_hdfs(query, RELEASE_GROUP_METADATA_CACHE_DATAFRAME, process_artists_column=True)
    unpersist_release_group_metadata_cache()


def get_release_group_metadata_cache():
    """ Read the RELEASE_GROUP_METADATA_CACHE parquet files from HDFS and create a spark SQL view
     if one already doesn't exist """
    global _release_group_metadata_df
    if _release_group_metadata_df is None:
        _release_group_metadata_df = read_files_from_HDFS(RELEASE_GROUP_METADATA_CACHE_DATAFRAME)
        _release_group_metadata_df.persist(StorageLevel.DISK_ONLY)
        _release_group_metadata_df.createOrReplaceTempView(_RELEASE_GROUP_METADATA_CACHE)
    return _RELEASE_GROUP_METADATA_CACHE


def unpersist_release_group_metadata_cache():
    global _release_group_metadata_df
    if _release_group_metadata_df is not None:
        _release_group_metadata_df.unpersist()
        _release_group_metadata_df = None
