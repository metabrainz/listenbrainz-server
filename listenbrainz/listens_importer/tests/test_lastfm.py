import unittest
from datetime import datetime, timezone
from unittest.mock import MagicMock

import requests
import requests_mock
from sqlalchemy import text
import listenbrainz.webserver
import listenbrainz.db.user as db_user
from data.model.external_service import ExternalServiceType
from listenbrainz.domain.external_service import ExternalServiceAPIError
from listenbrainz.domain.lastfm import LastfmService
from listenbrainz.listens_importer.lastfm import BaseLastfmImporter
from listenbrainz.listens_importer.librefm import LibrefmImporter
from listenbrainz.db.testing import DatabaseTestCase
from listenbrainz.db import external_service_oauth as db_oauth, listens_importer


class LastfmImporterTestCase(DatabaseTestCase):

    def setUp(self):
        super(LastfmImporterTestCase, self).setUp()
        self.app = listenbrainz.webserver.create_app()
        self.app.config["TESTING"] = True
        self.app.config["LASTFM_API_KEY"] = "test_api_key"
        self.app.config["LASTFM_API_URL"] = "https://ws.audioscrobbler.com/2.0/"

        self.user1 = db_user.get_or_create(self.db_conn, 1, "testuser1")
        self.user2 = db_user.get_or_create(self.db_conn, 2, "testuser2")
        self.user3 = db_user.get_or_create(self.db_conn, 3, "testuser3")
        self.user4 = db_user.get_or_create(self.db_conn, 4, "testuser4")
        
        for user, external_user_id in [
            (self.user1, "lastfm_user_success"),
            (self.user2, "lastfm_user_privacy"),
            (self.user3, "lastfm_user_notfound"),
            (self.user4, "lastfm_user_internal_server")
        ]:
            db_oauth.save_token(
                self.db_conn,
                user_id=user["id"],
                service=ExternalServiceType.LASTFM,
                access_token=None,
                refresh_token=None,
                token_expires_ts=None,
                record_listens=True,
                scopes=[],
                external_user_id=external_user_id,
                latest_listened_at=datetime.fromtimestamp(0, timezone.utc)
            )

    def _mock_lastfm_response(self, request, context):
        """Mock function that returns different responses based on the user parameter"""
        user = request.qs.get("user", [None])[0]

        if user == "lastfm_user_success":
            context.status_code = 200
            return {
                "recenttracks": {
                    "@attr": {
                        "user": user,
                        "totalPages": "0",
                        "page": "1",
                        "perPage": "200",
                        "total": "0"
                    },
                    "track": []
                }
            }
        elif user == "lastfm_user_privacy":
            context.status_code = 400
            return {
                "error": 17,
                "message": "Login: User required to be logged in"
            }
        elif user == "lastfm_user_notfound":
            context.status_code = 404
            return {
                "error": 6,
                "message": "User not found"
            }
        else:
            context.status_code = 500
            return {"error": "Unknown error"}

    def test_non_retryable_errors_and_user_exclusion(self):
        """Test that non-retryable errors are recorded with retry=false and users are excluded from subsequent runs"""
        with self.app.app_context(), requests_mock.Mocker() as m:
            m.get(
                self.app.config["LASTFM_API_URL"],
                json=self._mock_lastfm_response
            )

            importer = BaseLastfmImporter(
                name="TestLastfmImporter",
                user_friendly_name="Test Last.fm",
                service=LastfmService(),
                api_base_url=self.app.config["LASTFM_API_URL"],
                api_key=self.app.config["LASTFM_API_KEY"]
            )

            success, failure = importer.process_all_users()

            self.assertEqual(success, 1)
            self.assertEqual(failure, 3)

            user1_status = listens_importer.get_import_status(
                self.db_conn, self.user1["id"], ExternalServiceType.LASTFM
            )
            self.assertIsNone(user1_status.get("error"))

            user2_status = listens_importer.get_import_status(
                self.db_conn, self.user2["id"], ExternalServiceType.LASTFM
            )
            error2 = user2_status.get("error")
            self.assertIsNotNone(error2)
            self.assertEqual(error2["retry"], False)
            self.assertIn("privacy mode", error2["message"])

            user3_status = listens_importer.get_import_status(
                self.db_conn, self.user3["id"], ExternalServiceType.LASTFM
            )
            error3 = user3_status.get("error")
            self.assertIsNotNone(error3)
            self.assertEqual(error3["retry"], False)
            self.assertIn("not found", error3["message"])
            
            user4_status = listens_importer.get_import_status(
                self.db_conn, self.user4["id"], ExternalServiceType.LASTFM
            )
            error4 = user4_status.get("error")
            self.assertIsNotNone(error4)
            self.assertEqual(error4["retry"], True)
            self.assertIn("Unknown error", error4["message"])

            # second run, include users with retryable errors 
            success2, failure2 = importer.process_all_users()

            self.assertEqual(success2, 1)
            self.assertEqual(failure2, 1)


