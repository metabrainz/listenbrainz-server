from dataclasses import asdict
from unittest import TestCase
from unittest.mock import patch

from flask import Flask

from listenbrainz.domain import external_connect
from listenbrainz.webserver.views.external_connect import external_connect_bp


class ExternalConnectRecoveryTestCase(TestCase):
    """Exercise browser recovery without database or OAuth service dependencies."""

    def setUp(self):
        self.app = Flask("listenbrainz.webserver")
        self.app.config.update(TESTING=True, SECRET_KEY="test-secret")
        self.app.jinja_env.globals["get_static_path"] = lambda name: "/static/" + name
        self.app.register_blueprint(external_connect_bp, url_prefix="/connect")
        self.client = self.app.test_client()
        self.connect_request = external_connect.ExternalConnectRequest(
            redirect_uri="https://partner.example/return", service="spotify",
            permission="import", oauth_state="oauth-state", client_state="partner-state",
        )

    def assert_recovery_page(self, response):
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.mimetype, "text/html")
        self.assertIn(b"This connect link is no longer available", response.data)
        self.assertIn(b"request a new connect link", response.data)
        self.assertIn(b"Go back", response.data)
        self.assertNotIn("Location", response.headers)

    def test_missing_or_expired_ticket_get_always_returns_html(self):
        with patch.object(external_connect.cache, "get", return_value=None):
            for ticket in (None, "expired-ticket"):
                for accept in ("text/html", "text/html,*/*", "application/json"):
                    with self.subTest(ticket=ticket, accept=accept):
                        response = self.client.get(
                            "/connect/spotify/", query_string={"ticket": ticket} if ticket else {},
                            headers={"Accept": accept},
                        )
                        self.assert_recovery_page(response)

    def test_missing_confirmation_and_expired_ticket_returns_html(self):
        with patch.object(external_connect.cache, "get", return_value=None):
            response = self.client.post(
                "/connect/spotify/confirm/", data={"ticket": "expired-ticket", "nonce": "old"},
                headers={"Accept": "application/json"},
            )
        self.assert_recovery_page(response)

    def test_ticket_consumed_by_another_request_returns_html(self):
        with self.client.session_transaction() as session:
            session[external_connect.CONFIRM_SESSION_KEY] = {"ticket": "ticket", "nonce": "nonce"}
        with patch.object(external_connect.cache, "get", return_value=asdict(self.connect_request)), \
                patch.object(external_connect.cache, "delete", return_value=0):
            response = self.client.post(
                "/connect/spotify/confirm/",
                data={"ticket": "ticket", "nonce": "nonce", "action": "continue"},
                headers={"Accept": "application/json"},
            )
        self.assert_recovery_page(response)

    def test_recovery_does_not_use_untrusted_destinations_or_clear_pending_oauth(self):
        with self.client.session_transaction() as session:
            session[external_connect.SESSION_KEY] = asdict(self.connect_request)
        with patch.object(external_connect.cache, "get", return_value=None):
            response = self.client.get(
                "/connect/spotify/?ticket=unknown&redirect_uri=https://untrusted.example/",
                headers={"Referer": "https://untrusted.example/"},
            )
        self.assert_recovery_page(response)
        self.assertNotIn(b"untrusted.example", response.data)
        self.assertNotIn(b"partner.example", response.data)
        with self.client.session_transaction() as session:
            self.assertEqual(session[external_connect.SESSION_KEY], asdict(self.connect_request))

    def test_valid_ticket_still_recovers_via_confirmation(self):
        with patch.object(external_connect.cache, "get", return_value=asdict(self.connect_request)):
            response = self.client.post(
                "/connect/spotify/confirm/", data={"ticket": "ticket", "nonce": "old"},
            )
        self.assertEqual(response.status_code, 303)
        self.assertEqual(response.location, "/connect/spotify/?ticket=ticket&retry=1")
