import json
import os

import requests_mock

from listenbrainz_spark import utils
from listenbrainz_spark.hdfs.utils import create_dir
from listenbrainz_spark.hdfs.utils import path_exists
from listenbrainz_spark.hdfs.utils import upload_to_HDFS
from listenbrainz_spark.fresh_releases import fresh_releases
from listenbrainz_spark.fresh_releases.fresh_releases import FRESH_RELEASES_ENDPOINT
from listenbrainz_spark.path import LISTENBRAINZ_NEW_DATA_DIRECTORY
from listenbrainz_spark.tests import SparkNewTestCase, TEST_DATA_PATH


class FreshReleasesTestCase(SparkNewTestCase):

    def setUp(self):
        super(FreshReleasesTestCase, self).setUp()
        if not path_exists(LISTENBRAINZ_NEW_DATA_DIRECTORY):
            create_dir(LISTENBRAINZ_NEW_DATA_DIRECTORY)

        upload_to_HDFS(
            os.path.join(LISTENBRAINZ_NEW_DATA_DIRECTORY, "0.parquet"),
            os.path.join(TEST_DATA_PATH, "fresh_releases_listens.parquet")
        )
        
    def tearDown(self):
        super(FreshReleasesTestCase, self).tearDown()
        self.delete_uploaded_listens()

    @requests_mock.Mocker(real_http=True)
    def test_fresh_releases(self, mock_requests):
        self.maxDiff = None

        with open(self.path_to_data_file("sitewide_fresh_releases.json")) as f:
            data = json.load(f)
        mock_requests.get(FRESH_RELEASES_ENDPOINT, status_code=200, json=data)

        with open(self.path_to_data_file("user_fresh_releases_output.json")) as f:
            expected = json.load(f)

        database = "fresh_releases_20220919"

        itr = fresh_releases.main(None, database)

        self.assertEqual(next(itr), {
            "type": "couchdb_data_start",
            "database": database
        })

        message = next(itr)
        self.assertEqual(message["type"], "fresh_releases")
        self.assertEqual(message["database"], database)
        self.assertCountEqual(message["data"], expected)

        self.assertEqual(next(itr), {
            "type": "couchdb_data_end",
            "database": database
        })


