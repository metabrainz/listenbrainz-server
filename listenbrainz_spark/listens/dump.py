""" Spark job that downloads the latest listenbrainz dumps and imports into HDFS
"""
import logging
import os
import tempfile
import time
from datetime import datetime, timezone
from typing import Optional

from pyspark import Row
from pyspark.sql.functions import col

from listenbrainz_spark import hdfs_connection
from listenbrainz_spark.dump import DumpType, ListenbrainzDumpLoader
from listenbrainz_spark.dump.local import ListenbrainzLocalDumpLoader
from listenbrainz_spark.exceptions import PathNotFoundException
from listenbrainz_spark.ftp.download import ListenbrainzDataDownloader
from listenbrainz_spark.hdfs.upload import upload_archive_to_hdfs_temp
from listenbrainz_spark.hdfs.utils import path_exists, delete_dir, rename, move
from listenbrainz_spark.listens.cache import unpersist_incremental_df
from listenbrainz_spark.path import IMPORT_METADATA, LISTENBRAINZ_NEW_DATA_DIRECTORY, \
    LISTENBRAINZ_INTERMEDIATE_STATS_DIRECTORY, LISTENBRAINZ_BASE_STATS_DIRECTORY, INCREMENTAL_DUMPS_SAVE_PATH, \
    INCREMENTAL_USERS_DF
from listenbrainz_spark.schema import import_metadata_schema
from listenbrainz_spark.stats import run_query
from listenbrainz_spark.utils import read_files_from_HDFS, create_dataframe, save_parquet

logger = logging.getLogger(__name__)


def import_full_dump_to_hdfs(loader: ListenbrainzDumpLoader, dump_id: int = None) -> str:
    """ Import the full dump with the given dump_id if specified otherwise the
     latest full dump.

    Notes:
        Deletes all the existing listens and uploads listens from new dump.
    Args:
        loader: class to download dumps and load listens from it
        dump_id: id of the full dump to be imported
    Returns:
        the name of the imported dump
    """
    with tempfile.TemporaryDirectory() as temp_dir:
        src, dump_name, dump_id = loader.load_listens(
            directory=temp_dir,
            dump_type=DumpType.FULL,
            listens_dump_id=dump_id
        )
        temp_path = upload_archive_to_hdfs_temp(src, ".parquet")
        process_full_listens_dump(temp_path)
    insert_dump_data(dump_id, DumpType.FULL, datetime.now(tz=timezone.utc))
    return dump_name


def import_incremental_dump_to_hdfs(loader: ListenbrainzDumpLoader, dump_id: int = None) -> str:
    """ Import the incremental dump with the given dump_id if specified otherwise the
     latest incremental dump.

    Notes:
        All incremental dumps are stored together in incremental.parquet inside the listens directory.
    Args:
        loader: class to download dumps and load listens from it
        dump_id: id of the incremental dump to be imported
    Returns:
        the name of the imported dump
    """
    with tempfile.TemporaryDirectory() as temp_dir:
        src, dump_name, dump_id = loader.load_listens(
            directory=temp_dir,
            dump_type=DumpType.INCREMENTAL,
            listens_dump_id=dump_id
        )
        temp_path = upload_archive_to_hdfs_temp(src, ".parquet")
        process_incremental_listens_dump(temp_path)
    insert_dump_data(dump_id, DumpType.INCREMENTAL, datetime.now(tz=timezone.utc))
    return dump_name


def import_full_dump_handler(dump_id: int = None, local: bool = False):
    loader = ListenbrainzLocalDumpLoader() if local else ListenbrainzDataDownloader()
    errors = []
    dumps = []
    try:
        dumps.append(import_full_dump_to_hdfs(loader=loader, dump_id=dump_id))
    except Exception as e:
        logger.error("Error while importing full dump: ", exc_info=True)
        errors.append(str(e))
    return [{
        "type": "import_full_dump",
        "imported_dump": dumps,
        "errors": errors,
        "time": datetime.now(timezone.utc).isoformat(),
    }]


