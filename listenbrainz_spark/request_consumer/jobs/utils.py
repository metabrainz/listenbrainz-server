""" Bunch of utilility functions needed for import jobs """
import logging
from datetime import datetime
from typing import Optional

from listenbrainz_spark.exceptions import PathNotFoundException
from listenbrainz_spark.path import IMPORT_METADATA
from listenbrainz_spark.schema import import_metadata_schema
from listenbrainz_spark.utils import (create_dataframe, read_files_from_HDFS,
                                      save_parquet, path_exists, delete_dir, rename)
from pyspark.sql import Row
from pyspark.sql.functions import col


logger = logging.getLogger(__name__)


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


def search_dump(dump_id: int, dump_type: str, imported_at: datetime) -> bool:
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
        .filter(f"dump_id == '{dump_id}' AND dump_type == '{dump_type}'") \
        .count()

    return result > 0


def insert_dump_data(dump_id: int, dump_type: str, imported_at: datetime):
    """ Insert information about dump imported """
    import_meta_df = None
    try:
        import_meta_df = read_files_from_HDFS(IMPORT_METADATA)
    except PathNotFoundException:
        logger.info("Import metadata file not found, creating...")

    data = create_dataframe(Row(dump_id, dump_type, imported_at), schema=import_metadata_schema)
    if import_meta_df:
        result = import_meta_df \
            .filter(f"dump_id != '{dump_id}' OR dump_type != '{dump_type}'") \
            .union(data)
    else:
        result = data

    # We have to save the dataframe as a different file and move it as the df itself is read from the file
    save_parquet(result, "/temp.parquet")
    if path_exists(IMPORT_METADATA):
        delete_dir(IMPORT_METADATA, recursive=True)
    rename("/temp.parquet", IMPORT_METADATA)
