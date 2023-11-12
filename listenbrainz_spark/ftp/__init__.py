import ftplib
import logging
import os

from listenbrainz_spark import config
from listenbrainz_spark.dump import DumpType, ListenbrainzDumpLoader
from listenbrainz_spark.exceptions import DumpInvalidException

logger = logging.getLogger(__name__)


class ListenBrainzFTPDownloader(ListenbrainzDumpLoader):

    def __init__(self):
        self.connect()

    def connect(self):
        """ Connect to FTP server.
        """
        try:
            self.connection = ftplib.FTP(config.FTP_SERVER_URI)
            self.connection.login()
        except ftplib.error_perm:
            logger.critical("Couldn't connect to FTP Server, try again...")
            raise SystemExit

    def list_dir(self, path=None, verbose=False):
        """ Lists the current directory
        Args:
            path (str): the directory to list, lists the current working dir if not provided
            verbose (bool): whether to return file properties or just file names
        Returns:
            [str]: a list of contents of the directory
        """
        files = []

        def callback(x):
            files.append(x)

        cmd = 'LIST' if verbose else 'NLST'
        if path:
            cmd += ' ' + path
        self.connection.retrlines(cmd, callback=callback)
        return files

    def list_dump_directories(self, dump_type: DumpType):
        if dump_type == DumpType.INCREMENTAL:
            dump_dir = os.path.join(config.FTP_LISTENS_DIR, 'incremental/')
        else:
            dump_dir = os.path.join(config.FTP_LISTENS_DIR, 'fullexport/')

        self.connection.cwd(dump_dir)
        return self.list_dir()

    def download_file_binary(self, src, dest):
        """ Download file `src` from the FTP server to `dest`

            Args:
                src (str): Path on FTP server to download file.
                dest (str): Path to save file locally.
        """
        with open(dest, 'wb') as f:
            try:
                self.connection.retrbinary('RETR {}'.format(src), f.write)
            except ftplib.error_perm as e:
                logger.critical("Could not download file: {}".format(str(e)))

    def download_dump(self, filename, directory):
        """ Download file with `filename` from FTP.

            Args:
                filename (str): File name of FTP dump.
                directory (str): Dir to save dump locally.

            Returns:
                dest_path (str): Local path where dump has been downloaded.
        """
        # Check if sha256 is present to validate the download, if not present don't download
        sha_filename = filename + '.sha256'
        dir_content = self.list_dir()
        sha_dest_path = os.path.join(directory, sha_filename)
        if sha_filename in dir_content:
            self.download_file_binary(sha_filename, sha_dest_path)
        else:
            raise DumpInvalidException("SHA256 checksum for the given file missing, aborting download.")
        dest_path = os.path.join(directory, filename)
        self.download_file_binary(filename, dest_path)

        logger.info("Verifying dump integrity...")
        calculated_sha = self._calc_sha256(dest_path)
        received_sha = self._read_sha_file(sha_dest_path)

        os.remove(sha_dest_path)
        if calculated_sha != received_sha:
            # Cleanup
            os.remove(dest_path)
            raise DumpInvalidException("""Received SHA256 checksum doesn't match the calculated checksum, aborting.
                                       Calculated SHA: {calculated_sha}. Received SHA: {received_sha}""".format(
                calculated_sha=calculated_sha, received_sha=received_sha))

        self.connection.cwd('/')
        return dest_path
