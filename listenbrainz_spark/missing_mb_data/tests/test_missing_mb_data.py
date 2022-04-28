import json

from listenbrainz_spark import utils
from listenbrainz_spark.missing_mb_data import missing_mb_data
from listenbrainz_spark.path import LISTENBRAINZ_NEW_DATA_DIRECTORY
from listenbrainz_spark.tests import SparkNewTestCase


class MissingMBDataTestCase(SparkNewTestCase):

    def test_get_data_missing_from_musicbrainz(self):
        utils.upload_to_HDFS(LISTENBRAINZ_NEW_DATA_DIRECTORY, self.path_to_data_file('rec_listens.parquet'))
        print(list(utils.hdfs_walk("/")))
        # use a very long day range so that listens are used
        messages = missing_mb_data.main(10000)
        with open(self.path_to_data_file('missing_musicbrainz_data.json')) as f:
            expected_missing_mb_data = json.load(f)
        self.assertCountEqual(expected_missing_mb_data, messages)
