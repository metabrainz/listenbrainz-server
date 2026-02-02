import json
import requests

from unittest.mock import patch
import datetime

from listenbrainz.tests.integration import IntegrationTestCase
from listenbrainz.db import user as db_user
from listenbrainz.db import fresh_releases as db_fresh
from listenbrainz.db import couchdb


class FreshReleasesTestCase(IntegrationTestCase):
    @classmethod
    def setUpClass(cls):
        super(FreshReleasesTestCase, cls).setUpClass()
        cls.database = "fresh_releases_20220920"
        couchdb.create_database(cls.database)

    @classmethod
    def tearDownClass(cls):
        couchdb_url = f"{couchdb.get_base_url()}/{cls.database}"
        requests.delete(couchdb_url)
        super(FreshReleasesTestCase, cls).tearDownClass()

    def setUp(self):
        super(FreshReleasesTestCase, self).setUp()
        self.user = db_user.get_or_create(self.db_conn, 1, "testuserpleaseignore")

        with open(self.path_to_data_file("user_fresh_releases.json")) as f:
            self.expected = json.load(f)

        db_fresh.insert_fresh_releases(self.database, [{
            "user_id": self.user["id"],
            "releases": self.expected
        }])

    @patch('listenbrainz.webserver.views.fresh_releases.datetime')
    def test_fetch_fresh_releases(self, mock_datetime):
        # Mock today to be consistent with JSON data (May 2022)
        mock_datetime.date.today.return_value = datetime.date(2022, 6, 1)
        mock_datetime.datetime.strptime = datetime.datetime.strptime
        mock_datetime.timedelta = datetime.timedelta

        r = self.client.get(
            self.custom_url_for("fresh_releases_v1.get_releases", user_name=self.user["musicbrainz_id"])
        )
        self.assert200(r)

        # Releases should be filtered by default (Today - 14 days = May 18, 2022)
        # 2022-05-27 and 2022-05-30 are in range. 2022-06-09 is in future (future=True by default).
        self.assertEqual(r.json, {"payload": {
            "user_id": self.user["musicbrainz_id"],
            "releases": self.expected
        }})

    @patch('listenbrainz.webserver.views.fresh_releases.datetime')
    def test_fetch_fresh_releases_days(self, mock_datetime):
        # Mock today to June 1st 2022
        mock_datetime.date.today.return_value = datetime.date(2022, 6, 1)
        mock_datetime.datetime.strptime = datetime.datetime.strptime
        mock_datetime.timedelta = datetime.timedelta

        # Range = 5 days.
        # 2022-5-30 is 2 days ago (IN)
        # 2022-5-27 is 5 days ago (IN)
        # 2022-6-09 is 8 days in future (OUT)
        r = self.client.get(
            self.custom_url_for("fresh_releases_v1.get_releases", user_name=self.user["musicbrainz_id"], days=5)
        )
        self.assert200(r)
        self.assertEqual(len(r.json["payload"]["releases"]), 2)

        # Range = 2 days.
        # 2022-5-30 is 2 days ago (IN)
        # 2022-5-27 is 5 days ago (OUT)
        r = self.client.get(
            self.custom_url_for("fresh_releases_v1.get_releases", user_name=self.user["musicbrainz_id"], days=2)
        )
        self.assert200(r)
        self.assertEqual(len(r.json["payload"]["releases"]), 1)
