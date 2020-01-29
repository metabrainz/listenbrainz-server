from time import time

from listenbrainz_spark.ftp import ListenBrainzFTPDownloader
from listenbrainz_spark.exceptions import DumpNotFoundException

from flask import current_app

class ListenbrainzDataDownloader(ListenBrainzFTPDownloader):

    def get_dump_name_to_download(self, dump, dump_id, dump_id_pos):
        """ Get name of the dump to be downloaded.

            Args:
                dump (list): Contents of the directory from which dump will be downloaded.
                dump_id (int): Unique indentifier of dump to be downloaded .
                dump_id_pos (int): Unique identifier position in dump name.

            Returns:
                req_dump (str): Name of the dump to be downloaded.
        """
        if dump_id:
            for dump_name in dump:
                if int(dump_name.split('-')[dump_id_pos] == dump_id):
                    req_dump = dump_name
                    break
                else:
                    err_msg = "Could not find dump with ID: {}. Aborting...".format(dump_id)
                    raise DumpNotFoundException(err_msg)
        else:
            req_dump = dump[-1]
        return req_dump

    def get_dump_archive_name(self, dump_name):
        """ Get the name of the Spark dump archive from the dump directory name.

            Args:
                dump_name (str): FTP dump directory name.

            Returns:
                '' : Spark dump archive name.
        """
        return dump_name + '.tar.bz2'

    def get_listens_file_name(self):
        """ Get the name of Spark listens dump name archive.

            Returns:
                '' : Spark listens dump archive name.
        """
        return current_app.config['TEMP_LISTENS_DUMP']

    def download_spark_dump_and_get_path(self, directory, dump_id, ftp_dump_dir, dump_id_pos):
        """ Download dump and get local (spark) path.

            Args:
                directory (str): Dir to save dump locally.
                dump_id (int): Unique identifier of dump to be downloaded.
                    If not provided, most recent dump will be downloaded.
                ftp_dump_dir (str): FTP dir to find dump.
                dump_id_pos (int): Unique identifier position in dump name.

            Returns:
                dest_path (str): Local path where dump has been downloaded.
        """
        self.connection.cwd(ftp_dump_dir)
        dump = self.list_dir()
        req_dump = self.get_dump_name_to_download(dump, dump_id, dump_id_pos)

        self.connection.cwd(req_dump)
        file_name = self.get_dump_archive_name(req_dump)

        t0 = time()
        current_app.logger.info('Downloading {} from FTP...'.format(file_name))
        dest_path = self.download_dump(file_name, directory)
        current_app.logger.info('Done. Total time: {:.2f} sec'.format(time() - t0))
        return dest_path

    def download_msid_mbid_mapping(self, directory, mapping_dump_id=None):
        """ Download msid_mbid_mapping to dir passed as an argument.

            Args:
                directory (str): Dir to save mappings locally.
                mapping_dump_id (int): Unique identifier of mapping to be downloaded.
                    If not provided, most recent mapping will be downloaded.

            Returns:
                dest_path (str): Local path where mapping has been downloaded.
        """
        MAPPING_DUMP_ID_POS = 3
        dest_path = self.download_spark_dump_and_get_path(
                        directory, mapping_dump_id, current_app.config['FTP_MSID_MBID_DIR'],
                        MAPPING_DUMP_ID_POS
                    )
        return dest_path

    def download_msid_mbid_mapping_with_text(self):
        pass

    def download_msid_mbid_mapping_with_matchable(self):
        pass

    def download_listens(self, directory, listens_dump_id=None):
        """ Download listens to dir passed as an argument.

            Args:
                directory (str): Dir to save listens locally.
                listens_dump_id (int): Unique identifier of listens to be downloaded.
                    If not provided, most recent listens will be downloaded.

            Returns:
                dest_path (str): Local path where listens have been downloaded.
        """
        self.connection.cwd(current_app.config['FTP_LISTENS_DIR'])
        listens_dump = self.list_dir()
        # Temporary listens dump name.
        req_listens_dump = current_app.config['TEMP_LISTENS_DIR']
        # req_listens_dump = self.get_dump_name_to_download(listens_dump, listens_dump_id, 2)
        # Uncomment the above command when full and incremental dumps are updated.
        # refer to: http://ftp.musicbrainz.org/pub/musicbrainz/listenbrainz/

        self.connection.cwd(req_listens_dump)
        listens_file_name = self.get_listens_file_name()

        t0 = time()
        current_app.logger.info('Downloading {} from FTP...'.format(listens_file_name))
        dest_path = self.download_dump(listens_file_name, directory)
        current_app.logger.info('Done. Total time: {:.2f} sec'.format(time() - t0))
        return dest_path

    def download_artist_relation(self, directory, artist_relation_dump_id=None):
        """ Download artist relation to dir passed as an argument.

            Args:
                directory (str): Dir to save artist relation locally.
                artist_relation_dump_id (int): Unique identifier of artist relation to be downloaded.
                    If not provided, most recent artist relation will be downloaded.

            Returns:
                dest_path (str): Local path where artist relation has been downloaded.
        """
        ARTIST_RELATION_DUMP_ID_POS = 5
        dest_path = self.download_spark_dump_and_get_path(
                        directory, artist_relation_dump_id, current_app.config['FTP_ARTIST_RELATION_DIR'],
                        ARTIST_RELATION_DUMP_ID_POS
                    )
        return dest_path
