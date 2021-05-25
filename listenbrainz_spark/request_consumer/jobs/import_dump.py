""" Spark job that downloads the latest listenbrainz dumps and imports into HDFS
"""

import shutil
import tempfile
import time
import logging
from datetime import datetime

import listenbrainz_spark.request_consumer.jobs.utils as utils
from listenbrainz_spark.exceptions import DumpNotFoundException
from listenbrainz_spark.ftp.download import ListenbrainzDataDownloader
from listenbrainz_spark.hdfs.upload import ListenbrainzDataUploader
from listenbrainz_spark.request_consumer import request_consumer


logger = logging.getLogger(__name__)


def import_dump_to_hdfs(dump_type, overwrite, dump_id=None):
    temp_dir = tempfile.mkdtemp()
    dump_type = 'incremental' if dump_type == 'incremental' else 'full'
    src, dump_name, dump_id = ListenbrainzDataDownloader().download_listens(directory=temp_dir, dump_type=dump_type,
                                                                            listens_dump_id=dump_id)
    ListenbrainzDataUploader().upload_listens(src, overwrite=overwrite)
    utils.insert_dump_data(dump_id, dump_type, datetime.utcnow())
    shutil.rmtree(temp_dir)
    return dump_name


def import_newest_full_dump_handler():
    dump_name = import_dump_to_hdfs('full', overwrite=True)
    return [{
        'type': 'import_full_dump',
        'imported_dump': [dump_name],
        'time': str(datetime.utcnow()),
    }]


def import_full_dump_by_id_handler(id: int):
    dump_name = import_dump_to_hdfs('full', overwrite=True, dump_id=id)
    return [{
        'type': 'import_full_dump',
        'imported_dump': [dump_name],
        'time': str(datetime.utcnow()),
    }]


def import_newest_incremental_dump_handler():
    imported_dumps = []
    latest_full_dump = utils.get_latest_full_dump()
    if latest_full_dump is None:
        # If no prior full dump is present, just import the lates incremental dump
        imported_dumps.append(import_dump_to_hdfs('incremental', overwrite=False))
        logger.warning("No previous full dump found, importing latest incremental dump", exc_info=True)
    else:
        # Import all missing dumps from last full dump import
        dump_id = latest_full_dump["dump_id"] + 1
        imported_at = latest_full_dump["imported_at"]
        while True:
            if not utils.search_dump(dump_id, 'incremental', imported_at):
                try:
                    imported_dumps.append(import_dump_to_hdfs('incremental', False, dump_id))
                except DumpNotFoundException:
                    break
                except Exception as e:
                    # Exit if any other error occurs during import
                    logger.error(f"Error while importing incremental dump with ID {dump_id}: {e}", exc_info=True)
                    break
            dump_id += 1
            request_consumer.rc.ping()
    return [{
        'type': 'import_incremental_dump',
        'imported_dump': imported_dumps,
        'time': str(datetime.utcnow()),
    }]


def import_incremental_dump_by_id_handler(id: int):
    dump_name = import_dump_to_hdfs('incremental', overwrite=False, dump_id=id)
    return [{
        'type': 'import_incremental_dump',
        'imported_dump': [dump_name],
        'time': str(datetime.utcnow()),
    }]


def import_mapping_to_hdfs():
    ts = time.monotonic()
    temp_dir = tempfile.mkdtemp()
    src, mapping_name = ListenbrainzDataDownloader().download_msid_mbid_mapping(directory=temp_dir)
    ListenbrainzDataUploader().upload_mapping(archive=src)
    shutil.rmtree(temp_dir)

    return [{
        'type': 'import_mapping',
        'imported_mapping': mapping_name,
        'import_time': str(datetime.utcnow()),
        'time_taken_to_import': '{:.2f}'.format(time.monotonic() - ts)
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
