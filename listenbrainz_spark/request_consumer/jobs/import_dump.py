""" Spark job that downloads the latest listenbrainz dumps and imports into HDFS
"""
import shutil
import tempfile
import time
import logging
from datetime import datetime

import listenbrainz_spark.request_consumer.jobs.utils as utils
from listenbrainz_spark.path import INCREMENTAL_DUMPS_SAVE_PATH
from listenbrainz_spark.ftp import DumpType
from listenbrainz_spark.ftp.download import ListenbrainzDataDownloader
from listenbrainz_spark.hdfs.upload import ListenbrainzDataUploader
from listenbrainz_spark.request_consumer import request_consumer
from listenbrainz_spark.utils import read_files_from_HDFS

logger = logging.getLogger(__name__)

# NOTE: the name of the arguments in these methods should match the name
# of the params in request_queries.json.


def import_full_dump_to_hdfs(dump_id: int = None) -> str:
    """ Import the full dump with the given dump_id if specified otherwise the
     latest full dump.

    Notes:
        Deletes all the existing listens and uploads listens from new dump.
    Args:
        dump_id: id of the full dump to be imported
    Returns:
        the name of the imported dump
    """
    with tempfile.TemporaryDirectory() as temp_dir:
        downloader = ListenbrainzDataDownloader()
        src, dump_name, dump_id = downloader.download_listens(
            directory=temp_dir,
            dump_type=DumpType.FULL,
            listens_dump_id=dump_id
        )
        downloader.connection.close()
        ListenbrainzDataUploader().upload_new_listens_full_dump(src)
    utils.insert_dump_data(dump_id, DumpType.FULL, datetime.utcnow())
    return dump_name


def import_incremental_dump_to_hdfs(dump_id: int = None) -> str:
    """ Import the incremental dump with the given dump_id if specified otherwise the
     latest incremental dump.

    Notes:
        All incremental dumps are stored together in incremental.parquet inside the
        listens directory.
    Args:
        dump_id: id of the incremental dump to be imported
    Returns:
        the name of the imported dump
    """
    with tempfile.TemporaryDirectory() as temp_dir:
        src, dump_name, dump_id = ListenbrainzDataDownloader().download_listens(
            directory=temp_dir,
            dump_type=DumpType.INCREMENTAL,
            listens_dump_id=dump_id
        )

        # instantiating ListenbrainzDataUploader creates a spark session which
        # is a bit non-intuitive.
        # FIXME in future to make initializing of spark session more explicit?
        ListenbrainzDataUploader().upload_new_listens_incremental_dump(src)
    utils.insert_dump_data(dump_id, DumpType.INCREMENTAL, datetime.utcnow())
    return dump_name


def import_newest_full_dump_handler():
    errors = []
    dumps = []
    try:
        dumps.append(import_full_dump_to_hdfs(dump_id=None))
    except Exception as e:
        logger.error("Error while importing full dump: ", exc_info=True)
        errors.append(str(e))
    return [{
        'type': 'import_full_dump',
        'imported_dump': dumps,
        'errors': errors,
        'time': str(datetime.utcnow()),
    }]


def import_full_dump_by_id_handler(dump_id: int):
    errors = []
    dumps = []
    try:
        dumps.append(import_full_dump_to_hdfs(dump_id=dump_id))
    except Exception as e:
        logger.error("Error while importing full dump: ", exc_info=True)
        errors.append(str(e))
    return [{
        'type': 'import_full_dump',
        'imported_dump': dumps,
        'errors': errors,
        'time': str(datetime.utcnow()),
    }]


def import_newest_incremental_dump_handler():
    errors = []
    imported_dumps = []
    latest_full_dump = utils.get_latest_full_dump()
    if latest_full_dump is None:
        # If no prior full dump is present, just import the latest incremental dump
        imported_dumps.append(import_incremental_dump_to_hdfs(dump_id=None))

        error_msg = "No previous full dump found, importing latest incremental dump"
        errors.append(error_msg)
        logger.warning(error_msg, exc_info=True)
    else:
        # Import all missing dumps from last full dump import
        start_id = latest_full_dump["dump_id"] + 1
        imported_at = latest_full_dump["imported_at"]
        end_id = ListenbrainzDataDownloader().get_latest_dump_id(DumpType.INCREMENTAL) + 1

        for dump_id in range(start_id, end_id, 1):
            if not utils.search_dump(dump_id, DumpType.INCREMENTAL, imported_at):
                try:
                    imported_dumps.append(import_incremental_dump_to_hdfs(dump_id))
                except Exception as e:
                    # Skip current dump if any error occurs during import
                    error_msg = f"Error while importing incremental dump with ID {dump_id}: {e}"
                    errors.append(error_msg)
                    logger.error(error_msg, exc_info=True)
                    continue
            dump_id += 1
    return [{
        'type': 'import_incremental_dump',
        'imported_dump': imported_dumps,
        'errors': errors,
        'time': str(datetime.utcnow()),
    }]


def import_incremental_dump_by_id_handler(dump_id: int):
    errors = []
    dumps = []
    try:
        dumps.append(import_incremental_dump_to_hdfs(dump_id=dump_id))
    except Exception as e:
        logger.error("Error while importing incremental dump: ", exc_info=True)
        errors.append(str(e))
    return [{
        'type': 'import_incremental_dump',
        'imported_dump': dumps,
        'errors': errors,
        'time': str(datetime.utcnow()),
    }]


def import_artist_relation_to_hdfs():
    ts = time.monotonic()
    temp_dir = tempfile.mkdtemp()
    src, artist_relation_name = ListenbrainzDataDownloader().download_artist_relation(directory=temp_dir)
    ListenbrainzDataUploader().upload_artist_relation(archive=src)
    shutil.rmtree(temp_dir)

    return [{
        'type': 'import_artist_relation',
        'imported_artist_relation': artist_relation_name,
        'import_time': str(datetime.utcnow()),
        'time_taken_to_import': '{:.2f}'.format(time.monotonic() - ts)
    }]


def import_release_json_dump_to_hdfs():
    with tempfile.TemporaryDirectory() as temp_dir:
        downloader = ListenbrainzDataDownloader()
        dest = downloader.download_release_json_dump(temp_dir)
        downloader.connection.close()
        ListenbrainzDataUploader().upload_release_json_dump(dest)
