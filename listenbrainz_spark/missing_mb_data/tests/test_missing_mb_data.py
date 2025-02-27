import json

from listenbrainz_spark.listens.dump import import_incremental_dump_to_hdfs
from listenbrainz_spark.missing_mb_data import missing_mb_data
from listenbrainz_spark.tests import SparkNewTestCase


class MissingMBDataTestCase(SparkNewTestCase):

    def setUp(self):
        super().setUp()
        import_incremental_dump_to_hdfs(self.dump_loader, 5)

    def tearDown(self):
        self.delete_uploaded_listens()
        super().tearDown()

    def test_get_data_missing_from_musicbrainz(self):
        messages = missing_mb_data.main(10000)
        with open(self.path_to_data_file("missing_musicbrainz_data.json")) as f:
            expected_missing_mb_data = json.load(f)
        self.assertCountEqual(expected_missing_mb_data, messages)
