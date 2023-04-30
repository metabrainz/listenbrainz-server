import logging
import tempfile
import time
from datetime import datetime

import pycurl

from listenbrainz_spark import config
from listenbrainz_spark.hdfs.upload import ListenbrainzDataUploader

logger = logging.getLogger(__name__)


def download_mlhd_plus_dump_file(filename, dest):
    t0 = time.monotonic()
    logger.info(f"Downloading MLHD+ listen file {filename} from FTP...")

    curl = pycurl.Curl()
    download_path = f"{config.MLHD_PLUS_DUMP_URI}/{filename}"
    curl.setopt(pycurl.URL, download_path)
    with open(dest, "wb") as f:
        curl.setopt(pycurl.WRITEDATA, f)
        curl.perform()
        curl.close()

    logger.info(f"Done. Total time: {time.monotonic() - t0:.2f} sec")


def import_mlhd_dump_to_hdfs():
    """ Import the MLHD+ dump. """
    # MLHD_PLUS_CHUNKS = [
    #     "0", "1", "2", "3", "4", "5", "6", "7",
    #     "8", "9", "a", "b", "c", "d", "e", "f"
    # ]
    # MLHD_PLUS_FILES = [f"mlhdplus-complete-{chunk}.tar" for chunk in MLHD_PLUS_CHUNKS]
    MLHD_PLUS_FILES = ["mlhdplus-complete-0.tar"]
    uploader = ListenbrainzDataUploader()
    for file in MLHD_PLUS_FILES:
        with tempfile.TemporaryFile() as temp_dest:
            download_mlhd_plus_dump_file(file, temp_dest)
            uploader.upload_mlhd_dump_chunk(temp_dest)

    return [{
        'type': 'import_mlhd_dump',
        'time': str(datetime.utcnow()),
    }]
