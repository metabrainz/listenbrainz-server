import hashlib
import time
from datetime import datetime, timedelta, timezone

import orjson
from cryptography.fernet import Fernet
from flask_login import login_user
from sqlalchemy import event

import listenbrainz.db.user as db_user
import listenbrainz.db.user_setting as db_usersetting
from data.model.external_service import ExternalServiceType
from listenbrainz import db
from listenbrainz.db import external_service_oauth as db_oauth, funkwhale as db_funkwhale, navidrome as db_navidrome, \
    listens_importer as db_listens_importer
from listenbrainz.domain.musicbrainz import MusicBrainzService
from listenbrainz.domain.navidrome import NavidromeService
from listenbrainz.tests.integration import IntegrationTestCase
from listenbrainz.webserver.login import User
from listenbrainz.webserver.utils import get_global_props, get_initial_alerts


class GlobalPropsTestCase(IntegrationTestCase):

    def setUp(self):
        super().setUp()
        self.user = db_user.get_or_create(self.db_conn, 1, "global_props_user")
        self.app.config["NAVIDROME_ENCRYPTION_KEY"] = Fernet.generate_key().decode("utf-8")

    def _connect_every_service(self):
        user_id = self.user["id"]
        expires = int(time.time()) + 3600
        with self.app.test_request_context():
            # the MusicBrainz service type depends on the deployment
            musicbrainz = MusicBrainzService().service
        for service, token in [(ExternalServiceType.SPOTIFY, "spotify-token"),
                               (ExternalServiceType.CRITIQUEBRAINZ, "cb-token"),
                               (musicbrainz, "mb-token"),
                               (ExternalServiceType.SOUNDCLOUD, "sc-token"),
                               (ExternalServiceType.APPLE, "apple-token")]:
            db_oauth.save_token(self.db_conn, user_id=user_id, service=service, access_token=token,
                                refresh_token=f"{token}-refresh", token_expires_ts=expires,
                                record_listens=service == ExternalServiceType.SPOTIFY,
                                scopes=["streaming"])

        server_id = db_funkwhale.get_or_create_server(self.db_conn, "https://funkwhale.example", "fw-client",
                                                      "fw-secret", "read")
        self.funkwhale_expiry = datetime.now(timezone.utc) + timedelta(hours=1)
        db_funkwhale.save_token(self.db_conn, user_id, server_id, "fw-token", "fw-refresh", self.funkwhale_expiry)
        self.funkwhale_server_id = server_id

        with self.app.app_context():
            encrypted = NavidromeService()._encrypt_password("navidrome-password")
        db_navidrome.save_user_token(self.db_conn, user_id, "https://navidrome.example/", "nd-user", encrypted)

        db_usersetting.update_brainzplayer_prefs(self.db_conn, user_id, orjson.dumps({"spotifyEnabled": True}).decode())
        db_usersetting.update_flair(self.db_conn, user_id, {"name": "wave"})

    def _global_props(self):
        """ The props and alerts as a logged-in page gets them, and the main DB queries they took. """
        statements = []

        def count(conn, cursor, statement, *args):
            statements.append(statement)

        with self.app.test_request_context():
            login_user(User.from_dbrow(db_user.get(self.db_conn, self.user["id"])))
            event.listen(db.engine, "before_cursor_execute", count)
            try:
                props = orjson.loads(get_global_props())
                self.alerts = orjson.loads(get_initial_alerts())
            finally:
                event.remove(db.engine, "before_cursor_execute", count)
        return props, statements

    def test_props_for_every_connected_service(self):
        self._connect_every_service()

        props, _ = self._global_props()

        self.assertEqual(props["spotify"], {"access_token": "spotify-token", "permission": ["streaming"]})
        self.assertEqual(props["critiquebrainz"], {"access_token": "cb-token"})
        self.assertEqual(props["musicbrainz"], {"access_token": "mb-token"})
        self.assertEqual(props["soundcloud"], {"access_token": "sc-token"})
        self.assertEqual(props["appleMusic"]["music_user_token"], "apple-token-refresh")
        self.assertIn("developer_token", props["appleMusic"])
        self.assertEqual(props["funkwhale"], {
            "access_token": "fw-token",
            "instance_url": "https://funkwhale.example",
            "client_id": "fw-client",
            "client_secret": "fw-secret",
            "token_expiry": self.funkwhale_expiry.isoformat(),
            "refresh_token": "fw-refresh",
            "funkwhale_server_id": self.funkwhale_server_id,
        })
        navidrome = props["navidrome"]
        self.assertEqual((navidrome["instance_url"], navidrome["username"]), ("https://navidrome.example", "nd-user"))
        self.assertEqual(navidrome["md5_auth_token"],
                         hashlib.md5(("navidrome-password" + navidrome["salt"]).encode("utf-8")).hexdigest())
        self.assertEqual(props["user_preferences"], {"brainzplayer": {"spotifyEnabled": True}})
        self.assertEqual(props["flair"], {"name": "wave"})

    def test_props_for_user_without_connections(self):
        props, _ = self._global_props()

        for service in ["spotify", "critiquebrainz", "musicbrainz", "soundcloud", "funkwhale", "navidrome"]:
            self.assertEqual(props[service], {}, service)
        self.assertEqual(set(props["appleMusic"]), {"developer_token"})
        self.assertNotIn("user_preferences", props)
        self.assertNotIn("flair", props)

    def test_one_query_for_a_logged_in_page(self):
        self._connect_every_service()

        _, statements = self._global_props()

        self.assertEqual(len(statements), 1, statements)

    def test_reconnect_alert_for_revoked_spotify(self):
        self._connect_every_service()
        db_listens_importer.update_status(self.db_conn, self.user["id"], ExternalServiceType.SPOTIFY, "Error", 0,
                                          error={"message": "revoked", "retry": False, "reason": "invalid_grant"})

        self._global_props()

        self.assertIn("spotify-reconnect-required", [alert["id"] for alert in self.alerts])
