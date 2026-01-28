from datetime import datetime

from data.model.external_service import ExternalServiceType
from listenbrainz.db.testing import DatabaseTestCase, TimescaleTestCase
from listenbrainz.db import user as db_user
from listenbrainz.db import user_setting as db_user_setting
from listenbrainz.db import external_service_oauth as db_external_service_oauth
from listenbrainz.troi.spark import get_user_details


class TestSparkPlaylists(DatabaseTestCase, TimescaleTestCase):

    def setUp(self):
        DatabaseTestCase.setUp(self)
        TimescaleTestCase.setUp(self)

    def test_get_user_details(self):
        self.maxDiff = None
        self.user1 = db_user.get_or_create(self.db_conn, 100, "user1")
        self.user2 = db_user.get_or_create(self.db_conn, 200, "user2")
        self.user3 = db_user.get_or_create(self.db_conn, 300, "user3")
        self.user4 = db_user.get_or_create(self.db_conn, 400, "user4")
        self.user5 = db_user.get_or_create(self.db_conn, 500, "user5")

        db_user_setting.update_troi_prefs(self.db_conn, self.user1["id"], True)
        db_user_setting.update_troi_prefs(self.db_conn, self.user2["id"], False)
        
        db_external_service_oauth.save_token(
            self.db_conn,
            self.user1["id"], 
            ExternalServiceType.SPOTIFY,
            "access_token",
            "refresh_token", 
            int(datetime.now().timestamp()),
            True,
            ["streaming", "user-read-email", "user-read-private", "playlist-modify-public", "playlist-modify-private"],
            "spotify_user_id"
        )
        db_external_service_oauth.save_token(
            self.db_conn,
            self.user1["id"],
            ExternalServiceType.MUSICBRAINZ_PROD,
            "access_token",
            "refresh_token",
            int(datetime.now().timestamp()),
            True,
            [],
            "musicbrainz_user_id"
        )
        db_external_service_oauth.save_token(
            self.db_conn,
            self.user1["id"],
            ExternalServiceType.LASTFM,
            "access_token",
            "refresh_token",
            int(datetime.now().timestamp()),
            False,
            [],
            "lastfm_user_id"
        )

        db_external_service_oauth.save_token(
            self.db_conn,
            self.user2["id"],
            ExternalServiceType.SPOTIFY,
            "access_token",
            "refresh_token",
            int(datetime.now().timestamp()),
            True,
            ["streaming", "user-read-email", "user-read-private", "playlist-modify-public", "playlist-modify-private"],
            "spotify_user_id2"
        )

        db_external_service_oauth.save_token(
            self.db_conn,
            self.user4["id"],
            ExternalServiceType.SPOTIFY,
            "access_token",
            "refresh_token",
            int(datetime.now().timestamp()),
            True,
            ["streaming", "user-read-email", "user-read-private"],
            "spotify_user_id3"
        )

        db_external_service_oauth.save_token(
            self.db_conn,
            self.user5["id"],
            ExternalServiceType.LASTFM,
            "access_token",
            "refresh_token",
            int(datetime.now().timestamp()),
            False,
            [],
            "lastfm_user_id2"
        )

        user_ids = [self.user1["id"], self.user2["id"], self.user3["id"], self.user4["id"], self.user5["id"]]

        user_details = get_user_details("test-slug", user_ids)
        self.assertEqual(len(user_details), 5)
        self.assertDictEqual(user_details, {
            self.user1["id"]: {
                "username": self.user1["musicbrainz_id"],
                "export_to_spotify": True,
                "existing_url": None
            },
            self.user2["id"]: {
                "username": self.user2["musicbrainz_id"],
                "export_to_spotify": False,
                "existing_url": None
            },
            self.user3["id"]: {
                "username": self.user3["musicbrainz_id"],
                "export_to_spotify": False,
                "existing_url": None
            },
            self.user4["id"]: {
                "username": self.user4["musicbrainz_id"],
                "export_to_spotify": False,
                "existing_url": None
            },
            self.user5["id"]: {
                "username": self.user5["musicbrainz_id"],
                "export_to_spotify": False,
                "existing_url": None
            }
        })
