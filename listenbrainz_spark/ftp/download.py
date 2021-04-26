import os
import re
import time
import logging

from listenbrainz_spark import config
from listenbrainz_spark.ftp import ListenBrainzFTPDownloader
from listenbrainz_spark.exceptions import DumpNotFoundException

# mbid_msid_mapping_with_matchable is used.
# refer to: http://ftp.musicbrainz.org/pub/musicbrainz/listenbrainz/labs/mappings/
ARTIST_RELATION_DUMP_ID_POS = 5

FULL = 'full'
INCREMENTAL = 'incremental'

logger = logging.getLogger(__name__)


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
            req_dump = None
            for dump_name in dump:
                if int(dump_name.split('-')[dump_id_pos]) == dump_id:
                    req_dump = dump_name
                    break
            if req_dump is None:
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

    def get_listens_dump_file_name(self, dump_name):
        """ Get the name of Spark listens dump name archive.

            Returns:
                str : Spark listens dump archive name.
        """
        dump_id = dump_name.split('-')[2]
        dump_date = dump_name.split('-')[3]
        dump_time_of_day = dump_name.split('-')[4]
        dump_type = 'full' if 'full' in dump_name.split('-')[5] else 'incremental'
        return 'listenbrainz-listens-dump-{dump_id}-{date}-{tod}-spark-{dump_type}.tar.xz'.format(
            dump_id=dump_id,
            date=dump_date,
            tod=dump_time_of_day,
            dump_type=dump_type,
        )

    def get_available_dumps(self, dump, mapping_name_prefix):
        """ Get list of available mapping dumps.

            Args:
                dump: list of dumps in the current working directory.
                mapping_name_prefix (str): prefix of mapping dump name.

            Returns:
                mapping: list of mapping dump names in the current working directory.
        """
        mapping = list()
        for mapping_name in dump:
            mapping_pattern = '{}-\\d+-\\d+(.tar.bz2)$'.format(mapping_name_prefix)

            if re.match(mapping_pattern, mapping_name):
                mapping.append(mapping_name)

        if len(mapping) == 0:
            err_msg = '{} type mapping not found'.format(mapping_name_prefix)
            raise DumpNotFoundException(err_msg)

        return mapping

    def get_latest_mapping(self, mapping):
        """ Get latest mapping name.

            Args:
                mapping: list of mapping dump names.

            Returns:
               latest mapping dump name.
        """
        # sort the mappings on timestamp
        def callback(mapping_name):
            res = re.findall("\\d+", mapping_name)
            _date = res[0]
            _time = res[1]
            return int(_date + _time)

        return sorted(mapping, key=callback)[-1]

    def download_msid_mbid_mapping(self, directory):
        """ Download latest msid_mbid_mapping to dir passed as an argument.

            Args:
                directory (str): Dir to save mappings locally.

            Returns:
                dest_path (str): Local path where mapping has been downloaded.
                mapping_file_name (str): file name of downloaded mapping.
        """
        self.connection.cwd(config.FTP_MSID_MBID_DIR)
        dump = self.list_dir()

        mapping = self.get_available_dumps(dump, config.MAPPING_NAME_PREFIX)

        mapping_file_name = self.get_latest_mapping(mapping)

        t0 = time.monotonic()
        logger.info('Downloading {} from FTP...'.format(mapping_file_name))
        dest_path = self.download_dump(mapping_file_name, directory)
        logger.info('Done. Total time: {:.2f} sec'.format(time.monotonic() - t0))
        return dest_path, mapping_file_name

    def download_listens(self, directory, listens_dump_id=None, dump_type=FULL):
        """ Download listens to dir passed as an argument.

            Args:
                directory (str): Dir to save listens locally.
                listens_dump_id (int): Unique identifier of listens to be downloaded.
                    If not provided, most recent listens will be downloaded.

            Returns:
                dest_path (str): Local path where listens have been downloaded.
                listens_file_name (str): name of downloaded listens dump.
                dump_id (int): Unique indentifier of downloaded listens dump.
        """
        ftp_cwd = os.path.join(config.FTP_LISTENS_DIR, 'fullexport/')
        if dump_type == INCREMENTAL:
            ftp_cwd = os.path.join(config.FTP_LISTENS_DIR, 'incremental/')
        self.connection.cwd(ftp_cwd)
        listens_dump_list = sorted(self.list_dir(), key=lambda x: int(x.split('-')[2]))
        req_listens_dump = self.get_dump_name_to_download(listens_dump_list, listens_dump_id, 2)
        dump_id = req_listens_dump.split('-')[2]

        self.connection.cwd(req_listens_dump)
        listens_file_name = self.get_listens_dump_file_name(req_listens_dump)

        t0 = time.monotonic()
        logger.info('Downloading {} from FTP...'.format(listens_file_name))
        dest_path = self.download_dump(listens_file_name, directory)
        logger.info('Done. Total time: {:.2f} sec'.format(time.monotonic() - t0))
        return dest_path, listens_file_name, int(dump_id)

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
        artist_relation_file_name = self.get_dump_archive_name(req_dump)

        t0 = time.monotonic()
        logger.info('Downloading {} from FTP...'.format(artist_relation_file_name))
        dest_path = self.download_dump(artist_relation_file_name, directory)
        logger.info('Done. Total time: {:.2f} sec'.format(time.monotonic() - t0))

        return dest_path, artist_relation_file_name
