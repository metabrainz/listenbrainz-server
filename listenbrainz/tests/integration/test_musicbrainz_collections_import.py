from unittest import mock

import listenbrainz.db.user as db_user
from listenbrainz.tests.integration import IntegrationTestCase


class MusicBrainzCollectionsImportTestCase(IntegrationTestCase):
    def setUp(self):
        super().setUp()

        # Test users
        self.alice = db_user.get_or_create(self.db_conn, 1, "alice")
        self.bob = db_user.get_or_create(self.db_conn, 2, "bob")

        self.app.config["MB_DATABASE_URI"] = "postgresql://musicbrainz"

    def test_list_collections_requires_authentication(self):
        response = self.client.get(
            self.custom_url_for("playlist_api_v1.import_musicbrainz_collections")
        )

        self.assert401(response)

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

        fake_connection = mock.MagicMock()

        mock_connect.return_value.__enter__.return_value = fake_connection


        fake_connection.cursor.return_value.__enter__.return_value = fake_cursor

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

    @mock.patch("listenbrainz.webserver.views.collection.psycopg2.connect")
    def test_public_collection_can_be_viewed_without_login(self, mock_connect):
        fake_cursor = mock.MagicMock()

    
        fake_cursor.fetchone.side_effect = [
            {
                "collection_id": 123,
                "collection_mbid": "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
                "name": "Road Trip Songs",
                "public": True,
                "owner_editor_id": 1,
            },
            {"track_count": 1},
        ]

        fake_cursor.fetchall.return_value = [
            {
                "recording_mbid": "cccccccc-cccc-cccc-cccc-cccccccccccc",
                "title": "Night Drive",
                "artist_credit_name": "The Midnight",
                "length": 123000,
            }
        ]

        fake_connection = mock.MagicMock()

        mock_connect.return_value.__enter__.return_value = fake_connection
        fake_connection.cursor.return_value.__enter__.return_value = fake_cursor

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
        self.assertEqual(
            response.json["collection"]["name"],
            "Road Trip Songs",
        )
        self.assertEqual(response.json["collection"]["public"], True)
        self.assertEqual(response.json["track_count"], 1)
        self.assertEqual(len(response.json["tracks"]), 1)

    @mock.patch("listenbrainz.webserver.views.collection.psycopg2.connect")
    def test_private_collection_requires_login(self, mock_connect):
        fake_cursor = mock.MagicMock()

        fake_cursor.fetchone.return_value = {
            "collection_id": 123,
            "collection_mbid": "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb",
            "name": "Private Favorites",
            "public": False,
            "owner_editor_id": 1,
        }

        fake_connection = mock.MagicMock()

        mock_connect.return_value.__enter__.return_value = fake_connection
        fake_connection.cursor.return_value.__enter__.return_value = fake_cursor

        response = self.client.get(
            self.custom_url_for(
                "playlist_api_v1.import_musicbrainz_collection_detail",
                collection_mbid="bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb",
            )
        )

        self.assert401(response)

    @mock.patch("listenbrainz.webserver.views.collection.psycopg2.connect")
    def test_private_collection_blocks_other_users(self, mock_connect):
        fake_cursor = mock.MagicMock()

        fake_cursor.fetchone.return_value = {
            "collection_id": 123,
            "collection_mbid": "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb",
            "name": "Private Favorites",
            "public": False,
            "owner_editor_id": 1,
        }

        fake_connection = mock.MagicMock()

        mock_connect.return_value.__enter__.return_value = fake_connection
        fake_connection.cursor.return_value.__enter__.return_value = fake_cursor

        response = self.client.get(
            self.custom_url_for(
                "playlist_api_v1.import_musicbrainz_collection_detail",
                collection_mbid="bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb",
            ),
            headers={"Authorization": f"Token {self.bob['auth_token']}"},
        )

        self.assert403(response)