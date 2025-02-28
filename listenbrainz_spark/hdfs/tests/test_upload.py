import os

from listenbrainz_spark.tests import SparkNewTestCase
from listenbrainz_spark.listens.data import get_listen_files_list


class HDFSDataUploaderTestCase(SparkNewTestCase):

    TEST_DATA_PATH = os.path.join(os.path.dirname(os.path.realpath(__file__)), '..', '..', 'testdata')

    def tearDown(self):
        self.delete_uploaded_listens()

    def test_upload_listens(self):
        full_dump_tar = self.create_temp_listens_tar('full-dump')
        self.uploader.upload_new_listens_full_dump(full_dump_tar.name)
        self.assertListEqual(
            get_listen_files_list(),
            ["6.parquet", "5.parquet", "4.parquet", "3.parquet",
             "2.parquet", "1.parquet", "0.parquet"]
        )

        incremental_dump_tar = self.create_temp_listens_tar('incremental-dump-1')
        self.uploader.upload_new_listens_incremental_dump(incremental_dump_tar.name)
        self.assertListEqual(
            get_listen_files_list(),
            ["incremental.parquet", "6.parquet", "5.parquet", "4.parquet",
             "3.parquet", "2.parquet", "1.parquet", "0.parquet"]
        )

    def test_upload_incremental_listens(self):
        """ Test incremental listen imports work correctly when there are no
        existing incremental dumps and when there are existing incremental dumps"""
        incremental_dump_tar_1 = self.create_temp_listens_tar('incremental-dump-1')
        self.uploader.upload_new_listens_incremental_dump(incremental_dump_tar_1.name)
        listens = self.get_all_test_listens()
        self.assertEqual(listens.count(), 9)

        incremental_dump_tar_2 = self.create_temp_listens_tar('incremental-dump-2')
        self.uploader.upload_new_listens_incremental_dump(incremental_dump_tar_2.name)
        listens = self.get_all_test_listens()
        # incremental-dump-1 has 9 listens and incremental-dump-2 has 8
        self.assertEqual(listens.count(), 17)