def import_incremental_dump_handler(dump_id: int = None, local: bool = False):
    loader = ListenbrainzLocalDumpLoader() if local else ListenbrainzDataDownloader()
    errors = []
    imported_dumps = []
    latest_full_dump = get_latest_full_dump()
    if dump_id is not None:
        try:
            imported_dumps.append(import_incremental_dump_to_hdfs(loader, dump_id=dump_id))
        except Exception as e:
            logger.error("Error while importing incremental dump: ", exc_info=True)
            errors.append(str(e))
    elif latest_full_dump is None:
        # If no prior full dump is present, just import the latest incremental dump
        try:
            imported_dumps.append(import_incremental_dump_to_hdfs(loader, dump_id=None))
        except Exception as e:
            logger.error("Error while importing incremental dump: ", exc_info=True)
            errors.append(str(e))

        error_msg = "No previous full dump found, importing latest incremental dump"
        errors.append(error_msg)
        logger.warning(error_msg, exc_info=True)
    else:
        # Import all missing dumps from last full dump import
        start_id = latest_full_dump["dump_id"] + 1
        imported_at = latest_full_dump["imported_at"]
        end_id = ListenbrainzDataDownloader().get_latest_dump_id(DumpType.INCREMENTAL) + 1

        for dump_id in range(start_id, end_id, 1):
            if not search_dump(dump_id, DumpType.INCREMENTAL, imported_at):
                try:
                    imported_dumps.append(import_incremental_dump_to_hdfs(loader, dump_id=dump_id))
                except Exception as e:
                    # Skip current dump if any error occurs during import
                    error_msg = f"Error while importing incremental dump with ID {dump_id}: {e}"
                    errors.append(error_msg)
                    logger.error(error_msg, exc_info=True)
                    continue
            dump_id += 1
    return [{
        "type": "import_incremental_dump",
        "imported_dump": imported_dumps,
        "errors": errors,
        "time": datetime.now(timezone.utc).isoformat(),
    }]


def get_latest_full_dump() -> Optional[dict]:
    """ Get the latest imported dump information.

        Returns:
            Dictionary containing information about latest full dump import if found else None.
    """
    try:
        import_meta_df = read_files_from_HDFS(IMPORT_METADATA)
    except PathNotFoundException:
        return None

    result = import_meta_df.filter('dump_type == "full"') \
        .sort(col('imported_at').desc()) \
        .toLocalIterator()
    try:
        return next(result).asDict()
    except StopIteration:
        return None


def search_dump(dump_id: int, dump_type: DumpType, imported_at: datetime) -> bool:
    """ Search if a particular dump has been imported after a particular timestamp.

        Returns:
            True if dump is found else False
    """
    try:
        import_meta_df = read_files_from_HDFS(IMPORT_METADATA)
    except PathNotFoundException:
        return False

    result = import_meta_df \
        .filter(import_meta_df.imported_at >= imported_at) \
        .filter(f"dump_id == '{dump_id}' AND dump_type == '{dump_type.value}'") \
        .count()

    return result > 0


def insert_dump_data(dump_id: int, dump_type: DumpType, imported_at: datetime):
    """ Insert information about dump imported """
    import_meta_df = None
    try:
        import_meta_df = read_files_from_HDFS(IMPORT_METADATA)
    except PathNotFoundException:
        logger.info("Import metadata file not found, creating...")

    data = create_dataframe(Row(dump_id, dump_type.value, imported_at), schema=import_metadata_schema)
    if import_meta_df:
        result = import_meta_df \
            .filter(f"dump_id != '{dump_id}' OR dump_type != '{dump_type.value}'") \
            .union(data)
    else:
        result = data

    # We have to save the dataframe as a different file and move it as the df itself is read from the file
    save_parquet(result, "/temp.parquet")
    if path_exists(IMPORT_METADATA):
        delete_dir(IMPORT_METADATA, recursive=True)
    rename("/temp.parquet", IMPORT_METADATA)


def process_full_listens_dump(temp_path):
    """ Partition the imported full listens parquet dump by year and month """
    dest_path = LISTENBRAINZ_NEW_DATA_DIRECTORY
    t0 = time.monotonic()
    move(temp_path, dest_path)
    logger.info(f"Full dump uploaded! Time taken: {time.monotonic() - t0:.2f}")

    unpersist_incremental_df()

    query = f"""
        select extract(year from listened_at) as year
             , extract(month from listened_at) as month
             , listened_at
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
          from parquet.`{dest_path}`
    """
    run_query(query) \
        .write \
        .partitionBy("year", "month") \
        .mode("overwrite") \
        .parquet(LISTENBRAINZ_INTERMEDIATE_STATS_DIRECTORY)

    if path_exists(LISTENBRAINZ_BASE_STATS_DIRECTORY):
        hdfs_connection.client.delete(LISTENBRAINZ_BASE_STATS_DIRECTORY, recursive=True, skip_trash=True)


def process_incremental_listens_dump(temp_path):
    read_files_from_HDFS(temp_path) \
        .repartition(1) \
        .write \
        .mode("append") \
        .parquet(INCREMENTAL_DUMPS_SAVE_PATH)

    # delete parquet from hdfs temporary path
    delete_dir(temp_path, recursive=True)

    unpersist_incremental_df()

    query = f"""
        SELECT user_id
             , max(created) AS created
          FROM parquet.`{INCREMENTAL_DUMPS_SAVE_PATH}`
      GROUP BY user_id
    """
    run_query(query) \
        .write \
        .mode("overwrite") \
        .parquet(INCREMENTAL_USERS_DF)
