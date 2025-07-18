import json
from datetime import datetime

from pyspark.sql import Row

import listenbrainz_spark.listens.dump
from listenbrainz_spark.dump import DumpType
from listenbrainz_spark.hdfs.utils import (delete_dir, path_exists, rename)
from listenbrainz_spark.path import IMPORT_METADATA
from listenbrainz_spark.schema import import_metadata_schema
from listenbrainz_spark.tests import SparkNewTestCase
from listenbrainz_spark.utils import (create_dataframe,
                                      read_files_from_HDFS, save_parquet)


class ImporterUtilsTestCase(SparkNewTestCase):
    # use path_ as prefix for all paths in this class.
    path_ = IMPORT_METADATA

    def setUp(self):
        """ Store the testdata as parquet in HDFS before each test. """
        with open(self.path_to_data_file("import_metadata.json")) as f:
            data = json.load(f)

        df = None
        for entry in data:
            row = create_dataframe(Row(dump_id=entry["dump_id"],
                                       dump_type=entry["dump_type"],
                                       imported_at=datetime.fromtimestamp(entry["imported_at"])),
                                   schema=import_metadata_schema)
            df = df.union(row) if df else row

        save_parquet(df, self.path_)

        return super().setUp()

    def tearDown(self):
        """ Delete the parquet file stored to ensure that the tests are independant. """
        path_found = path_exists(self.path_)
        if path_found:
            delete_dir(self.path_, recursive=True)

        return super().tearDown()

    def test_get_latest_full_dump_present(self):
        """ Test to ensure correct dump is returned if full dump has been imported. """
        self.assertDictEqual(listenbrainz_spark.listens.dump.get_latest_full_dump(), {
            "dump_id": 7,
            "dump_type": "full",
            "imported_at": datetime.fromtimestamp(7)
        })

    def test_get_latest_full_dump_file_missing(self):
        """ Test to ensure 'None' is returned if metadata file is missing. """
        path_found = path_exists(self.path_)
        if path_found:
            delete_dir(self.path_, recursive=True)

        self.assertIsNone(listenbrainz_spark.listens.dump.get_latest_full_dump())

    def test_get_latest_full_dump_no_full(self):
        """ Test to ensure 'None' is returned if not full import has been made. """
        # Remove full dump entries from parquet
        import_meta_df = read_files_from_HDFS(self.path_)
        result = import_meta_df.filter(import_meta_df.dump_type != "full")

        # We have to save the dataframe as a different file and move it as the df itself is read from the file
        save_parquet(result, '/temp.parquet')
        delete_dir(self.path_, recursive=True)
        rename('/temp.parquet', self.path_)

        self.assertIsNone(listenbrainz_spark.listens.dump.get_latest_full_dump())

    def test_search_dump(self):
        """ Test to ensure 'True' is returned if appropriate dump is found and 'False' if it isn't found. """
        self.assertTrue(listenbrainz_spark.listens.dump.search_dump(4, DumpType.FULL, datetime.fromtimestamp(3)))
        self.assertFalse(listenbrainz_spark.listens.dump.search_dump(4, DumpType.FULL, datetime.fromtimestamp(5)))
        self.assertFalse(listenbrainz_spark.listens.dump.search_dump(5, DumpType.FULL, datetime.fromtimestamp(5)))

        self.assertTrue(listenbrainz_spark.listens.dump.search_dump(4, DumpType.INCREMENTAL, datetime.fromtimestamp(4)))
        self.assertFalse(
            listenbrainz_spark.listens.dump.search_dump(4, DumpType.INCREMENTAL, datetime.fromtimestamp(5)))

    def test_search_dump_file_missing(self):
        """ Test to ensure 'False' is returned if metadata file is missing. """
        path_found = path_exists(self.path_)
        if path_found:
            delete_dir(self.path_, recursive=True)

        self.assertFalse(listenbrainz_spark.listens.dump.search_dump(1, DumpType.FULL, datetime.fromtimestamp(1)))

    def test_insert_dump_data(self):
        """ Test to ensure that data is inserted correctly. """
        listenbrainz_spark.listens.dump.insert_dump_data(9, DumpType.FULL, datetime.fromtimestamp(9))
        self.assertTrue(listenbrainz_spark.listens.dump.search_dump(9, DumpType.FULL, datetime.fromtimestamp(9)))

    def test_insert_dump_data_update_date(self):
        """ Test to ensure date is updated if entry already exists. """
        self.assertFalse(
            listenbrainz_spark.listens.dump.search_dump(7, DumpType.INCREMENTAL, datetime.fromtimestamp(9)))
        listenbrainz_spark.listens.dump.insert_dump_data(7, DumpType.INCREMENTAL, datetime.fromtimestamp(9))
        self.assertTrue(listenbrainz_spark.listens.dump.search_dump(7, DumpType.INCREMENTAL, datetime.fromtimestamp(9)))
        self.assertTrue(listenbrainz_spark.listens.dump.search_dump(2, DumpType.INCREMENTAL, datetime.fromtimestamp(2)))

    def test_insert_dump_data_file_missing(self):
        """ Test to ensure a file is created if it is missing. """
        path_found = path_exists(self.path_)
        if path_found:
            delete_dir(self.path_, recursive=True)

        self.assertFalse(listenbrainz_spark.listens.dump.search_dump(1, DumpType.FULL, datetime.fromtimestamp(1)))
        listenbrainz_spark.listens.dump.insert_dump_data(1, DumpType.FULL, datetime.fromtimestamp(1))
        self.assertTrue(listenbrainz_spark.listens.dump.search_dump(1, DumpType.FULL, datetime.fromtimestamp(1)))
