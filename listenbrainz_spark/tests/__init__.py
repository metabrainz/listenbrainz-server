import os
import tarfile
import unittest
import uuid
from datetime import datetime
from pathlib import Path
from tempfile import NamedTemporaryFile

import listenbrainz_spark
from listenbrainz_spark import hdfs_connection, utils, config
from listenbrainz_spark.hdfs.upload import ListenbrainzDataUploader
from listenbrainz_spark.path import LISTENBRAINZ_NEW_DATA_DIRECTORY
from listenbrainz_spark.utils import get_listens_from_new_dump

TEST_PLAYCOUNTS_PATH = '/tests/playcounts.parquet'
TEST_DATA_PATH = os.path.join(os.path.dirname(os.path.realpath(__file__)), '..', 'testdata')
PLAYCOUNTS_COUNT = 100


class SparkNewTestCase(unittest.TestCase):

    uploader = None
    # create a very long time window to fetch all listens from storage
    begin_date = datetime(2005, 1, 1)
    end_date = datetime(2025, 1, 1)

    @classmethod
    def setUpClass(cls) -> None:
        listenbrainz_spark.init_test_session(f"spark-test-run-{uuid.uuid4()}")
        hdfs_connection.init_hdfs(config.HDFS_HTTP_URI)
        cls.uploader = ListenbrainzDataUploader()

    @classmethod
    def tearDownClass(cls):
        listenbrainz_spark.context.stop()
        cls.delete_dir()

    @classmethod
    def delete_dir(cls):
        walk = utils.hdfs_walk('/', depth=1)
        # dirs in '/'
        dirs = next(walk)[1]
        for directory in dirs:
            utils.delete_dir(os.path.join('/', directory), recursive=True)

    @staticmethod
    def create_temp_listens_tar(name: str):
        """ Create a temporary tar file containing test listens data.
            Args:
                name: the name of the directory inside testdata
                    which contains test listens data
            Returns:
                the tar file containing the listens
        """
        full_dump_path = os.path.join(TEST_DATA_PATH, name)
        files = os.listdir(full_dump_path)
        with NamedTemporaryFile('wb', suffix='.tar', delete=False) as dump_tar:
            dump_name = Path(dump_tar.name).stem
            with tarfile.open(fileobj=dump_tar, mode='w') as tar:
                for filename in files:
                    src_path = os.path.join(full_dump_path, filename)
                    dest_path = os.path.join(dump_name, filename)
                    tar.add(src_path, arcname=dest_path)
        return dump_tar

    @classmethod
    def upload_test_listens(cls):
        full_dump_tar = cls.create_temp_listens_tar('full-dump')
        inc_dump1_tar = cls.create_temp_listens_tar('incremental-dump-1')
        inc_dump2_tar = cls.create_temp_listens_tar('incremental-dump-2')
        cls.uploader.upload_new_listens_full_dump(full_dump_tar.name)
        cls.uploader.upload_new_listens_incremental_dump(inc_dump1_tar.name)
        cls.uploader.upload_new_listens_incremental_dump(inc_dump2_tar.name)

    @staticmethod
    def delete_uploaded_listens():
        if utils.path_exists(LISTENBRAINZ_NEW_DATA_DIRECTORY):
            utils.delete_dir(LISTENBRAINZ_NEW_DATA_DIRECTORY, recursive=True)

    @staticmethod
    def path_to_data_file(file_name):
        """ Returns the path of the test data file relative to listenbrainz_spark/test/__init__.py.

            Args:
                file_name: the name of the data file
        """
        return os.path.join(TEST_DATA_PATH, file_name)

    @classmethod
    def get_all_test_listens(cls):
        return get_listens_from_new_dump(cls.begin_date, cls.end_date)
