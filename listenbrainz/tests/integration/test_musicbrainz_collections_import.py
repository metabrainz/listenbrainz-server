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
                "item_count": 2,
            },
            {
                "mbid": "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb",
                "name": "Private Favorites",
                "public": False,
                "item_count": 0,
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
                    "item_count": 2,
                },
                {
                    "mbid": "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb",
                    "name": "Private Favorites",
                    "public": False,
                    "item_count": 0,
                },
            ],
        )

    @mock.patch("listenbrainz.webserver.views.playlist_api.fetch_collection_payload")
    def test_public_collection_can_be_viewed_without_login(self, mock_fetch):
        mock_fetch.return_value = (
            {
                "collection": {
                    "mbid": "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
                    "name": "Road Trip Songs",
                    "public": True,
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
                    }
                ],
            },
            None,
        )

        response = self.client.get(
            self.custom_url_for(
                "playlist_api_v1.import_musicbrainz_collection_detail",
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
        self.assertEqual(response.json["track_count"], 1)
        self.assertEqual(len(response.json["tracks"]), 1)
        mock_fetch.assert_called_once()
        self.assertIsNone(mock_fetch.call_args.kwargs["viewer_editor_id"])

    @mock.patch("listenbrainz.webserver.views.playlist_api.fetch_collection_payload")
    def test_private_collection_requires_login(self, mock_fetch):
        mock_fetch.return_value = (
            None,
            ({"error": "You must be logged in to access this collection"}, 401),
        )

        response = self.client.get(
            self.custom_url_for(
                "playlist_api_v1.import_musicbrainz_collection_detail",
                collection_mbid="bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb",
            )
        )

        self.assert401(response)

    @mock.patch("listenbrainz.webserver.views.playlist_api.fetch_collection_payload")
    def test_private_collection_blocks_other_users(self, mock_fetch):
        mock_fetch.return_value = (
            None,
            ({"error": "You are not allowed to access this collection"}, 403),
        )

        response = self.client.get(
            self.custom_url_for(
                "playlist_api_v1.import_musicbrainz_collection_detail",
                collection_mbid="bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb",
            ),
            headers={"Authorization": f"Token {self.bob['auth_token']}"},
        )

        self.assert403(response)
        mock_fetch.assert_called_once()
        self.assertEqual(
            mock_fetch.call_args.kwargs["viewer_editor_id"],
            self.bob["musicbrainz_row_id"],
        )

    def test_collection_detail_invalid_mbid_returns_400(self):
        response = self.client.get(
            self.custom_url_for(
                "playlist_api_v1.import_musicbrainz_collection_detail",
                collection_mbid="not-a-valid-mbid",
            )
        )

        self.assert400(response)
        self.assertIn("invalid", response.json["error"].lower())

    def test_collection_detail_count_above_max_returns_400(self):
        response = self.client.get(
            self.custom_url_for(
                "playlist_api_v1.import_musicbrainz_collection_detail",
                collection_mbid="aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
            )
            + "?count=501"
        )

        self.assert400(response)
        self.assertIn("count", response.json["error"].lower())

    def test_collection_detail_count_zero_returns_400(self):
        response = self.client.get(
            self.custom_url_for(
                "playlist_api_v1.import_musicbrainz_collection_detail",
                collection_mbid="aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
            )
            + "?count=0"
        )

        self.assert400(response)
        self.assertIn("count", response.json["error"].lower())

    def test_collection_detail_negative_offset_returns_400(self):
        response = self.client.get(
            self.custom_url_for(
                "playlist_api_v1.import_musicbrainz_collection_detail",
                collection_mbid="aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
            )
            + "?offset=-1"
        )

        self.assert400(response)
        self.assertIn("offset", response.json["error"].lower())