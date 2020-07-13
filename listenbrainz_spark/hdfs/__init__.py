import os
import sys
import time
import shutil
import subprocess
from tarfile import TarError

import listenbrainz_spark
from listenbrainz_spark import utils, config, hdfs_connection
from listenbrainz_spark.exceptions import SparkSessionNotInitializedException

from flask import current_app


class ListenbrainzHDFSUploader:

    def __init__(self):
        hdfs_connection.init_hdfs(config.HDFS_HTTP_URI)
        try:
            listenbrainz_spark.init_spark_session('uploader')
        except SparkSessionNotInitializedException as err:
            current_app.logger.error(str(err), exc_info=True)
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

    def upload_archive(self, tmp_dump_dir, tar, dest_path, schema, callback=None, force=False):
        """ Upload data dump to HDFS.

            Args:
                tmp_dump_dir (str): Path to temporary directory to upload JSON.
                tar: Uncompressed tar object.
                dest_path (str): HDFS path to upload data dump.
                schema: Schema of parquet to be uploaded.
                callback: Function to process JSON files.
                force: If True deletes dir at dest_path
        """
        if callback is None:
            raise NotImplementedError('Callback to process JSON missing. Aboritng...')

        # Extract all files in tmp_dump_dir
        t = time.time()
        current_app.logger.info("Extracting dump in temporary directory")
        try:
            tar.extractall(path=tmp_dump_dir)
        except TarError as err:
            current_app.logger.error("{} while extracting tarfile, aborting import".format(type(err).__name__))
            return
        time_taken = time.time() - t
        current_app.logger.info("Extraction completed in {:.2f} seconds".format(time_taken))

        if force:
            current_app.logger.info('Removing {} from HDFS...'.format(dest_path))
            utils.delete_dir(dest_path, recursive=True)
            current_app.logger.info('Done!')

        file_count = 0
        total_time = 0.0
        for (dirpath, dirnames, filenames) in os.walk(tmp_dump_dir):
            for filename in filenames:
                if self._is_json_file(filename):
                    current_app.logger.info('Loading {}...'.format(filename))
                    t0 = time.time()
                    file_path = os.path.join(dirpath, filename)
                    tmp_hdfs_path = file_path
                    utils.upload_to_HDFS(tmp_hdfs_path, file_path)
                    callback(file_path, dest_path, tmp_hdfs_path, schema)
                    utils.delete_dir(tmp_hdfs_path, recursive=True)
                    os.remove(file_path)
                    file_count += 1
                    time_taken = time.time() - t0
                    current_app.logger.info(
                        "Done! Processed {} files. Current file done in {:.2f} sec".format(file_count, time_taken))
                    total_time += time_taken
                    average_time = total_time / file_count
                    current_app.logger.info("Total time: {:.2f}, average time: {:.2f}".format(total_time, average_time))

        utils.delete_dir(tmp_dump_dir, recursive=True)
        shutil.rmtree(tmp_dump_dir)
