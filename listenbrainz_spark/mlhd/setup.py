import logging
import os
import shutil
import tarfile
import tempfile
import time
from datetime import datetime
from glob import glob
from pathlib import Path

import pandas
import pycurl

import listenbrainz_spark
from listenbrainz_spark import config, path
from listenbrainz_spark.exceptions import DumpInvalidException
from listenbrainz_spark.schema import mlhd_schema

logger = logging.getLogger(__name__)


def transform_chunk(location):
    """ Transform the extracted MLHD+ chunk.

    The source dump is a bunch of small compressed csv files (one per user). However, this format
    is not amenable to HDFS storage and processing. Therefore, we transform the csv files to a smaller
    number of large parquet files. Further, also add the user_id as a column to the parquet file.
    """
    logger.info(f"Transforming MLHD+ extracted listen files ...")
    t0 = time.monotonic()

    for directory in os.listdir(location):
        pattern = os.path.join(location, directory, "*.txt.zst")

        dfs = []
        for file in glob(pattern):
            # the user id is the name of the csv file, every user has its own file
            user_id = Path(file).stem
            # convert csv to parquet using pandas because spark workers cannot access
            # csv files on leader's local file system
            df = pandas.read_csv(
                file,
                # mlhd+ files are tab separated and do not have a header row
                sep="\t",
                names=["listened_at", "artist_credit_mbids", "release_mbid", "recording_mbid"]
            )
            df.insert(0, "user_id", user_id)
            dfs.append(df)
        final_df = pandas.concat(dfs)
        logger.info("Concatenated df in pandas")

        listenbrainz_spark.session.createDataFrame(final_df, schema=mlhd_schema)\
            .repartition(1)\
            .write\
            .mode("append")\
            .parquet(config.HDFS_CLUSTER_URI + path.MLHD_PLUS_DATA_DIRECTORY)

        logger.info(f"Processed directory: {pattern}")

    time_taken = time.monotonic() - t0
    logger.info(f"Done! Files transformed. Time taken: {time_taken:.2f}")


def extract_chunk(filename, archive, destination):
    """ Extract one chunk of MLHD+ dump. """
    logger.info(f"Extracting MLHD+ listen file {filename} ...")
    total_files = 0
    t0 = time.monotonic()

    with tarfile.open(archive, mode='r') as tar:
        for member in tar:
            if member.isfile() and member.name.endswith(".txt.zst"):
                try:
                    tar.extract(member, path=destination)
                except tarfile.TarError as err:
                    shutil.rmtree(destination, ignore_errors=True)
                    raise DumpInvalidException(f"{type(err).__name__} while extracting {member.name}, aborting import")
                total_files += 1

    time_taken = time.monotonic() - t0
    logger.info(f"Done! Total files extracted {total_files}. Time taken: {time_taken:.2f}")


def download_chunk(filename, dest) -> str:
    """ Download one chunk of MLHD+ dump and return the path of its download location """
    t0 = time.monotonic()
    logger.info(f"Downloading MLHD+ listen file {filename} ...")
    download_url = f"{config.MLHD_PLUS_DUMP_URI}/{filename}"
    download_path = os.path.join(dest, filename)

    with open(download_path, "wb") as f:
        curl = pycurl.Curl()
        curl.setopt(pycurl.URL, download_url)
        curl.setopt(pycurl.WRITEDATA, f)
        curl.perform()
        curl.close()

    logger.info(f"Done. Total time: {time.monotonic() - t0:.2f} sec")
    return download_path


def import_mlhd_dump_to_hdfs():
    """ Import the MLHD+ dump. """
    # MLHD_PLUS_CHUNKS = [
    #     "0", "1", "2", "3", "4", "5", "6", "7",
    #     "8", "9", "a", "b", "c", "d", "e", "f"
    # ]
    # MLHD_PLUS_FILES = [f"mlhdplus-complete-{chunk}.tar" for chunk in MLHD_PLUS_CHUNKS]
    MLHD_PLUS_FILES = ["mlhdplus-complete-0.tar"]
    for filename in MLHD_PLUS_FILES:
        local_temp_dir = tempfile.mkdtemp()
        downloaded_chunk = download_chunk(filename, local_temp_dir)
        extract_chunk(filename, downloaded_chunk, local_temp_dir)
        transform_chunk(local_temp_dir)

    return [{
        'type': 'import_mlhd_dump',
        'time': str(datetime.utcnow()),
    }]