class LastfmRecentTracksTestCase(unittest.TestCase):

    def setUp(self):
        self.importer = BaseLastfmImporter("t", "t", MagicMock(), "https://ws.audioscrobbler.com/2.0/", "k")
        self.user = {"external_user_id": "u", "latest_listened_at": datetime.fromtimestamp(0, timezone.utc)}

    def _get(self, **kwargs):
        with requests_mock.Mocker() as m:
            m.get("https://ws.audioscrobbler.com/2.0/", **kwargs)
            return self.importer.get_user_recent_tracks(requests.Session(), self.user, page=1)

    def test_invalid_json(self):
        with self.assertRaises(ExternalServiceAPIError):
            self._get(text="", status_code=200)
        with self.assertRaises(ExternalServiceAPIError):
            self._get(text="", status_code=400)

    def test_error_payload(self):
        with self.assertRaises(ExternalServiceAPIError):
            self._get(json={"error": 8, "message": "Operation failed"}, status_code=200)

    def test_librefm_empty_range(self):
        data = self._get(json={"error": {"code": "7"}}, status_code=200)
        self.assertEqual(data["recenttracks"]["track"], [])

    def test_single_track_dict_normalized_to_list(self):
        """Libre.fm returns a dict instead of a list when there is one track."""
        single_track = {"name": "Song", "artist": {"#text": "Artist", "mbid": ""}, "album": {"#text": "", "mbid": ""}, "date": {"uts": "1000"}}
        data = self._get(json={"recenttracks": {"@attr": {"totalPages": "1"}, "track": single_track}}, status_code=200)
        self.assertIsInstance(data["recenttracks"]["track"], list)
        self.assertEqual(len(data["recenttracks"]["track"]), 1)
        self.assertEqual(data["recenttracks"]["track"][0]["name"], "Song")

    def test_multi_track_list_unchanged(self):
        tracks = [{"name": "A"}, {"name": "B"}]
        data = self._get(json={"recenttracks": {"@attr": {"totalPages": "1"}, "track": tracks}}, status_code=200)
        self.assertIsInstance(data["recenttracks"]["track"], list)
        self.assertEqual(len(data["recenttracks"]["track"]), 2)


