import requests_mock
from brainzutils.musicbrainz_db import mb_session
from flask import url_for
from mbdata.models import Editor
from sqlalchemy import text

from listenbrainz.db import timescale
from listenbrainz.tests.integration import IntegrationTestCase
import listenbrainz.db.user as db_user

from urllib.parse import urlparse
from urllib.parse import parse_qs


class OAuthLoginTestCase(IntegrationTestCase):

    def setUp(self):
        IntegrationTestCase.setUp()
        self.editor = Editor(id=5746, name="lucifer", email="example@metabrainz.org", password="password", ha1="ha1")
        with mb_session() as db:
            db.add(self.editor)
            db.commit()

    @requests_mock.Mocker()
    def test_login(self, mock_requests):
        mock_requests.post("https://musicbrainz.org/oauth2/token", status_code=200, json={
            "access_token": "access-token",
            "expires_in": 3600,
            "refresh_token": "refresh-token",
            "token_type": "Bearer"
        })
        mock_requests.get("https://musicbrainz.org/oauth2/userinfo", status_code=200, json={
            "sub": "lucifer",
            "metabrainz_user_id": 5746
        })

        r = self.client.get(url_for("login.musicbrainz"))
        url = urlparse(r.headers["Location"])
        params = parse_qs(url.query)

        r = self.client.get(url_for("login.musicbrainz_post", code="foobar", state=params["state"][0]))
        user = db_user.get_by_mb_id("lucifer", fetch_email=True)
        self.assertEqual(user["musicbrainz_row_id"], 5746)
        self.assertEqual(user["email"], "example@metabrainz.org")

        with timescale.engine.connect() as ts_conn:
            ts_conn.execute(text("SELECT * listen_user_metadata WHERE user_id = :user_id"), user_id=user["id"])
            row = ts_conn.fetchone()
            self.assertEqual(row["count"], 0)
            self.assertEqual(row["min_listened_at"], None)
            self.assertEqual(row["max_listened_at"], None)

    def tearDown(self):
        IntegrationTestCase.tearDown()
        with mb_session() as db:
            db.delete(self.editor)
            db.commit()
