import os

import listenbrainz_spark
from listenbrainz_spark import hdfs_connection
from listenbrainz_spark.hdfs.utils import path_exists
from listenbrainz_spark.listens.cache import unpersist_incremental_df
from listenbrainz_spark.listens.data import get_listens_from_dump
from listenbrainz_spark.listens.metadata import get_listens_metadata, generate_new_listens_location, \
    update_listens_metadata
from listenbrainz_spark.path import LISTENBRAINZ_BASE_STATS_DIRECTORY


def main():
    """
    Compacts listen storage by processing base and incremental listen records.

    Reads base and incremental listen records, removes deleted listens, and stores the final
    processed data partitioned by year and month in a new HDFS location.
    """
    table = "listens_to_compact"
    old_df = get_listens_from_dump(include_incremental=True, remove_deleted=True)
    old_df.createOrReplaceTempView(table)

    write_partitioned_listens(table)


def write_partitioned_listens(table):
    """ Read listens from the given table and write them to a new HDFS location partitioned
     by listened_at's year and month. """
    query = f"""
        select extract(year from listened_at) as year
             , extract(month from listened_at) as month
             , *
          from {table}
    """
    new_location = generate_new_listens_location()
    new_base_listens_location = os.path.join(new_location, "base")

    listenbrainz_spark \
        .session \
        .sql(query) \
        .write \
        .partitionBy("year", "month") \
        .mode("overwrite") \
        .parquet(new_base_listens_location)

    query = f"""
        select max(listened_at) as max_listened_at, max(created) as max_created
          from parquet.`{new_base_listens_location}`
    """
    result = listenbrainz_spark \
        .session \
        .sql(query) \
        .collect()[0]

    metadata = get_listens_metadata()
    if metadata is None:
        existing_location = None
    else:
        existing_location = metadata.location

    update_listens_metadata(new_location, result.max_listened_at, result.max_created)

    unpersist_incremental_df()

    if existing_location and path_exists(existing_location):
        hdfs_connection.client.delete(existing_location, recursive=True, skip_trash=True)

    hdfs_connection.client.delete(LISTENBRAINZ_BASE_STATS_DIRECTORY, recursive=True, skip_trash=True)
