from unittest import TestCase
from unittest.mock import MagicMock, patch

from flask import Flask

from listenbrainz.webserver import decorators
from listenbrainz.webserver.views import entity_pages

GENRE_MBID = "0e3fc579-2d24-4f20-9dae-736e1ec78798"


class GenreEntityTest(TestCase):

    def setUp(self):
        app = Flask(__name__)
        app.config.update(TESTING=True, MB_DATABASE_URI="test")
        app.register_blueprint(entity_pages.genre_bp, url_prefix="/genre")
        self.client = app.test_client()

        self.enterContext(patch.object(decorators.timescale_connection, "_ts", object()))
        self.enterContext(patch.object(decorators.listens_db, "engine", MagicMock()))
        self.connect = self.enterContext(patch.object(entity_pages.psycopg2, "connect"))
        self.resolve = self.enterContext(patch.object(
            entity_pages, "get_genre_by_name", return_value={"genre_gid": GENRE_MBID, "name": "rock"}
        ))
        self.tags = self.enterContext(patch.object(entity_pages, "find_tagged_entities", return_value={}))
        self.load_by_mbid = self.enterContext(patch.object(
            entity_pages, "load_genres_from_mbids",
            return_value={GENRE_MBID: {"genre_gid": GENRE_MBID, "name": "rock"}},
        ))
        self.cache = self.enterContext(patch.object(entity_pages, "cache"))
        entries = {}
        self.cache.get.side_effect = lambda key, **kwargs: entries.get(key)
        self.cache.set_many.side_effect = lambda mapping, **kwargs: entries.update(mapping)
        self.enterContext(patch.object(
            entity_pages, "get_rate_limit_data",
            return_value={"key": "test-client", "limit": 30, "window": 10},
        ))
        self.rate_limit = self.enterContext(patch.object(entity_pages, "RateLimit"))
        self.rate_limit.return_value.over_limit = False

    def test_caches_the_same_genre_for_name_and_mbid(self):
        first = self.client.post("/genre/rock/")
        self.assertEqual(first.status_code, 200)
        self.assertEqual(first.json["genre_mbid"], GENRE_MBID)
        for identifier in (GENRE_MBID, "ROCK"):
            with self.subTest(identifier=identifier):
                response = self.client.post(f"/genre/{identifier}/")
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.json, first.json)

        self.connect.assert_called_once()
        self.resolve.assert_called_once()
        self.tags.assert_called_once()
        self.load_by_mbid.assert_not_called()

    def test_caches_the_canonical_name_when_mbid_is_requested_first(self):
        first = self.client.post(f"/genre/{GENRE_MBID.upper()}/")
        self.assertEqual(first.status_code, 200)
        self.assertEqual(self.client.post("/genre/rock/").json, first.json)
        self.connect.assert_called_once()
        self.resolve.assert_not_called()
        self.tags.assert_called_once()

    def test_rate_limits_before_doing_database_work(self):
        self.rate_limit.return_value.over_limit = True
        self.assertEqual(self.client.post("/genre/rock/").status_code, 429)
        self.rate_limit.assert_called_once_with("genre_page:test-client", 10, 10)
        self.connect.assert_not_called()

    def test_keeps_tagged_entities_without_cached_metadata(self):
        self.tags.return_value = {
            "release_group": {"entities": [{"mbid": "album-id", "name": "Album", "tag_count": 2}]},
            "recording": {"entities": [{"mbid": "track-id", "name": "Track", "tag_count": 3}]},
        }
        self.enterContext(patch.object(entity_pages.popularity, "get_counts", return_value=([], {})))
        self.enterContext(patch.object(entity_pages, "fetch_release_group_metadata", return_value={}))
        self.enterContext(patch.object(
            entity_pages, "load_recordings_from_mbids_with_redirects", return_value=[{"recording_mbid": None}],
        ))

        response = self.client.post("/genre/rock/")

        self.assertEqual(response.status_code, 200)
        release_group, = response.json["entities"]["release_group"]["entities"]
        recording, = response.json["entities"]["recording"]["entities"]
        self.assertEqual(release_group["mbid"], "album-id")
        self.assertEqual(release_group["name"], "Album")
        self.assertIs(release_group["has_metadata"], False)
        self.assertEqual(recording["recording_mbid"], "track-id")
        self.assertEqual(recording["recording_name"], "Track")
        self.assertIsNone(recording.get("artist_credit_name"))
