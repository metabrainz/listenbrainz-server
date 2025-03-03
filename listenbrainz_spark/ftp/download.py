import logging
import time

from listenbrainz_spark.dump import DumpType
from listenbrainz_spark.ftp import ListenBrainzFTPDownloader

FULL = 'full'
INCREMENTAL = 'incremental'

logger = logging.getLogger(__name__)


class ListenbrainzDataDownloader(ListenBrainzFTPDownloader):

    def download_listens(self, directory, listens_dump_id=None, dump_type: DumpType = DumpType.FULL) -> (str, str, int):
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

    def load_listens(self, directory, listens_dump_id=None, dump_type: DumpType = DumpType.FULL) -> (str, str, int):
        return self.download_listens(directory, listens_dump_id, dump_type)
