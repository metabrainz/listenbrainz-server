import os
from pathlib import Path
import time
import tarfile
import tempfile
import logging

from listenbrainz_spark import path, utils, hdfs_connection
from listenbrainz_spark.hdfs.utils import create_dir, move
from listenbrainz_spark.hdfs.utils import delete_dir
from listenbrainz_spark.hdfs.utils import path_exists
from listenbrainz_spark.hdfs.utils import upload_to_HDFS
from listenbrainz_spark.hdfs.utils import rename
from listenbrainz_spark.path import INCREMENTAL_DUMPS_SAVE_PATH
from listenbrainz_spark.stats import run_query
from listenbrainz_spark.utils import read_files_from_HDFS

logger = logging.getLogger(__name__)

HDFS_TEMP_DIR = "/temp"


class ListenbrainzDataUploader:

    def extract_and_upload_archive(self, archive, local_dir, hdfs_dir, extension, cleanup_on_failure=True):
        """
        Extract the archive and upload it to the given hdfs directory.
        Args:
            archive: path to the tar archive to uploaded
            local_dir: path to local dir to be used for extraction
            hdfs_dir: path to hdfs dir where contents of tar should be uploaded
            extension: the file extension members to upload
            cleanup_on_failure: whether to delete local and hdfs directories
                if error occurs during extraction
        """
        total_files = 0
        total_time = 0.0
        with tarfile.open(archive, mode='r') as tar:
            for member in tar:
                if member.isfile() and member.name.endswith(extension):
                    logger.info(f"Uploading {member.name}...")
                    t0 = time.monotonic()

                    try:
                        tar.extract(member, path=local_dir)
                    except tarfile.TarError as err:
                        if cleanup_on_failure:
                            if path_exists(hdfs_dir):
                                delete_dir(hdfs_dir, recursive=True)
                            shutil.rmtree(local_dir, ignore_errors=True)
                        raise DumpInvalidException(f"{type(err).__name__} while extracting {member.name}, aborting import")

                    hdfs_path = os.path.join(hdfs_dir, member.name)
                    local_path = os.path.join(local_dir, member.name)
                    upload_to_HDFS(hdfs_path, local_path)

                    time_taken = time.monotonic() - t0
                    total_files += 1
                    total_time += time_taken
                    logger.info(f"Done! Current file processed in {time_taken:.2f} sec")
        logger.info(f"Done! Total files processed {total_files}. Average time taken: {total_time / total_files:.2f}")

    def upload_release_json_dump(self, archive: str):
        """ Decompress archive and upload artist relation to HDFS.

            Args:
                archive: artist relation tar file to upload.
        """
        hdfs_dir = path.MUSICBRAINZ_RELEASE_DUMP
        hdfs_mbdump_dir = os.path.join(hdfs_dir, "mbdump")  # release.tar.xz file has actual dump file inside mbdump dir
        with tarfile.open(name=archive, mode="r:xz") as tar, tempfile.TemporaryDirectory() as local_dir:
            # Remove existing dumps
            if path_exists(hdfs_dir):
                delete_dir(hdfs_dir, recursive=True)

            create_dir(hdfs_dir)

            for member in tar:
                t0 = time.monotonic()
                logger.info(f"Extracting {member.name}")
                tar.extract(member, path=local_dir)
                logger.info(f"Done. Total time: {time.monotonic() - t0:.2f} sec")

                t0 = time.monotonic()
                logger.info(f"Uploading {member.name}")
                hdfs_path = os.path.join(hdfs_dir, member.name)
                local_path = os.path.join(local_dir, member.name)
                upload_to_HDFS(hdfs_path, local_path)
                logger.info(f"Done. Total time: {time.monotonic() - t0:.2f} sec")

    def upload_new_listens_incremental_dump(self, archive: str):
        """ Upload new format parquet listens of an incremental
         dump to HDFS.
            Args:
                archive: path to parquet listens dump to be uploaded
        """
        # upload parquet file to temporary path so that we can
        # read it in spark in next step
        hdfs_path = self.upload_archive_to_temp(archive, ".parquet")

        # read the parquet file from the temporary path and append
        # it to incremental.parquet for permanent storage
        read_files_from_HDFS(hdfs_path) \
            .repartition(1) \
            .write \
            .mode("append") \
            .parquet(INCREMENTAL_DUMPS_SAVE_PATH)

        # delete parquet from hdfs temporary path
        delete_dir(hdfs_path, recursive=True)

    def upload_new_listens_full_dump(self, archive: str):
        """ Upload new format parquet listens dumps to of a full
        dump to HDFS.

            Args:
                  archive: path to parquet listens dump to be uploaded
        """
        src_path = self.upload_archive_to_temp(archive, ".parquet")
        dest_path = path.LISTENBRAINZ_NEW_DATA_DIRECTORY

        t0 = time.monotonic()
        move(src_path, dest_path)
        logger.info(f"Full dump uploaded! Time taken: {time.monotonic() - t0:.2f}")

    def upload_mlhd_dump_chunk(self, archive: str):
        """ Upload MLHD+ dump to HDFS """
        dest_path = path.MLHD_PLUS_RAW_DATA_DIRECTORY

        # Check if parent directory exists, if not create a directory
        dest_path_parent = str(Path(dest_path).parent)
        if not path_exists(dest_path_parent):
            create_dir(dest_path_parent)

        src_path = self.upload_archive_to_temp(archive, ".txt.zst")
        archive_dest_path = os.path.join(dest_path, str(Path(archive).name))

        logger.info(f"Moving the processed files from {src_path} to {archive_dest_path}")
        t0 = time.monotonic()
        rename(src_path, archive_dest_path)
        logger.info(f"Done! Time taken: {time.monotonic() - t0:.2f}")

    def upload_archive_to_temp(self, archive: str, extension: str) -> str:
        """ Upload parquet files in archive to a temporary hdfs directory

            Args:
                archive: the archive to be uploaded
                extension: the file extension members to upload
            Returns:
                path of the temp dir where archive has been uploaded
            Notes:
                The following dump structure should be ensured for this
                function to work correctly. Say, the dump is named
                v-2021-08-15.tar. The tar should contain one top level
                directory, v-2021-08-15. This directory should contain
                all the files that need to be uploaded.
        """
        with tempfile.TemporaryDirectory() as local_temp_dir:
            logger.info("Cleaning HDFS temporary directory...")
            if path_exists(HDFS_TEMP_DIR):
                delete_dir(HDFS_TEMP_DIR, recursive=True)

            logger.info("Uploading listens to temporary directory in HDFS...")
            self.extract_and_upload_archive(archive, local_temp_dir, HDFS_TEMP_DIR, extension)

        # dump is uploaded to HDFS_TEMP_DIR/archive_name
        archive_name = Path(archive).stem
        return str(Path(HDFS_TEMP_DIR).joinpath(archive_name))

    def process_full_listens_dump(self):
        """ Partition the imported full listens parquet dump by year and month """
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
              from parquet.`{path.LISTENBRAINZ_NEW_DATA_DIRECTORY}`
        """
        run_query(query) \
            .write \
            .partitionBy("year", "month") \
            .mode("overwrite") \
            .parquet(path.LISTENBRAINZ_INTERMEDIATE_STATS_DIRECTORY)

        if path_exists(path.LISTENBRAINZ_BASE_STATS_DIRECTORY):
            hdfs_connection.client.delete(path.LISTENBRAINZ_BASE_STATS_DIRECTORY, recursive=True, skip_trash=True)

    def process_incremental_listens_dump(self):
        query = f"""
            SELECT user_id
                 , max(created) AS created
              FROM parquet.`{path.INCREMENTAL_DUMPS_SAVE_PATH}`
          GROUP BY user_id
        """
        run_query(query) \
            .write \
            .mode("overwrite") \
            .parquet(path.INCREMENTAL_USERS_DF)