class LibrefmImporterTestCase(DatabaseTestCase):
    def setUp(self):
        super().setUp()
        self.app = listenbrainz.webserver.create_app()
        self.app.config["TESTING"] = True
        self.app.config["LIBREFM_API_KEY"] = "test_api_key"
        self.app.config["LIBREFM_API_URL"] = "https://ws.audioscrobbler.com/2.0/"

        self.user = db_user.get_or_create(self.db_conn, 5, "librefm_testuser")
        db_oauth.save_token(
            self.db_conn,
            user_id=self.user["id"],
            service=ExternalServiceType.LIBREFM,
            access_token=None,
            refresh_token=None,
            token_expires_ts=None,
            record_listens=True,
            scopes=[],
            external_user_id="deleted_librefm_user",
            latest_listened_at=datetime.fromtimestamp(0, timezone.utc),
        )

    def test_deleted_user_disconnects_and_records_non_retryable_error(self):
        def mock_response(request, context):
            return {"error": {"#text": "Invalid resource specified", "code": "7"}}

        with self.app.app_context(), requests_mock.Mocker() as mocker:
            mocker.get(self.app.config["LIBREFM_API_URL"], json=mock_response)
            importer = LibrefmImporter()
            result = importer.process_all_users()

        status = listens_importer.get_import_status(
            self.db_conn, self.user["id"], ExternalServiceType.LIBREFM
        )
        token = db_oauth.get_token(
            self.db_conn, self.user["id"], ExternalServiceType.LIBREFM
        )

        self.assertEqual(result, (0, 1))
        self.assertEqual(status["status"]["state"], "Error")
        self.assertFalse(status["error"]["retry"])
        self.assertIn("not found", status["error"]["message"])
        self.assertIsNone(token)

    def test_existing_user_with_empty_range_stays_connected_and_synced(self):
        def mock_response(request, context):
            if request.qs["method"] == ["user.getrecenttracks"]:
                return {"error": {"#text": "Invalid resource specified", "code": "7"}}
            return {"user": {"name": "deleted_librefm_user"}}

        with self.app.app_context(), requests_mock.Mocker() as mocker:
            mocker.get(self.app.config["LIBREFM_API_URL"], json=mock_response)
            importer = LibrefmImporter()
            result = importer.process_all_users()

        status = listens_importer.get_import_status(
            self.db_conn, self.user["id"], ExternalServiceType.LIBREFM
        )
        token = db_oauth.get_token(
            self.db_conn, self.user["id"], ExternalServiceType.LIBREFM
        )

        self.assertEqual(result, (1, 0))
        self.assertEqual(status["status"]["state"], "Synced")
        self.assertIsNone(status.get("error"))
        self.assertIsNotNone(token)

    def test_reconnect_reuses_import_row_after_deleted_user_error(self):
        oauth_id_query = text("""
            SELECT id
              FROM external_service_oauth
             WHERE user_id = :user_id
               AND service = :service
        """)
        importer_row_query = text("""
            SELECT external_service_oauth_id
                 , error
              FROM listens_importer
             WHERE user_id = :user_id
               AND service = :service
        """)
        query_params = {
            "user_id": self.user["id"],
            "service": ExternalServiceType.LIBREFM.value,
        }
        original_oauth_id = self.db_conn.execute(oauth_id_query, query_params).scalar_one()

        def deleted_user_response(request, context):
            return {"error": {"#text": "Invalid resource specified", "code": "7"}}

        with self.app.app_context(), requests_mock.Mocker() as mocker:
            mocker.get(self.app.config["LIBREFM_API_URL"], json=deleted_user_response)
            importer = LibrefmImporter()
            result = importer.process_all_users()

        status = listens_importer.get_import_status(
            self.db_conn, self.user["id"], ExternalServiceType.LIBREFM
        )
        importer_row = self.db_conn.execute(importer_row_query, query_params).mappings().one()
        token = db_oauth.get_token(
            self.db_conn, self.user["id"], ExternalServiceType.LIBREFM
        )

        self.assertEqual(result, (0, 1))
        self.assertEqual(status["status"]["state"], "Error")
        self.assertFalse(status["error"]["retry"])
        self.assertIn("not found", status["error"]["message"])
        self.assertIsNone(token)
        self.assertIsNone(importer_row["external_service_oauth_id"])
        self.assertEqual(importer_row["error"], status["error"])

        db_oauth.save_token(
            self.db_conn,
            user_id=self.user["id"],
            service=ExternalServiceType.LIBREFM,
            access_token="new_access_token",
            refresh_token=None,
            token_expires_ts=None,
            record_listens=True,
            scopes=[],
            external_user_id="reconnected_librefm_user",
            latest_listened_at=datetime.fromtimestamp(0, timezone.utc),
        )

        new_oauth_id = self.db_conn.execute(oauth_id_query, query_params).scalar_one()
        importer_row = self.db_conn.execute(importer_row_query, query_params).mappings().one()
        status = listens_importer.get_import_status(
            self.db_conn, self.user["id"], ExternalServiceType.LIBREFM
        )

        self.assertNotEqual(new_oauth_id, original_oauth_id)
        self.assertEqual(importer_row["external_service_oauth_id"], new_oauth_id)
        self.assertIsNone(importer_row["error"])
        self.assertNotEqual((status.get("status") or {}).get("state"), "Error")
        self.assertIsNone(status.get("error"))

        def reconnected_user_response(request, context):
            if request.qs["method"] == ["user.getrecenttracks"]:
                return {"error": {"#text": "Invalid resource specified", "code": "7"}}
            return {"user": {"name": "reconnected_librefm_user"}}

        with self.app.app_context(), requests_mock.Mocker() as mocker:
            mocker.get(self.app.config["LIBREFM_API_URL"], json=reconnected_user_response)
            result = LibrefmImporter().process_all_users()

        status = listens_importer.get_import_status(
            self.db_conn, self.user["id"], ExternalServiceType.LIBREFM
        )
        token = db_oauth.get_token(
            self.db_conn, self.user["id"], ExternalServiceType.LIBREFM
        )

        self.assertEqual(result, (1, 0))
        self.assertEqual(status["status"]["state"], "Synced")
        self.assertIsNone(status.get("error"))
        self.assertIsNotNone(token)
        self.assertEqual(token["external_user_id"], "reconnected_librefm_user")

    def _assert_getinfo_failure_stays_synced(self, getinfo_response):
        def mock_response(request, context):
            if request.qs["method"] == ["user.getrecenttracks"]:
                return {"error": {"#text": "Invalid resource specified", "code": "7"}}
            return getinfo_response(context)

        with self.app.app_context(), requests_mock.Mocker() as mocker:
            mocker.get(self.app.config["LIBREFM_API_URL"], json=mock_response)
            importer = LibrefmImporter()
            result = importer.process_all_users()

        status = listens_importer.get_import_status(
            self.db_conn, self.user["id"], ExternalServiceType.LIBREFM
        )
        token = db_oauth.get_token(
            self.db_conn, self.user["id"], ExternalServiceType.LIBREFM
        )

        self.assertEqual(result, (1, 0))
        self.assertEqual(status["status"]["state"], "Synced")
        self.assertIsNone(status.get("error"))
        self.assertIsNotNone(token)

    def test_getinfo_error_code_keeps_connection_and_stays_synced(self):
        self._assert_getinfo_failure_stays_synced(
            lambda context: {"error": {"#text": "Operation failed", "code": "8"}}
        )

    def test_getinfo_http_failure_keeps_connection_and_stays_synced(self):
        def getinfo_response(context):
            context.status_code = 500
            return {"message": "Service unavailable"}

        self._assert_getinfo_failure_stays_synced(getinfo_response)

    def test_getinfo_404_keeps_connection_and_stays_synced(self):
        def getinfo_response(context):
            context.status_code = 404
            return {"message": "User not found"}

        self._assert_getinfo_failure_stays_synced(getinfo_response)

    def test_unexpected_getinfo_payload_keeps_connection_and_stays_synced(self):
        self._assert_getinfo_failure_stays_synced(lambda context: {"user": []})
