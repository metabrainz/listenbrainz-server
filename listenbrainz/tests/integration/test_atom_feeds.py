from datetime import datetime
import json
import time
from uuid import UUID
from listenbrainz.db import couchdb
from listenbrainz.db.model.playlist import PLAYLIST_EXTENSION_URI, PLAYLIST_URI_PREFIX
from listenbrainz.tests.integration import ListenAPIIntegrationTestCase
from lxml import etree
from listenbrainz.db import fresh_releases as db_fresh
from data.model.common_stat import ALLOWED_STATISTICS_RANGE
import listenbrainz.db.stats as db_stats


class AtomFeedsTestCase(ListenAPIIntegrationTestCase):
    @classmethod
    def setUpClass(cls):
        super(AtomFeedsTestCase, cls).setUpClass()

        couchdb.create_database("fresh_releases_20240710")

        stats = ["artists", "recordings", "release_groups"]
        for stat in stats:
            for range in ALLOWED_STATISTICS_RANGE:
                couchdb.create_database(f"{stat}_{range}_20240710")

    def setUp(self):
        super(AtomFeedsTestCase, self).setUp()
        self.nsAtom = "{http://www.w3.org/2005/Atom}"
        self.fresh_releases_database = "fresh_releases_20240710"

        # Mon Jul 01 2024 00:00:00 GMT+0000 - Mon Jul 08 2024 00:00:00 GMT+0000
        self.stats_from_ts = 1719792000
        self.stats_to_ts = 1720396800

        with open(
            self.path_to_data_file("user_top_artists_db_data_for_api_test.json"), "r"
        ) as f:
            self.user_artist_payload = json.load(f)
            self.user_artist_payload[0]["user_id"] = self.user["id"]
        database = "artists_week_20240710"
        db_stats.insert(
            database, self.stats_from_ts, self.stats_to_ts, self.user_artist_payload
        )

        with open(
            self.path_to_data_file("user_top_release_groups_db_data_for_api_test.json"),
            "r",
        ) as f:
            self.user_release_group_payload = json.load(f)
            self.user_release_group_payload[0]["user_id"] = self.user["id"]
        database = "release_groups_week_20240710"
        db_stats.insert(
            database,
            self.stats_from_ts,
            self.stats_to_ts,
            self.user_release_group_payload,
        )

        with open(
            self.path_to_data_file("user_top_recordings_db_data_for_api_test.json"), "r"
        ) as f:
            self.recording_payload = json.load(f)
            self.recording_payload[0]["user_id"] = self.user["id"]
        database = "recordings_week_20240710"
        db_stats.insert(
            database, self.stats_from_ts, self.stats_to_ts, self.recording_payload
        )

    def test_get_listens_invalid_params(self):
        """
        Check server sends 400 for invalid params.
        """
        listens_feed_url = self.custom_url_for(
            "atom.get_listens",
            user_name=self.user["musicbrainz_id"],
        )

        # invalid param
        response = self.client.get(listens_feed_url, query_string={"minutes": "-1"})
        self.assert400(response)
        response = self.client.get(
            listens_feed_url, query_string={"minutes": "10081"}
        )  # just above 1 week
        self.assert400(response)

        # invalid user
        invalid_user_url = self.custom_url_for("atom.get_listens", user_name="invalid")
        response = self.client.get(
            invalid_user_url,
        )
        self.assert404(response)

    def test_get_fresh_releases_invalid_params(self):
        """
        Check server sends 400 for invalid params.
        """
        fresh_releases_url = self.custom_url_for("atom.get_fresh_releases")
        response = self.client.get(fresh_releases_url, query_string={"days": "0"})
        self.assert400(response)
        response = self.client.get(fresh_releases_url, query_string={"days": "91"})
        self.assert400(response)

    def test_get_stats_invalid_params(self):
        """
        Check server sends 400 for invalid params.
        """
        stats_url = self.custom_url_for(
            "atom.get_artist_stats", user_name=self.user["musicbrainz_id"]
        )
        response = self.client.get(stats_url, query_string={"range": "invalid"})
        self.assert400(response)
        response = self.client.get(stats_url, query_string={"count": "-1"})
        self.assert400(response)

    def test_get_listens_feed_elements(self):
        """
        Check server sends valid listens feed.
        """
        with open(self.path_to_data_file("valid_single.json"), "r") as f:
            payload = json.load(f)

        ts = int(time.time())
        payload["payload"][0]["listened_at"] = ts
        response = self.send_data(payload, recalculate=True)
        self.assert200(response)
        self.assertEqual(response.json["status"], "ok")

        url = self.custom_url_for(
            "atom.get_listens",
            user_name=self.user["musicbrainz_id"],
        )
        response = self.client.get(url)
        self.assert200(response)

        nsAtom = self.nsAtom
        xml_tree = etree.fromstring(response.data)

        # Check feed id
        _path = self.custom_url_for(
            "atom.get_listens",
            user_name=self.user["musicbrainz_id"],
            force_external=True,
        )
        feedId = xml_tree.find(f"{nsAtom}id")
        if feedId is None:
            self.fail("No id element found in feed")
        self.assertEqual(feedId.text, _path)

        # Check entry id
        entryId = xml_tree.find(f"{nsAtom}entry/{nsAtom}id")
        if entryId is None:
            self.fail("No id element found in feed")
        self.assertEqual(
            entryId.text,
            f"{_path}/{ts}/{payload['payload'][0]['track_metadata']['track_name']}",
        )

    def test_get_listens_entry_order(self):
        """
        Check server sends listens feed with correct entry order.
        """
        with open(self.path_to_data_file("valid_single.json"), "r") as f:
            payload = json.load(f)

        # First listen
        ts1 = int(time.time()) - 100
        payload["payload"][0]["listened_at"] = ts1
        response = self.send_data(payload, recalculate=True)
        self.assert200(response)
        self.assertEqual(response.json["status"], "ok")

        # Second listen
        ts2 = int(time.time()) - 50
        payload["payload"][0]["listened_at"] = ts2
        response = self.send_data(payload, recalculate=True)
        self.assert200(response)
        self.assertEqual(response.json["status"], "ok")

        url = self.custom_url_for(
            "atom.get_listens", user_name=self.user["musicbrainz_id"]
        )
        response = self.client.get(url)
        self.assert200(response)

        nsAtom = self.nsAtom
        xml_tree = etree.fromstring(response.data)

        _path = self.custom_url_for(
            "atom.get_listens",
            user_name=self.user["musicbrainz_id"],
            force_external=True,
        )
        element = xml_tree.findall(f"{nsAtom}entry/{nsAtom}id")
        if element is None:
            self.fail("No id element found in feed")
        self.assertEqual(len(element), 2)
        self.assertEqual(
            element[0].text,
            f"{_path}/{ts2}/{payload['payload'][0]['track_metadata']['track_name']}",
        )
        self.assertEqual(
            element[1].text,
            f"{_path}/{ts1}/{payload['payload'][0]['track_metadata']['track_name']}",
        )

    def test_get_user_fresh_releases_elements(self):
        """
        Check server sends valid user fresh releases feed.
        """
        with open(self.path_to_data_file("user_fresh_releases.json")) as f:
            releases = json.load(f)

        release_count = len(releases)
        release_name = releases[0]["release_name"]
        artist_credit_name = releases[0]["artist_credit_name"]
        release_date_str = releases[0]["release_date"]
        _t = datetime.combine(
            datetime.strptime(release_date_str, "%Y-%m-%d"), datetime.min.time()
        )
        _uts = int(_t.timestamp())

        db_fresh.insert_fresh_releases(
            self.fresh_releases_database,
            [{"user_id": self.user["id"], "releases": releases}],
        )

        url = self.custom_url_for(
            "atom.get_user_fresh_releases", user_name=self.user["musicbrainz_id"]
        )
        response = self.client.get(url)
        self.assert200(response)

        nsAtom = self.nsAtom
        xml_tree = etree.fromstring(response.data)
        _path = self.custom_url_for(
            "atom.get_user_fresh_releases",
            user_name=self.user["musicbrainz_id"],
            force_external=True,
        )

        # Check feed id
        feedId = xml_tree.find(f"{nsAtom}id")
        if feedId is None:
            self.fail("No id element found in feed")
        self.assertEqual(feedId.text, _path)

        # Check entries
        entryIds = xml_tree.findall(f"{nsAtom}entry/{nsAtom}id")
        if entryIds is None:
            self.fail("No id element found in feed")
        self.assertEqual(len(entryIds), release_count)
        self.assertEqual(
            entryIds[release_count - 1].text,
            f"{_path}/{_uts}/{artist_credit_name}/{release_name}",
        )

    def test_get_user_fresh_releases_exclude_future_releases(self):
        """
        Check server sends only past releases.
        """
        with open(self.path_to_data_file("user_fresh_releases.json")) as f:
            releases = json.load(f)

        release_count = len(releases)
        for r in releases:
            r["release_date"] = "2023-01-01"
        releases[0]["release_date"] = "2049-01-01"

        db_fresh.insert_fresh_releases(
            self.fresh_releases_database,
            [{"user_id": self.user["id"], "releases": releases}],
        )

        url = self.custom_url_for(
            "atom.get_user_fresh_releases", user_name=self.user["musicbrainz_id"]
        )
        response = self.client.get(url)
        self.assert200(response)

        nsAtom = self.nsAtom
        xml_tree = etree.fromstring(response.data)

        entryIds = xml_tree.findall(f"{nsAtom}entry/{nsAtom}id")
        if entryIds is None:
            self.fail("No id element found in feed")
        self.assertEqual(len(entryIds), release_count - 1)

    def test_get_stats_elements(self):
        """
        Check server sends valid stats feed.
        """
        for endpoint in ["artist", "release_group", "recording"]:
            _method_name = f"get_{endpoint}_stats"

            url = self.custom_url_for(
                f"atom.{_method_name}", user_name=self.user["musicbrainz_id"]
            )
            response = self.client.get(url, query_string={"range": "week"})
            self.assert200(response)

            nsAtom = self.nsAtom
            xml_tree = etree.fromstring(response.data)
            _path = self.custom_url_for(
                f"atom.{_method_name}",
                user_name=self.user["musicbrainz_id"],
                range="week",
                force_external=True,
            )

            # Check feed id
            feedId = xml_tree.find(f"{nsAtom}id")
            if feedId is None:
                self.fail("No id element found in feed")
            self.assertEqual(feedId.text, _path)

            # Check entries
            entryIds = xml_tree.find(f"{nsAtom}entry/{nsAtom}id")
            if entryIds is None:
                self.fail("No id element found in feed")
            self.assertEqual(
                entryIds.text,
                f"{_path}/{self.stats_to_ts}",
            )

    def test_get_playlist_recordings(self):
        """
        Check server sends valid playlist feed.
        """
        playlist = {
            "playlist": {
                "title": "neo soul",
                "annotation": "souls that are n-e-o.",
                "extension": {
                    PLAYLIST_EXTENSION_URI: {
                        "public": True,
                        "additional_metadata": {"what_to_get": "soul"},
                    }
                },
            }
        }

        response = self.client.post(
            self.custom_url_for("playlist_api_v1.create_playlist"),
            json=playlist,
            headers={"Authorization": "Token {}".format(self.user["auth_token"])},
        )
        self.assert200(response)

        playlist_mbid = response.json["playlist_mbid"]
        UUID(response.json["playlist_mbid"])

        response = self.client.get(
            self.custom_url_for(
                "atom.get_playlist_recordings",
                playlist_mbid=playlist_mbid,
            ),
        )
        self.assert200(response)

        nsAtom = self.nsAtom
        xml_tree = etree.fromstring(response.data)
        _path = self.custom_url_for(
            "atom.get_playlist_recordings",
            playlist_mbid=playlist_mbid,
            force_external=True,
        )

        # Check feed id
        feedId = xml_tree.find(f"{nsAtom}id")
        if feedId is None:
            self.fail("No id element found in feed")
        self.assertEqual(feedId.text, _path)
