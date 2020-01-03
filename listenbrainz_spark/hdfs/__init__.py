import os
import sys
import time
import shutil
import tempfile
import subprocess

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

    def upload_archive(self, tar, dest_path, callback=None, force=False):
        """ Upload data dump to HDFS.

            Args:
                tar: Uncompressed tar object.
                dest_path (str): HDFS path to upload data dump.
                callback: Function to process JSON files.
                force: If True deletes dir at dest_path
        """
        if callback is None:
            current_app.logger.critical('Callback to process JSON missing. Aboritng...')
            sys.exit(-1)

        tmp_dump_dir = tempfile.mkdtemp()
        if force:
            current_app.logger.info('Removing {} from HDFS...'.format(dest_path))
            utils.delete_dir(dest_path, recursive=True)
            current_app.logger.info('Done!')

        file_count = 0
        total_time = 0.0
        for member in tar:
            if member.isfile() and self._is_json_file(member.name):
                current_app.logger.info('Loading {}...'.format(member.name))
                t = time.time()
                tar.extract(member)
                tmp_hdfs_path = os.path.join(tmp_dump_dir, member.name)
                hdfs_connection.client.upload(hdfs_path=tmp_hdfs_path, local_path=member.name)
                self.callback(member.name, dest_path, tmp_hdfs_path)
                utils.delete_dir(tmp_hdfs_path, recursive=True)
                os.remove(member.name)
                file_count += 1
                time_taken = time.time() - t
                current_app.logger.info("Done! Processed {} files. Current file done in {:.2f} sec".format(file_count, time_taken))
                total_time += time_taken
                average_time = total_time / file_count
                print("Total time: {:.2f}, average time: {:.2f}".format(total_time, average_time))
        utils.delete_dir(tmp_dump_dir, recursive=True)
        shutil.rmtree(tmp_dump_dir)
