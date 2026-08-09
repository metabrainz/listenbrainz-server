from unittest import mock

import psycopg2
import listenbrainz.db.user as db_user
from listenbrainz.tests.integration import IntegrationTestCase

_REAL_PSYCOPG2_CONNECT = psycopg2.connect


class MusicBrainzCollectionsImportTestCase(IntegrationTestCase):
    def setUp(self):
        super().setUp()

        self.alice = db_user.get_or_create(self.db_conn, 1, "alice")
        self.bob = db_user.get_or_create(self.db_conn, 2, "bob")

        self.app.config["MB_DATABASE_URI"] = "postgresql://musicbrainz"

    def test_list_collections_requires_authentication(self):
        response = self.client.get(
            self.custom_url_for("playlist_api_v1.import_musicbrainz_collections")
        )

        self.assert401(response)

    @mock.patch("listenbrainz.webserver.views.playlist_api.DictCursor", new=mock.MagicMock)
    @mock.patch("listenbrainz.webserver.views.playlist_api.psycopg2.connect")
    def test_list_collections_returns_expected_response(self, mock_connect):
        fake_cursor = mock.MagicMock()
        fake_cursor.fetchall.return_value = [
            {
                "mbid": "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
                "name": "Road Trip Songs",
                "public": True,
                "entity_type": "recording",
                "item_count": 2,
            },
            {
                "mbid": "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb",
                "name": "My Albums",
                "public": True,
                "entity_type": "release",
                "item_count": 3,
            },
        ]

        fake_mb_conn = mock.MagicMock()
        fake_mb_conn.__enter__.return_value.cursor.return_value.__enter__.return_value = (
            fake_cursor
        )

        mb_dsn = self.app.config["MB_DATABASE_URI"]

        def connect_side_effect(*args, **kwargs):
            if args and args[0] == mb_dsn:
                return fake_mb_conn
            return _REAL_PSYCOPG2_CONNECT(*args, **kwargs)

        mock_connect.side_effect = connect_side_effect

        response = self.client.get(
            self.custom_url_for("playlist_api_v1.import_musicbrainz_collections"),
            headers={"Authorization": f"Token {self.alice['auth_token']}"},
        )

        self.assert200(response)

        self.assertEqual(
            response.json,
            [
                {
                    "mbid": "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
                    "name": "Road Trip Songs",
                    "public": True,
                    "entity_type": "recording",
                    "item_count": 2,
                },
                {
                    "mbid": "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb",
                    "name": "My Albums",
                    "public": True,
                    "entity_type": "release",
                    "item_count": 3,
                },
            ],
        )

    @mock.patch("listenbrainz.webserver.views.collection.fetch_collection_payload")
    def test_public_collection_can_be_viewed_without_login(self, mock_fetch):
        mock_fetch.return_value = (
            {
                "collection": {
                    "mbid": "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
                    "name": "Road Trip Songs",
                    "public": True,
                    "entity_type": "recording",
                },
                "track_count": 1,
                "count": 100,
                "offset": 0,
                "tracks": [
                    {
                        "recording_mbid": "cccccccc-cccc-cccc-cccc-cccccccccccc",
                        "title": "Night Drive",
                        "artist_credit_name": "The Midnight",
                        "length": 123000,
                        "caa_id": 12345,
                        "caa_release_mbid": "dddddddd-dddd-dddd-dddd-dddddddddddd",
                    }
                ],
                "items": [],
                "cover_art": "<svg></svg>",
            },
            None,
        )

        response = self.client.post(
            self.custom_url_for(
                "collection.load_collection",
                collection_mbid="aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
            )
        )

        self.assert200(response)
        self.assertEqual(
            response.json["collection"]["mbid"],
            "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
        )
        self.assertEqual(response.json["collection"]["name"], "Road Trip Songs")
        self.assertEqual(response.json["collection"]["public"], True)
        self.assertEqual(response.json["collection"]["entity_type"], "recording")
        self.assertEqual(response.json["track_count"], 1)
        self.assertEqual(len(response.json["tracks"]), 1)
        self.assertEqual(response.json["items"], [])
        self.assertEqual(response.json["tracks"][0]["caa_id"], 12345)
        self.assertEqual(
            response.json["tracks"][0]["caa_release_mbid"],
            "dddddddd-dddd-dddd-dddd-dddddddddddd",
        )
        self.assertEqual(response.json["cover_art"], "<svg></svg>")
        mock_fetch.assert_called_once()
        self.assertIsNone(mock_fetch.call_args.kwargs["viewer_editor_id"])

    @mock.patch("listenbrainz.webserver.views.collection.fetch_collection_payload")
    def test_public_release_collection_returns_release_items(self, mock_fetch):
        mock_fetch.return_value = (
            {
                "collection": {
                    "mbid": "dddddddd-dddd-dddd-dddd-dddddddddddd",
                    "name": "My Albums",
                    "public": True,
                    "entity_type": "release",
                },
                "track_count": 2,
                "count": 100,
                "offset": 0,
                "tracks": [],
                "items": [
                    {
                        "release_mbid": "eeeeeeee-eeee-eeee-eeee-eeeeeeeeeeee",
                        "title": "Example Album",
                        "artist_credit_name": "Example Artist",
                        "date_year": 2020,
                        "date_month": 5,
                        "date_day": 1,
                    },
                ],
                "cover_art": None,
            },
            None,
        )

        response = self.client.post(
            self.custom_url_for(
                "collection.load_collection",
                collection_mbid="dddddddd-dddd-dddd-dddd-dddddddddddd",
            )
        )

        self.assert200(response)
        self.assertEqual(response.json["collection"]["entity_type"], "release")
        self.assertEqual(response.json["track_count"], 2)
        self.assertEqual(response.json["tracks"], [])
        self.assertEqual(len(response.json["items"]), 1)
        self.assertEqual(
            response.json["items"][0]["release_mbid"],
            "eeeeeeee-eeee-eeee-eeee-eeeeeeeeeeee",
        )

    @mock.patch("listenbrainz.webserver.views.collection.fetch_collection_payload")
    def test_private_collection_requires_login(self, mock_fetch):
        mock_fetch.return_value = (
            None,
            ({"error": "You must be logged in to access this collection"}, 401),
        )

        response = self.client.post(
            self.custom_url_for(
                "collection.load_collection",
                collection_mbid="bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb",
            )
        )

        self.assert401(response)

    @mock.patch("listenbrainz.webserver.views.collection.fetch_collection_payload")
    def test_private_collection_blocks_other_users(self, mock_fetch):
        mock_fetch.return_value = (
            None,
            ({"error": "You are not allowed to access this collection"}, 403),
        )

        self.temporary_login(self.bob["login_id"])
        response = self.client.post(
            self.custom_url_for(
                "collection.load_collection",
                collection_mbid="bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb",
            )
        )

        self.assert403(response)
        mock_fetch.assert_called_once()
        self.assertEqual(
            mock_fetch.call_args.kwargs["viewer_editor_id"],
            self.bob["musicbrainz_row_id"],
        )

    def test_collection_detail_invalid_mbid_returns_400(self):
        response = self.client.post(
            self.custom_url_for(
                "collection.load_collection",
                collection_mbid="not-a-valid-mbid",
            )
        )

        self.assert400(response)
        self.assertIn("invalid", response.json["error"].lower())

    def test_collection_detail_count_above_max_returns_400(self):
        response = self.client.post(
            self.custom_url_for(
                "collection.load_collection",
                collection_mbid="aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
            )
            + "?count=501"
        )

        self.assert400(response)
        self.assertIn("count", response.json["error"].lower())

    def test_collection_detail_count_zero_returns_400(self):
        response = self.client.post(
            self.custom_url_for(
                "collection.load_collection",
                collection_mbid="aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
            )
            + "?count=0"
        )

        self.assert400(response)
        self.assertIn("count", response.json["error"].lower())

    def test_collection_detail_negative_offset_returns_400(self):
        response = self.client.post(
            self.custom_url_for(
                "collection.load_collection",
                collection_mbid="aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
            )
            + "?offset=-1"
        )

        self.assert400(response)
        self.assertIn("offset", response.json["error"].lower())
