import os
import ftplib

from listenbrainz_spark import config

from flask import current_app

class ListenBrainzFTPDownloader:

    def __init__(self):
        self.connect()

    def connect(self):
        """ Connect to FTP server.
        """
        try:
            self.connection = ftplib.FTP(config.FTP_SERVER_URI)
            self.connection.login()
        except ftplib.error_perm:
            current_app.logger.critical("Couldn't connect to FTP Server, try again...")
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
            cmd+= ' ' + path
        self.connection.retrlines(cmd, callback=callback)
        return files

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
                current_app.logger.critical("Could not download file: {}".format(str(e)))

    def download_dump(self, filename, directory):
        """ Download file with `filename` from FTP.

            Args:
                filename (str): File name of FTP dump.
                directory (str): Dir to save dump locally.

            Returns:
                dest_path (str): Local path where dump has been downloaded.
        """
        dest_path = os.path.join(directory, filename)
        self.download_file_binary(filename, dest_path)
        self.connection.cwd('/')
        return dest_path
