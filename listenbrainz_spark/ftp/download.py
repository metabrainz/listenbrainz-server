from time import time

from listenbrainz_spark.ftp import ListenBrainzFTPDownloader
from listenbrainz_spark.exceptions import DumpNotFoundException

from flask import current_app

class ListenbrainzDataDownloader(ListenBrainzFTPDownloader):

    def get_mapping_file_name(self, mapping_dump_name):
        """ Get the name of the Spark mapping dump archive from the dump directory name

            Args:
                mapping_dump_name (str): FTP dump directory name.

            Returns:
                '' : Spark mapping dump archive name
        """
        return mapping_dump_name + '.tar.bz2'

    def get_listens_file_name(self, listens_dump_name):
        """ Get the name of Spark listens dump name archive from the dump directory name.

            Args:
                listens_dump_name (str): FTP dump directory name.

            Returns:
                '' : Spark listens dump archive name.
        """
        return listens_dump_name + '-spark-full.tar.xz'

    def download_msid_mbid_mapping(self, directory, mapping_dump_id=None):
        """ Download msid_mbid_mapping to dir passed as an argument.

            Args:
                directory (str): Dir to save mappings locally.
                mapping_dump_id (int): Unique identifier of mapping to be downloaded.
                    If not provided, most recent mapping would be downloaded.

            Returns:
                dest_path (str): Local path where mapping has been downloaded.
        """
        self.connection.cwd('/pub/musicbrainz/listenbrainz/labs/mappings/msid-mbid-mapping/')
        mappings_dump = self.list_dir()
        if mapping_dump_id:
            for mapping_name in mappings_dump:
                if int(mapping_name.split('-')[3] == mapping_dump_id):
                    req_mapping_dump = mapping_name
                    break
                else:
                    err_msg = "Could not find mappings with ID: {}. Aborting...".format(mapping_dump_id)
                    raise DumpNotFoundException(err_msg)
        else:
            req_mapping_dump = mappings_dump[-1]

        self.connection.cwd(req_mapping_dump)
        mapping_file_name = self.get_mapping_file_name(req_mapping_dump)

        t0 = time()
        current_app.logger.info('Downloading {} from FTP...'.format(mapping_file_name))
        dest_path = self.download_dump(mapping_file_name, directory)
        current_app.logger.info('Done. Total time: {:.2f}'.format(time() - t0))
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
                    If not provided, most recent listens would be downloaded.

            Returns:
                dest_path (str): Local path where listens have been downloaded.
        """
        self.connection.cwd('/pub/musicbrainz/listenbrainz/fullexport/')
        listens_dump = self.list_dir()
        if dump_id:
            for listens_dump_name in listens_dump:
                if int(listens_dump_name.split('-')[2] == listens_dump_id):
                    req_listens_dump = listens_dump_name
                    break
                else:
                    err_msg = "Could not find listen dump with ID: {}. Aborting...".format(listens_dump_id)
                    raise DumpNotFoundException(err_msg)
        else:
            req_listens_dump = config.TEMP_LISTENS_DUMP + '-' + 'full/'

        self.connection.cwd(req_listens_dump)
        listens_file_name = self.get_listens_file_name(req_listens_dump)

        t0 = time()
        current_app.logger.info('Downloading {} from FTP...'.format(listens_file_name))
        dest_path = self.download_dump(listens_file_name, directory)
        current_app.logger.info('Done. Total time: {:.2f}'.format(time() - t0))
        return dest_path
