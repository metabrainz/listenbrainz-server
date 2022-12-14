import os
from pathlib import Path
import time
import tarfile
import tempfile
import logging

from listenbrainz_spark import schema, path, utils
from listenbrainz_spark.hdfs.utils import create_dir
from listenbrainz_spark.hdfs.utils import delete_dir
from listenbrainz_spark.hdfs.utils import path_exists
from listenbrainz_spark.hdfs.utils import upload_to_HDFS
from listenbrainz_spark.hdfs.utils import rename
from listenbrainz_spark.hdfs import ListenbrainzHDFSUploader, TEMP_DIR_PATH as HDFS_TEMP_DIR
from listenbrainz_spark.path import INCREMENTAL_DUMPS_SAVE_PATH
from listenbrainz_spark.utils import read_files_from_HDFS

logger = logging.getLogger(__name__)


class ListenbrainzDataUploader(ListenbrainzHDFSUploader):

    def process_json(self, _, dest_path, tmp_hdfs_path, __, schema):
        """ Read JSON from HDFS as a dataframe and upload to
            HDFS as a parquet.

            Args:
                dest_path (str): HDFS path to upload JSON as parquet.
                tmp_hdfs_path (str): HDFS path where JSON has been uploaded.
        """
        start_time = time.monotonic()
        df = utils.read_json(tmp_hdfs_path, schema=schema)
        logger.info("Processing {} rows...".format(df.count()))

        logger.info("Uploading to {}...".format(dest_path))
        utils.save_parquet(df, dest_path)
        logger.info("File processed in {:.2f} seconds!".format(time.monotonic() - start_time))

    def upload_artist_relation(self, archive: str):
        """ Decompress archive and upload artist relation to HDFS.

            Args:
                archive: artist relation tar file to upload.
        """
        with tarfile.open(name=archive, mode='r:bz2') as tar:
            with tempfile.TemporaryDirectory() as tmp_dump_dir:
                self.upload_archive(tmp_dump_dir, tar, path.SIMILAR_ARTIST_DATAFRAME_PATH, schema.artist_relation_schema,
                                    self.process_json, overwrite=True)

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
        hdfs_path = self.upload_archive_to_temp(archive)

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
        src_path = self.upload_archive_to_temp(archive)
        dest_path = path.LISTENBRAINZ_NEW_DATA_DIRECTORY
        # Delete existing dumps if any
        if path_exists(dest_path):
            logger.info(f'Removing {dest_path} from HDFS...')
            delete_dir(dest_path, recursive=True)
            logger.info('Done!')

        logger.info(f"Moving the processed files from {src_path} to {dest_path}")
        t0 = time.monotonic()

        # Check if parent directory exists, if not create a directory
        dest_path_parent = str(Path(dest_path).parent)
        if not path_exists(dest_path_parent):
            create_dir(dest_path_parent)

        rename(src_path, dest_path)
        utils.logger.info(f"Done! Time taken: {time.monotonic() - t0:.2f}")

    def upload_archive_to_temp(self, archive: str) -> str:
        """ Upload parquet files in archive to a temporary hdfs directory

            Args:
                archive: the archive to be uploaded
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
            self.extract_and_upload_archive(archive, local_temp_dir, HDFS_TEMP_DIR)

        # dump is uploaded to HDFS_TEMP_DIR/archive_name
        archive_name = Path(archive).stem
        return str(Path(HDFS_TEMP_DIR).joinpath(archive_name))
