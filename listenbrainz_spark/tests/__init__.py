import os
import tarfile
import unittest
import uuid
from pathlib import Path
from tempfile import NamedTemporaryFile

import listenbrainz_spark
from listenbrainz_spark import hdfs_connection, config
from listenbrainz_spark.dump import ListenbrainzDumpLoader, DumpType
from listenbrainz_spark.listens.dump import import_full_dump_to_hdfs, import_incremental_dump_to_hdfs
from listenbrainz_spark.path import LISTENBRAINZ_NEW_DATA_DIRECTORY, LISTENBRAINZ_INTERMEDIATE_STATS_DIRECTORY
from listenbrainz_spark.hdfs.utils import delete_dir, path_exists, hdfs_walk

TEST_PLAYCOUNTS_PATH = '/tests/playcounts.parquet'
TEST_DATA_PATH = os.path.join(os.path.dirname(os.path.realpath(__file__)), '..', 'testdata')
PLAYCOUNTS_COUNT = 100


class ListenBrainzTestDumpLoader(ListenbrainzDumpLoader):

    def list_dump_directories(self, dump_type: DumpType):
        return []

    def load_listens(self, directory, listens_dump_id=None, dump_type: DumpType = DumpType.FULL) -> (str, str, int):
        dump_name = f"{dump_type.value}-dump-{listens_dump_id}"
        dump_path = os.path.join(TEST_DATA_PATH, dump_name)
        files = os.listdir(dump_path)
        with NamedTemporaryFile("wb", suffix=".tar", dir=directory, delete=False) as dump_tar:
            tar_name = Path(dump_tar.name).stem
            with tarfile.open(fileobj=dump_tar, mode="w") as tar:
                for filename in files:
                    src_path = os.path.join(dump_path, filename)
                    tar.add(src_path, arcname=os.path.join(tar_name, filename))
        return dump_tar.name, dump_name, listens_dump_id


class SparkNewTestCase(unittest.TestCase):

    @classmethod
    def setUpClass(cls) -> None:
        listenbrainz_spark.init_test_session(f"spark-test-run-{uuid.uuid4()}")
        hdfs_connection.init_hdfs(config.HDFS_HTTP_URI)
        cls.dump_loader = ListenBrainzTestDumpLoader()

    @classmethod
    def tearDownClass(cls):
        listenbrainz_spark.context.stop()
        cls.delete_dir()

    @classmethod
    def delete_dir(cls):
        walk = hdfs_walk('/', depth=1)
        # dirs in '/'
        dirs = next(walk)[1]
        for directory in dirs:
            delete_dir(os.path.join('/', directory), recursive=True)

    @classmethod
    def upload_test_listens(cls):
        import_full_dump_to_hdfs(cls.dump_loader, 1)
        import_incremental_dump_to_hdfs(cls.dump_loader, 2)
        import_incremental_dump_to_hdfs(cls.dump_loader, 3)

    @staticmethod
    def delete_uploaded_listens():
        if path_exists(LISTENBRAINZ_NEW_DATA_DIRECTORY):
            delete_dir(LISTENBRAINZ_NEW_DATA_DIRECTORY, recursive=True)
        if path_exists(LISTENBRAINZ_INTERMEDIATE_STATS_DIRECTORY):
            delete_dir(LISTENBRAINZ_INTERMEDIATE_STATS_DIRECTORY, recursive=True)

    @staticmethod
    def path_to_data_file(file_name):
        """ Returns the path of the test data file relative to listenbrainz_spark/test/__init__.py.

            Args:
                file_name: the name of the data file
        """
        return os.path.join(TEST_DATA_PATH, file_name)
