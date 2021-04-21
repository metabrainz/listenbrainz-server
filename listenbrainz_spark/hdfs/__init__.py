import os
import pathlib
import sys
import subprocess
import time
import logging
from tarfile import TarError

import listenbrainz_spark
from listenbrainz_spark import utils, config, hdfs_connection
from listenbrainz_spark.exceptions import SparkSessionNotInitializedException, DumpInvalidException


TEMP_DIR_PATH = "/temp"

logger = logging.getLogger(__name__)


class ListenbrainzHDFSUploader:

    def __init__(self):
        hdfs_connection.init_hdfs(config.HDFS_HTTP_URI)
        try:
            listenbrainz_spark.init_spark_session('uploader')
        except SparkSessionNotInitializedException as err:
            logger.error(str(err), exc_info=True)
            sys.exit(-1)

    def _is_json_file(self, filename):
        """ Check if passed filename is a JSON file

        Args:
            filename (str): the name of the file

        Returns:
            bool: True if JSON file, False otherwise
        """
        return filename.endswith('.json')

    def get_pxz_output(self, archive, threads=8):
        """ Spawn a new pxz process to decompress tar.

            Args:
                archive: Tar to decompress.
                threads: Maximal number of threads to run simultaneously.

            Returns:
                pxz: Return pipe to pxz command.
        """
        pxz_command = ['pxz', '--decompress', '--stdout', archive, '-T{}'.format(threads)]
        pxz = subprocess.Popen(pxz_command, stdout=subprocess.PIPE)
        return pxz

    def upload_archive(self, tmp_dump_dir, tar, dest_path, schema, callback=None, overwrite=False):
        """ Upload data dump to HDFS.

            Args:
                tmp_dump_dir (str): Path to temporary directory to upload JSON.
                tar: Uncompressed tar object.
                dest_path (str): HDFS path to upload data dump.
                schema: Schema of parquet to be uploaded.
                callback: Function to process JSON files.
                overwrite: If True deletes dir at dest_path
        """
        if callback is None:
            raise NotImplementedError('Callback to process JSON missing. Aborting...')

        # Delete TEMP_DIR_PATH if it exists
        if utils.path_exists(TEMP_DIR_PATH):
            utils.delete_dir(TEMP_DIR_PATH, recursive=True)

        # Copy data from dest_path to TEMP_DIR_PATH to be merged with new data
        if not overwrite and utils.path_exists(dest_path):
            t0 = time.monotonic()
            logger.info("Copying old listens into '{}'".format(TEMP_DIR_PATH))
            utils.copy(dest_path, TEMP_DIR_PATH, overwrite=True)
            logger.info("Done! Time taken: {:.2f}".format(time.monotonic() - t0))

        logger.info("Uploading listens to temporary directory in HDFS...")
        total_files = 0
        total_time = 0.0
        for member in tar:
            if member.isfile() and self._is_json_file(member.name):
                logger.info("Uploading {}...".format(member.name))
                t0 = time.monotonic()

                try:
                    tar.extract(member)
                except TarError as err:
                    # Cleanup
                    if utils.path_exists(TEMP_DIR_PATH):
                        utils.delete_dir(TEMP_DIR_PATH, recursive=True)
                    if utils.path_exists(tmp_dump_dir):
                        utils.delete_dir(tmp_dump_dir, recursive=True)
                    raise DumpInvalidException("{} while extracting {}, aborting import".format(type(err).__name__, member.name))

                tmp_hdfs_path = os.path.join(tmp_dump_dir, member.name)
                utils.upload_to_HDFS(tmp_hdfs_path, member.name)
                callback(member.name, TEMP_DIR_PATH, tmp_hdfs_path, not overwrite, schema)
                utils.delete_dir(tmp_hdfs_path, recursive=True)
                os.remove(member.name)
                time_taken = time.monotonic() - t0
                total_files += 1
                total_time += time_taken
                logger.info("Done! Current file processed in {:.2f} sec".format(time_taken))
        logger.info("Done! Total files processed {}. Average time taken: {:.2f}".format(
            total_files, total_time / total_files
        ))

        # Delete dest_path if present
        if utils.path_exists(dest_path):
            logger.info('Removing {} from HDFS...'.format(dest_path))
            utils.delete_dir(dest_path, recursive=True)
            logger.info('Done!')

        logger.info("Moving the processed files to {}".format(dest_path))
        t0 = time.monotonic()

        # Check if parent directory exists, if not create a directory
        dest_path_parent = pathlib.Path(dest_path).parent
        if not utils.path_exists(dest_path_parent):
            utils.create_dir(dest_path_parent)

        utils.rename(TEMP_DIR_PATH, dest_path)
        utils.logger.info("Done! Time taken: {:.2f}".format(time.monotonic() - t0))

        # Cleanup
        utils.delete_dir(tmp_dump_dir, recursive=True)
