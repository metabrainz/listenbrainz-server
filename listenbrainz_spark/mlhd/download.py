import logging
import os
import shutil
import tarfile
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from glob import glob
from pathlib import Path

import pandas
import pycurl

import listenbrainz_spark
from listenbrainz_spark import config, path
from listenbrainz_spark.exceptions import DumpInvalidException
from listenbrainz_spark.hdfs.utils import upload_to_HDFS, delete_dir
from listenbrainz_spark.stats import run_query


logger = logging.getLogger(__name__)

MLHD_PLUS_CHUNKS = [
    "0", "1", "2", "3", "4", "5", "6", "7",
    "8", "9", "a", "b", "c", "d", "e", "f"
]


def post_process_mlhd_plus():
    """ Post process the MLHD+ dump loaded into spark.

    The listened_at field has to be converted into a Timestamp Field and the artist_credit_mbids
    field is converted to an array of mbids instead of a comma separated string.
    """
    table = "raw_mlhd_data"
    query = f"""
        SELECT user_id
             , to_timestamp(listened_at) AS listened_at
             , split(artist_credit_mbids, ',') AS artist_credit_mbids
             , release_mbid
             , recording_mbid
          FROM {table}
    """
    for chunk in MLHD_PLUS_CHUNKS:
        listenbrainz_spark\
            .session\
            .read\
            .format("parquet")\
            .option("pathGlobFilter", f"{chunk}*.parquet")\
            .parquet(config.HDFS_CLUSTER_URI + path.MLHD_PLUS_RAW_DATA_DIRECTORY)\
            .createOrReplaceTempView(table)

        run_query(query)\
            .write\
            .mode("append")\
            .partitionBy("user_id")\
            .parquet(path.MLHD_PLUS_DATA_DIRECTORY)

        logger.info(f"Processed chunk: {chunk}")


def transform_chunk(location):
    """ Transform the extracted MLHD+ chunk.

    The source dump is a bunch of small compressed csv files (one per user). However, this format
    is not amenable to HDFS storage and processing. Therefore, we transform the csv files to a smaller
    number of large parquet files. Further, also add the user_id as a column to the parquet file.
    """
    logger.info(f"Processing MLHD+ extracted listen files ...")
    t0 = time.monotonic()

    for directory in os.listdir(location):
        if not os.path.isdir(os.path.join(location, directory)):
            continue

        pattern = os.path.join(location, directory, "*.txt.zst")

        dfs = []
        for file in glob(pattern):
            # the user id is the name of the csv file, every user has its own file
            user_id = Path(file).name.split(".")[0]
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

        if not dfs:
            logger.info(f"Processed directory: {pattern} but no dump files found")

        final_df = pandas.concat(dfs)

        local_path = os.path.join(location, f"{directory}.parquet")
        final_df.to_parquet(local_path, index=False)

        hdfs_path = os.path.join(path.MLHD_PLUS_RAW_DATA_DIRECTORY, f"{directory}.parquet")
        upload_to_HDFS(hdfs_path, local_path)

        os.remove(local_path)
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


def process_chunk(filename):
    try:
        with tempfile.TemporaryDirectory() as local_temp_dir:
            downloaded_chunk = download_chunk(filename, local_temp_dir)
            extract_chunk(filename, downloaded_chunk, local_temp_dir)
            transform_chunk(local_temp_dir)
    except Exception:
        logger.error(f"Error while processing chunk {filename}: ", exc_info=True)


def import_mlhd_dump_to_hdfs():
    """ Import the MLHD+ dump. """
    MLHD_PLUS_FILES = [f"mlhdplus-complete-{chunk}.tar" for chunk in MLHD_PLUS_CHUNKS]

    with ThreadPoolExecutor(max_workers=4) as executor:
        for filename in MLHD_PLUS_FILES:
            executor.submit(process_chunk, filename)

    post_process_mlhd_plus()
    delete_dir(path.MLHD_PLUS_RAW_DATA_DIRECTORY, recursive=True)

    return [{
        'type': 'import_mlhd_dump',
        'time': str(datetime.now(tz=timezone.utc).isoformat()),
    }]
