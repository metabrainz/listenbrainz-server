""" Spark job that downloads the latest listenbrainz dump and imports into HDFS
"""

import shutil
import tempfile

from datetime import datetime
from listenbrainz_spark.ftp.download import ListenbrainzDataDownloader
from listenbrainz_spark.hdfs.upload import ListenbrainzDataUploader


def import_dump_to_hdfs(dump_type, force, dump_id=None):
    temp_dir = tempfile.mkdtemp()
    dump_type = 'incremental' if dump_type == 'incremental' else 'full'
    src, dump_name = ListenbrainzDataDownloader().download_listens(directory=temp_dir, dump_type=dump_type)
    ListenbrainzDataUploader().upload_listens(src, force=force)
    shutil.rmtree(temp_dir)
    return dump_name

def import_newest_full_dump_handler():
    dump_name = import_dump_to_hdfs('full', force=True)
    return [{
        'type': 'import_full_dump',
        'imported_dump': dump_name,
        'time': str(datetime.utcnow()),
    }]
