import os

from listenbrainz_spark.dump import ListenbrainzDumpLoader, DumpType


class ListenbrainzLocalDumpLoader(ListenbrainzDumpLoader):

    def list_dump_directories(self, dump_type: DumpType):
        files = os.listdir('listenbrainz-export')
        return list(filter(lambda x: x.startswith(f'listenbrainz-dump-'), files))

    def load_listens(self, directory, listens_dump_id=None, dump_type: DumpType = DumpType.FULL) -> (str, str, int):
        dump_directories = self.list_dump_directories(dump_type)

        listens_dump_list = sorted(dump_directories, key=lambda x: int(x.split('-')[2]))
        req_listens_dump = self.get_dump_name_to_download(listens_dump_list, listens_dump_id, 2)
        listens_file_name = self.get_listens_dump_file_name(req_listens_dump)
        dest_path = os.path.join('listenbrainz-export', req_listens_dump, listens_file_name)
        dump_id = int(req_listens_dump.split('-')[2])

        return dest_path, listens_file_name, dump_id

    def close(self):
        pass
