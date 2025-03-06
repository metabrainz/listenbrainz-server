import json

import requests_mock

from listenbrainz_spark.fresh_releases import fresh_releases
from listenbrainz_spark.fresh_releases.fresh_releases import FRESH_RELEASES_ENDPOINT
from listenbrainz_spark.listens.dump import import_incremental_dump_to_hdfs
from listenbrainz_spark.tests import SparkNewTestCase


class FreshReleasesTestCase(SparkNewTestCase):

    def setUp(self):
        super(FreshReleasesTestCase, self).setUp()
        import_incremental_dump_to_hdfs(self.dump_loader, 4)

    def tearDown(self):
        self.delete_uploaded_listens()
        super(FreshReleasesTestCase, self).tearDown()

    @requests_mock.Mocker(real_http=True)
    def test_fresh_releases(self, mock_requests):
        with open(self.path_to_data_file("sitewide_fresh_releases.json")) as f:
            data = json.load(f)
        mock_requests.get(FRESH_RELEASES_ENDPOINT, status_code=200, json=data)

        with open(self.path_to_data_file("user_fresh_releases_output.json")) as f:
            expected = json.load(f)

        database = "fresh_releases_20220919"

        itr = fresh_releases.main(None, database, 0)

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
