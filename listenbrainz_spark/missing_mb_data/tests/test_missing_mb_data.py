import json

from listenbrainz_spark.listens.dump import import_incremental_dump_to_hdfs
from listenbrainz_spark.missing_mb_data import missing_mb_data
from listenbrainz_spark.tests import SparkNewTestCase


class MissingMBDataTestCase(SparkNewTestCase):

    def test_get_data_missing_from_musicbrainz(self):
        import_incremental_dump_to_hdfs(self.dump_loader, 5)
        # use a very long day range so that listens are used
        messages = missing_mb_data.main(10000)
        with open(self.path_to_data_file('missing_musicbrainz_data.json')) as f:
            expected_missing_mb_data = json.load(f)
        print(json.dumps(expected_missing_mb_data, indent=2))
        self.assertCountEqual(expected_missing_mb_data, messages)
