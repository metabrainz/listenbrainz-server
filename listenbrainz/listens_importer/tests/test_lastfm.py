import requests_mock
import listenbrainz.webserver
from datetime import datetime, timezone

import listenbrainz.db.user as db_user
from data.model.external_service import ExternalServiceType
from listenbrainz.domain.lastfm import LastfmService
from listenbrainz.listens_importer.lastfm import BaseLastfmImporter
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
