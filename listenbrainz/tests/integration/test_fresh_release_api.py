import json

from listenbrainz.tests.integration import IntegrationTestCase
from listenbrainz.db import user as db_user
from listenbrainz.db import fresh_releases as db_fresh
from listenbrainz.db import couchdb


class FreshReleasesTestCase(IntegrationTestCase):

    def setUp(self):
        super(FreshReleasesTestCase, self).setUp()
        self.user = db_user.get_or_create(self.db_conn, 1, "testuserpleaseignore")

        with open(self.path_to_data_file("user_fresh_releases.json")) as f:
            self.expected = json.load(f)

        database = "fresh_releases_20220920"
        couchdb.create_database(database)
        db_fresh.insert_fresh_releases(database, [{
            "user_id": self.user["id"],
            "releases": self.expected
        }])

    def test_fetch_fresh_releases(self):
        r = self.client.get(
            self.custom_url_for("fresh_releases_v1.get_releases", user_name=self.user["musicbrainz_id"])
        )
        self.assert200(r)

        self.assertEqual(r.json, {"payload": {
            "user_id": self.user["musicbrainz_id"],
            "releases": self.expected
        }})
