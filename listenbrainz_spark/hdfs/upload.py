import os
from pathlib import Path
import time
import tarfile
import tempfile
import logging

from listenbrainz_spark import schema, path, utils
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

    def process_json_listens(self, filename, data_dir, tmp_hdfs_path, append, schema):
        """ Process a file containing listens from the ListenBrainz dump and add listens to
            appropriate dataframes.

            Args:
                filename (str): File name of JSON file.
                data_dir (str): Dir to save listens to in HDFS as parquet.
                tmp_hdfs_path (str): HDFS path where listens JSON has been uploaded.
                append (bool): If true append to end of parquet rather than write.
                schema: Schema of the listens
        """
        start_time = time.monotonic()
        df = utils.read_json(tmp_hdfs_path, schema=schema)

        if filename.split('/')[-1] == 'invalid.json':
            dest_path = os.path.join(data_dir, 'invalid.parquet')
        else:
            year = filename.split('/')[-2]
            month = filename.split('/')[-1][0:-5]
            dest_path = os.path.join(data_dir, year, '{}.parquet'.format(str(month)))

        if append and utils.path_exists(dest_path):
            utils.save_parquet(df, dest_path, mode="append")
        else:
            utils.save_parquet(df, dest_path, mode="overwrite")

        logger.info("Uploading to {}...".format(dest_path))
        logger.info("File processed in {:.2f} seconds!".format(time.monotonic() - start_time))

    def upload_mapping(self, archive: str):
        """ Decompress archive and upload mapping to HDFS.

            Args:
                archive: Mapping tar file to upload.
        """
        with tarfile.open(name=archive, mode='r:bz2') as tar:
            with tempfile.TemporaryDirectory() as tmp_dump_dir:
                self.upload_archive(tmp_dump_dir, tar, path.MBID_MSID_MAPPING, schema.msid_mbid_mapping_schema,
                                    self.process_json, overwrite=True)

    def upload_artist_relation(self, archive: str):
        """ Decompress archive and upload artist relation to HDFS.

            Args:
                archive: artist relation tar file to upload.
        """
        with tarfile.open(name=archive, mode='r:bz2') as tar:
            with tempfile.TemporaryDirectory() as tmp_dump_dir:
                self.upload_archive(tmp_dump_dir, tar, path.SIMILAR_ARTIST_DATAFRAME_PATH, schema.artist_relation_schema,
                                    self.process_json, overwrite=True)

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
        utils.delete_dir(hdfs_path, recursive=True)

    def upload_new_listens_full_dump(self, archive: str):
        """ Upload new format parquet listens dumps to of a full
        dump to HDFS.

            Args:
                  archive: path to parquet listens dump to be uploaded
        """
        src_path = self.upload_archive_to_temp(archive)
        dest_path = path.LISTENBRAINZ_NEW_DATA_DIRECTORY
        # Delete existing dumps if any
        if utils.path_exists(dest_path):
            logger.info(f'Removing {dest_path} from HDFS...')
            utils.delete_dir(dest_path, recursive=True)
            logger.info('Done!')

        logger.info(f"Moving the processed files from {src_path} to {dest_path}")
        t0 = time.monotonic()

        # Check if parent directory exists, if not create a directory
        dest_path_parent = str(Path(dest_path).parent)
        if not utils.path_exists(dest_path_parent):
            utils.create_dir(dest_path_parent)

        utils.rename(src_path, dest_path)
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
            if utils.path_exists(HDFS_TEMP_DIR):
                utils.delete_dir(HDFS_TEMP_DIR, recursive=True)

            logger.info("Uploading listens to temporary directory in HDFS...")
            self.extract_and_upload_archive(archive, local_temp_dir, HDFS_TEMP_DIR)

        # dump is uploaded to HDFS_TEMP_DIR/archive_name
        archive_name = Path(archive).stem
        return str(Path(HDFS_TEMP_DIR).joinpath(archive_name))
