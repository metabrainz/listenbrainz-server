import logging
import os
import tempfile
import time

from listenbrainz_spark import config
from listenbrainz_spark.dump import DumpType, ListensDump
from listenbrainz_spark.exceptions import DumpNotFoundException
from listenbrainz_spark.ftp import ListenBrainzFTPDownloader

# mbid_msid_mapping_with_matchable is used.
# refer to: http://ftp.musicbrainz.org/pub/musicbrainz/listenbrainz/labs/mappings/
ARTIST_RELATION_DUMP_ID_POS = 5

FULL = 'full'
INCREMENTAL = 'incremental'

logger = logging.getLogger(__name__)


class ListenbrainzDataDownloader(ListenBrainzFTPDownloader):

    def download_listens(self, directory, listens_dump_id=None, dump_type: DumpType = DumpType.FULL):
        """ Download listens to dir passed as an argument.

            Args:
                directory (str): Dir to save listens locally.
                listens_dump_id (int): Unique identifier of listens to be downloaded.
                    If not provided, most recent listens will be downloaded.
                dump_type: type of dump, full or incremental

            Returns:
                dest_path (str): Local path where listens have been downloaded.
                listens_file_name (str): name of downloaded listens dump.
                dump_id (int): Unique identifier of downloaded listens dump.
        """
        dump_directories = self.list_dump_directories(dump_type)

        listens_dump_list = sorted(dump_directories, key=lambda x: int(x.split('-')[2]))
        req_listens_dump = self.get_dump_name_to_download(listens_dump_list, listens_dump_id, 2)
        listens_file_name = self.get_listens_dump_file_name(req_listens_dump)
        dump_id = int(req_listens_dump.split('-')[2])

        self.connection.cwd(req_listens_dump)

        t0 = time.monotonic()
        logger.info('Downloading {} from FTP...'.format(listens_file_name))
        dest_path = self.download_dump(listens_file_name, directory)
        logger.info('Done. Total time: {:.2f} sec'.format(time.monotonic() - t0))
        self.connection.close()
        return dest_path, listens_file_name, dump_id

    def load_listens(self, directory, listens_dump_id=None, dump_type: DumpType = DumpType.FULL):
        return self.download_listens(directory, listens_dump_id, dump_type)

    def download_artist_relation(self, directory, artist_relation_dump_id=None):
        """ Download artist relation to dir passed as an argument.

            Args:
                directory (str): Dir to save artist relation locally.
                artist_relation_dump_id (int): Unique identifier of artist relation to be downloaded.
                    If not provided, most recent artist relation will be downloaded.

            Returns:
                dest_path (str): Local path where artist relation has been downloaded.
                artist_relation_file_name (str): file name of downloaded artist relation.
        """
        self.connection.cwd(config.FTP_ARTIST_RELATION_DIR)
        dump = self.list_dir()
        req_dump = self.get_dump_name_to_download(dump, artist_relation_dump_id, ARTIST_RELATION_DUMP_ID_POS)

        self.connection.cwd(req_dump)
        artist_relation_file_name = req_dump + '.tar.bz2'

        t0 = time.monotonic()
        logger.info('Downloading {} from FTP...'.format(artist_relation_file_name))
        dest_path = self.download_dump(artist_relation_file_name, directory)
        logger.info('Done. Total time: {:.2f} sec'.format(time.monotonic() - t0))

        return dest_path, artist_relation_file_name

    def download_release_json_dump(self, directory):
        self.connection.cwd(config.FTP_MUSICBRAINZ_DIR)
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_file = os.path.join(temp_dir, "LATEST")
            self.download_file_binary("LATEST", temp_file)
            with open(temp_file) as f:
                dump_name = f.readline().strip()
        self.connection.cwd(dump_name)

        filename = "release.tar.xz"
        logger.info(f"Downloading {filename} of dump {dump_name} from FTP...")
        t0 = time.monotonic()
        dest = os.path.join(directory, filename)
        self.download_file_binary(filename, dest)
        logger.info(f"Done. Total time: {time.monotonic() - t0:.2f} sec")
        return dest
