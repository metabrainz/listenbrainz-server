import hashlib
from enum import Enum
from typing import NamedTuple
from abc import ABC, abstractmethod

from listenbrainz_spark.exceptions import DumpNotFoundException


class DumpType(Enum):
    INCREMENTAL = "incremental"
    FULL = "full"


class ListensDump(NamedTuple):
    dump_id: int
    dump_date: str
    dump_tod: str
    dump_type: DumpType

    @staticmethod
    def from_dir_name(dir_name: str) -> 'ListensDump':
        # Remove / if any from the end of dir name before splitting so the dump_type is correct
        parts = dir_name.replace('/', '').split('-')
        return ListensDump(dump_id=int(parts[2]),
                           dump_date=parts[3],
                           dump_tod=parts[4],
                           dump_type=DumpType.INCREMENTAL if parts[5] == 'incremental' else DumpType.FULL)

    def get_dump_file(self):
        return f'listenbrainz-spark-dump-{self.dump_id}-{self.dump_date}' \
               f'-{self.dump_tod}-{self.dump_type.value}.tar'


class ListenbrainzDumpLoader(ABC):

    @abstractmethod
    def list_dump_directories(self, dump_type: DumpType):
        pass

    @abstractmethod
    def close(self):
        pass

    def get_latest_dump_id(self, dump_type: DumpType):
        listens_dumps = [ListensDump.from_dir_name(name) for name in self.list_dump_directories(dump_type)]
        listens_dumps.sort(key=lambda x: x.dump_id)
        return listens_dumps[-1].dump_id

    def get_dump_name_to_download(self, dump, dump_id, dump_id_pos):
        """ Get name of the dump to be downloaded.

            Args:
                dump (list): Contents of the directory from which dump will be downloaded.
                dump_id (int): Unique identifier of dump to be downloaded.
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

    def get_listens_dump_file_name(self, dump_name):
        """ Get the name of Spark listens dump name archive.

            Returns:
                str : Spark listens dump archive name.
        """
        return ListensDump.from_dir_name(dump_name).get_dump_file()

    @abstractmethod
    def load_listens(self, directory, listens_dump_id=None, dump_type: DumpType = DumpType.FULL) -> (str, str, int):
        pass

    def _calc_sha256(self, filepath: str) -> str:
        """ Takes in path of a file and calculates the SHA256 checksum for it
        """
        calculated_sha = hashlib.sha256()
        with open(filepath, "rb") as f:
            # Read and update hash string value in blocks of 4K
            for byte_block in iter(lambda: f.read(4096), b""):
                calculated_sha.update(byte_block)

        return calculated_sha.hexdigest()

    def _read_sha_file(self, filepath: str) -> str:
        """ Reads the SHA file and returns the string stripped of any whitespace and extra characters
        """
        with open(filepath, "r") as f:
            sha = f.read().lstrip().split(" ", 1)[0].strip()

        return sha
