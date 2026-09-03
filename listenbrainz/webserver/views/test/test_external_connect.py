import re
import time
from unittest.mock import patch
from urllib.parse import urlparse, parse_qs

import spotipy

import listenbrainz.db.user as db_user
from data.model.external_service import ExternalServiceType
from listenbrainz.db import external_service_oauth as db_oauth
from listenbrainz.domain import external_connect
from listenbrainz.domain.spotify import SpotifyService, SPOTIFY_IMPORT_PERMISSIONS, SPOTIFY_LISTEN_PERMISSIONS
from listenbrainz.tests.integration import IntegrationTestCase

REDIRECT_URI = "https://fankee.example/listenbrainz/connected"
OTHER_REDIRECT_URI = "https://partner.example/listenbrainz/connected"


class ExternalConnectViewsTestCase(IntegrationTestCase):

    def setUp(self):
        super(ExternalConnectViewsTestCase, self).setUp()
        self.user = db_user.get_or_create(self.db_conn, 1, 'iliekcomputers')
        db_user.agree_to_gdpr(self.db_conn, self.user['musicbrainz_id'])
        with self.app.app_context():
            self.service = SpotifyService()
        # the test client is created once per class, so the session of the previous test
        # would otherwise leak into this one
        with self.client.session_transaction() as session:
            session.clear()

    def introspection_response(self, **kwargs):
        response = {
            "active": True,
            "sub": self.user["musicbrainz_row_id"],
            "username": self.user["musicbrainz_id"],
            # This is the shape returned by the real MetaBrainz introspection endpoint.
            "scope": ["profile", external_connect.CONNECT_SERVICES_SCOPE],
            "expires_at": int(time.time()) + 3600,
            "client_id": "fankee-client-id",
        }
        response.update(kwargs)
        return response

    def post_connect(self, service_name="spotify", token="meba_token", **kwargs):
        """ Make the call a partner application's backend makes to start the flow. """
        body = {"redirect_uri": REDIRECT_URI, "state": "partner-state"}
        body.update(kwargs)
        body = {key: value for key, value in body.items() if value is not None}
        headers = {"Authorization": f"Bearer {token}"} if token else {}
        return self.client.post(
            self.custom_url_for("external_connect.create_connect_session", service_name=service_name),
            json=body, headers=headers
        )

    def post_connect_ok(self, service_name="spotify", **kwargs):
        """ post_connect with a token the introspection endpoint accepts. """
        with patch('listenbrainz.domain.musicbrainz.MusicBrainzService.get_user_info') as mock_introspect:
            mock_introspect.return_value = self.introspection_response()
            return self.post_connect(service_name=service_name, **kwargs)

    def get_ticket(self, service_name="spotify", **kwargs):
        """ Start the flow with a valid access token and return the ticket we handed out. """
        response = self.post_connect_ok(service_name=service_name, **kwargs)
        self.assert200(response)
        return parse_qs(urlparse(response.json["url"]).query)["ticket"][0]

    def ticket_url(self, ticket, service_name="spotify"):
        return self.custom_url_for("external_connect.connect", service_name=service_name, ticket=ticket)

    def open_confirmation(self, ticket, service_name="spotify"):
        """ Open the confirmation page and return it along with the nonce it carries. """
        response = self.client.get(self.ticket_url(ticket, service_name=service_name))
        self.assert200(response)
        nonce = re.search(rb'name="nonce" value="([^"]+)"', response.data)
        return response, nonce.group(1).decode() if nonce else None

    def submit_confirmation(self, ticket, service_name="spotify", action="continue", nonce=None):
        """ Submit the confirmation page the way the user's browser would. """
        if nonce is None:
            _, nonce = self.open_confirmation(ticket, service_name=service_name)
        return self.client.post(
            self.custom_url_for("external_connect.confirm", service_name=service_name),
            data={"ticket": ticket, "nonce": nonce, "action": action}
        )

    def connect(self, service_name="spotify", **kwargs):
        """ Run the whole partner side of the flow up to the redirect to the music service. """
        ticket = self.get_ticket(service_name=service_name, **kwargs)
        return self.submit_confirmation(ticket, service_name=service_name)

    def assert_returned_to_client(self, response, redirect_uri=REDIRECT_URI, **expected):
        """ Assert the user was redirected to the partner app with the given query params. """
        self.assertStatus(response, 302)
        location = urlparse(response.location)
        self.assertEqual(location._replace(query="").geturl(), redirect_uri)
        params = {key: value[0] for key, value in parse_qs(location.query).items()}
        for key, value in expected.items():
            self.assertEqual(params.get(key), value, f"unexpected value of '{key}' in {params}")
        return params

    def test_connect_redirects_to_service(self):
        r = self.connect()

        self.assertStatus(r, 302)
        location = urlparse(r.location)
        self.assertEqual(location.netloc, "accounts.spotify.com")

        params = parse_qs(location.query)
        self.assertEqual(set(params["scope"][0].split()), SPOTIFY_IMPORT_PERMISSIONS)

        with self.client.session_transaction() as session:
            stored = session[external_connect.SESSION_KEY]
            # the flow must not log the user in to ListenBrainz
            self.assertNotIn("_user_id", session)
        self.assertEqual(stored["user_id"], self.user["id"])
        self.assertEqual(stored["redirect_uri"], REDIRECT_URI)
        self.assertEqual(stored["client_state"], "partner-state")
        self.assertEqual(stored["permission"], "import")
        # the state must reach spotify so that the callback can verify it
        self.assertEqual(params["state"][0], stored["oauth_state"])

    def test_connect_requires_a_ticket(self):
        r = self.client.get(self.custom_url_for("external_connect.connect", service_name="spotify",
                                                redirect_uri=REDIRECT_URI))
        self.assert400(r)

    def test_connect_rejects_an_unknown_ticket(self):
        self.assert400(self.client.get(self.ticket_url("not-a-ticket")))

    def test_ticket_is_single_use(self):
        ticket = self.get_ticket()

        r = self.submit_confirmation(ticket)
        self.assertStatus(r, 302)
        self.assertEqual(urlparse(r.location).netloc, "accounts.spotify.com")

        # the ticket is spent by the confirmation, not by merely opening the page
        self.assert400(self.client.get(self.ticket_url(ticket)))

    def test_opening_the_confirmation_page_does_not_spend_the_ticket(self):
        ticket = self.get_ticket()

        self.open_confirmation(ticket)
        self.open_confirmation(ticket)

        r = self.submit_confirmation(ticket)
        self.assertStatus(r, 302)
        self.assertEqual(urlparse(r.location).netloc, "accounts.spotify.com")

    def test_ticket_is_bound_to_its_service(self):
        ticket = self.get_ticket()
        self.assert400(self.client.get(self.ticket_url(ticket, service_name="soundcloud")))

    def test_confirmation_page_names_the_client_the_account_and_the_permission(self):
        response, nonce = self.open_confirmation(self.get_ticket())

        self.assertIsNotNone(nonce)
        page = response.data.decode()
        # no MetaBrainz database is configured in the tests, so the application is named by
        # the host the user will be sent back to
        self.assertIn("fankee.example", page)
        self.assertIn(self.user["musicbrainz_id"], page)
        self.assertIn("read your Spotify listening history", page)
        # the user must not be sent anywhere before they have confirmed
        self.assertNotIn("accounts.spotify.com", page)
        with self.client.session_transaction() as session:
            self.assertNotIn(external_connect.SESSION_KEY, session)

    @patch('listenbrainz.domain.external_connect.db_oauth_client.get_client_name')
    def test_confirmation_page_names_the_registered_application(self, mock_get_client_name):
        """ When the MetaBrainz database is available we can put the name the application
        is registered under next to the host the user is going back to. """
        mock_get_client_name.return_value = "Fankee"
        # the app is created once per class, so put the config back for the next test
        previous = self.app.config["SQLALCHEMY_METABRAINZ_URI"]
        self.addCleanup(self.app.config.__setitem__, "SQLALCHEMY_METABRAINZ_URI", previous)
        self.app.config["SQLALCHEMY_METABRAINZ_URI"] = "postgresql://meb"

        response, _ = self.open_confirmation(self.get_ticket())

        mock_get_client_name.assert_called_once()
        self.assertEqual(mock_get_client_name.call_args.args[1], "fankee-client-id")
        self.assertIn("Fankee (fankee.example)", response.data.decode())

    def test_confirmation_requires_the_nonce_from_the_page(self):
        ticket = self.get_ticket()
        self.open_confirmation(ticket)

        # a partner that posts the form itself never saw the nonce
        self.assert400(self.submit_confirmation(ticket, nonce="not-the-nonce"))
        with self.client.session_transaction() as session:
            self.assertNotIn(external_connect.SESSION_KEY, session)

    def test_confirmation_cannot_be_submitted_without_opening_the_page(self):
        ticket = self.get_ticket()
        r = self.client.post(
            self.custom_url_for("external_connect.confirm", service_name="spotify"),
            data={"ticket": ticket, "nonce": "guessed", "action": "continue"}
        )
        self.assert400(r)

    def test_confirmation_nonce_is_single_use(self):
        ticket = self.get_ticket()
        _, nonce = self.open_confirmation(ticket)

        self.assertStatus(self.submit_confirmation(ticket, nonce=nonce), 302)
        self.assert400(self.submit_confirmation(ticket, nonce=nonce))

    def test_cancelling_the_confirmation_returns_to_the_client(self):
        ticket = self.get_ticket()

        r = self.submit_confirmation(ticket, action="cancel")
        self.assert_returned_to_client(r, status="error", error=external_connect.ERROR_ACCESS_DENIED,
                                       state="partner-state")
        with self.client.session_transaction() as session:
            self.assertNotIn(external_connect.SESSION_KEY, session)
        # cancelling spends the ticket too
        self.assert400(self.client.get(self.ticket_url(ticket)))

    def test_confirmation_page_rejects_a_different_logged_in_user(self):
        other_user = db_user.get_or_create(self.db_conn, 2, 'someone-else')
        db_user.agree_to_gdpr(self.db_conn, other_user['musicbrainz_id'])
        ticket = self.get_ticket()

        self.temporary_login(other_user['login_id'])
        r = self.client.get(self.ticket_url(ticket))
        self.assert_returned_to_client(r, status="error", error=external_connect.ERROR_INVALID_REQUEST)

    def test_connect_uses_requested_permissions(self):
        r = self.connect(permissions="both")

        self.assertStatus(r, 302)
        params = parse_qs(urlparse(r.location).query)
        self.assertIn("streaming", params["scope"][0].split())
        self.assertIn("user-read-recently-played", params["scope"][0].split())

    def test_connect_returns_immediately_if_already_connected(self):
        db_oauth.save_token(self.db_conn, user_id=self.user['id'], service=ExternalServiceType.SPOTIFY,
                            access_token='token', refresh_token='refresh', token_expires_ts=int(time.time()) + 3600,
                            record_listens=True, scopes=list(SPOTIFY_IMPORT_PERMISSIONS))

        r = self.connect()
        self.assert_returned_to_client(r, status="connected", state="partner-state", service="spotify")

        # unless the partner explicitly asks us to authorize again
        r = self.connect(force=True)
        self.assertStatus(r, 302)
        self.assertEqual(urlparse(r.location).netloc, "accounts.spotify.com")

    def test_connect_reauthorizes_if_scopes_are_insufficient(self):
        db_oauth.save_token(self.db_conn, user_id=self.user['id'], service=ExternalServiceType.SPOTIFY,
                            access_token='token', refresh_token='refresh', token_expires_ts=int(time.time()) + 3600,
                            record_listens=True, scopes=list(SPOTIFY_IMPORT_PERMISSIONS))

        r = self.connect(permissions="both")
        self.assertStatus(r, 302)
        self.assertEqual(urlparse(r.location).netloc, "accounts.spotify.com")

    def test_connect_returns_to_the_requested_redirect_uri(self):
        db_oauth.save_token(self.db_conn, user_id=self.user['id'], service=ExternalServiceType.SPOTIFY,
                            access_token='token', refresh_token='refresh', token_expires_ts=int(time.time()) + 3600,
                            record_listens=True, scopes=list(SPOTIFY_IMPORT_PERMISSIONS))

        r = self.connect(redirect_uri=OTHER_REDIRECT_URI)
        self.assert_returned_to_client(r, OTHER_REDIRECT_URI, status="connected")

    def test_connect_replaces_reserved_redirect_uri_parameters(self):
        db_oauth.save_token(self.db_conn, user_id=self.user['id'], service=ExternalServiceType.SPOTIFY,
                            access_token='token', refresh_token='refresh', token_expires_ts=int(time.time()) + 3600,
                            record_listens=True, scopes=list(SPOTIFY_IMPORT_PERMISSIONS))
        redirect_uri = (
            f"{REDIRECT_URI}?keep=this&service=old&status=old&state=old"
            "&error=old&error_description=old"
        )

        r = self.connect(redirect_uri=redirect_uri)

        params = parse_qs(urlparse(r.location).query)
        self.assertEqual(params, {
            "keep": ["this"],
            "service": ["spotify"],
            "status": ["connected"],
            "state": ["partner-state"],
        })

    def test_connect_requires_redirect_uri(self):
        self.assert400(self.post_connect(redirect_uri=None))

    def test_connect_rejects_a_redirect_uri_that_is_not_an_https_url(self):
        """ There is no allow list to match against, so all we can do is make sure the
        browser can actually be redirected there. http is only allowed for local
        development. """
        for redirect_uri in ["javascript:alert(1)", "data:text/html,x", "/listenbrainz/connected",
                             "https:///connected", "http://partner.example/connected"]:
            with self.subTest(redirect_uri=redirect_uri):
                self.assert400(self.post_connect(redirect_uri=redirect_uri))

        self.assert200(self.post_connect_ok(redirect_uri="http://localhost:3000/connected"))

    def test_connect_only_supports_spotify(self):
        """ Spotify is the only service offered through this flow for now. Soundcloud and
        critiquebrainz can be connected from the settings page but not from here. """
        for service_name in ["soundcloud", "critiquebrainz", "funkwhale", "apple"]:
            with self.subTest(service=service_name):
                self.assert400(self.post_connect(service_name=service_name))

    def test_connect_rejects_invalid_permissions(self):
        self.assert400(self.post_connect(permissions="everything"))

    def test_connect_rejects_overlong_state(self):
        self.assert400(self.post_connect(state="x" * (external_connect.MAX_CLIENT_STATE_LENGTH + 1)))

    def test_connect_rejects_values_that_are_not_strings(self):
        """ The body is json, so a partner can put anything in it. """
        for key, value in [("redirect_uri", [REDIRECT_URI]),
                           ("state", 123), ("permissions", ["import"])]:
            with self.subTest(key=key):
                self.assert400(self.post_connect(**{key: value}))

    def test_connect_rejects_a_ticket_for_a_different_logged_in_user(self):
        other_user = db_user.get_or_create(self.db_conn, 2, 'someone-else')
        db_user.agree_to_gdpr(self.db_conn, other_user['musicbrainz_id'])
        ticket = self.get_ticket()

        self.temporary_login(other_user['login_id'])
        r = self.client.get(self.ticket_url(ticket))
        self.assert_returned_to_client(r, status="error", error=external_connect.ERROR_INVALID_REQUEST)
        with self.client.session_transaction() as session:
            self.assertNotIn(external_connect.SESSION_KEY, session)

    @patch('listenbrainz.domain.musicbrainz.MusicBrainzService.get_user_info')
    def test_connect_validates_the_request_before_introspecting_the_token(self, mock_introspect):
        self.assert400(self.post_connect(redirect_uri="javascript:alert(1)"))
        mock_introspect.assert_not_called()

    @patch('listenbrainz.domain.spotify.SpotifyService.fetch_access_token')
    @patch.object(spotipy.Spotify, 'current_user')
    def test_callback_returns_to_client(self, mock_current_user, mock_fetch_access_token):
        mock_current_user.return_value = {"id": "test-id"}
        mock_fetch_access_token.return_value = {
            'access_token': 'token',
            'refresh_token': 'refresh',
            'expires_in': 3600,
            'scope': ' '.join(SPOTIFY_IMPORT_PERMISSIONS),
        }
        self.connect()
        with self.client.session_transaction() as session:
            oauth_state = session[external_connect.SESSION_KEY]["oauth_state"]

        r = self.client.get(self.custom_url_for(
            'settings.music_services_callback', service_name='spotify', code='code', state=oauth_state
        ))
        self.assert_returned_to_client(r, status="connected", service="spotify", state="partner-state")

        # the tokens are stored for the owner of the access token the partner sent us
        with self.app.app_context():
            user = self.service.get_user(self.user['id'])
        self.assertEqual(self.user['id'], user['user_id'])
        self.assertEqual('token', user['access_token'])

        # the request is single use, a second callback goes to the settings page instead
        with self.client.session_transaction() as session:
            self.assertNotIn(external_connect.SESSION_KEY, session)
            self.assertNotIn("_user_id", session)

    @patch('listenbrainz.domain.spotify.SpotifyService.fetch_access_token')
    @patch.object(spotipy.Spotify, 'current_user')
    def test_callback_replaces_the_old_connection_after_token_exchange(self, mock_current_user,
                                                                        mock_fetch_access_token):
        """ Narrowing the permissions must not leave the listens importer behind. """
        db_oauth.save_token(self.db_conn, user_id=self.user['id'], service=ExternalServiceType.SPOTIFY,
                            access_token='old', refresh_token='refresh', token_expires_ts=int(time.time()) + 3600,
                            record_listens=True, scopes=list(SPOTIFY_IMPORT_PERMISSIONS))
        mock_current_user.return_value = {"id": "test-id"}
        mock_fetch_access_token.return_value = {
            'access_token': 'token', 'refresh_token': 'refresh', 'expires_in': 3600,
            'scope': ' '.join(SPOTIFY_LISTEN_PERMISSIONS),
        }

        self.connect(permissions="listen", force=True)
        with self.client.session_transaction() as session:
            oauth_state = session[external_connect.SESSION_KEY]["oauth_state"]
        r = self.client.get(self.custom_url_for(
            'settings.music_services_callback', service_name='spotify', code='code', state=oauth_state
        ))
        self.assert_returned_to_client(r, status="connected")

        with self.app.app_context():
            self.assertEqual('token', self.service.get_user(self.user['id'])['access_token'])
            self.assertIsNone(self.service.get_user_connection_details(self.user['id']))

    def test_callback_returns_error_to_client_when_denied(self):
        db_oauth.save_token(self.db_conn, user_id=self.user['id'], service=ExternalServiceType.SPOTIFY,
                            access_token='old', refresh_token='refresh', token_expires_ts=int(time.time()) + 3600,
                            record_listens=True, scopes=list(SPOTIFY_IMPORT_PERMISSIONS))
        self.connect(force=True)
        with self.client.session_transaction() as session:
            oauth_state = session[external_connect.SESSION_KEY]["oauth_state"]

        r = self.client.get(self.custom_url_for(
            'settings.music_services_callback', service_name='spotify', error='access_denied', state=oauth_state
        ))
        self.assert_returned_to_client(r, status="error", error=external_connect.ERROR_ACCESS_DENIED,
                                       state="partner-state")
        with self.app.app_context():
            self.assertEqual('old', self.service.get_user(self.user['id'])['access_token'])
            self.assertIsNotNone(self.service.get_user_connection_details(self.user['id']))

    def test_callback_does_not_report_a_service_side_error_as_a_denial(self):
        self.connect()
        with self.client.session_transaction() as session:
            oauth_state = session[external_connect.SESSION_KEY]["oauth_state"]

        r = self.client.get(self.custom_url_for(
            'settings.music_services_callback', service_name='spotify', error='invalid_scope', state=oauth_state
        ))
        self.assert_returned_to_client(r, status="error", error=external_connect.ERROR_SERVER_ERROR)

    def test_callback_error_with_invalid_state_does_not_cancel_pending_request(self):
        self.connect()

        r = self.client.get(self.custom_url_for(
            'settings.music_services_callback', service_name='spotify',
            error='access_denied', state='not-the-state'
        ))

        self.assert_returned_to_client(r, status="error", error=external_connect.ERROR_INVALID_REQUEST)
        with self.client.session_transaction() as session:
            self.assertIn(external_connect.SESSION_KEY, session)

    def test_callback_error_does_not_clear_the_pending_oauth_state(self):
        """ Otherwise it could be used to strip the state off an authorization in flight. """
        self.temporary_login(self.user['login_id'])
        self.client.post(self.custom_url_for('settings.music_services_disconnect', service_name='spotify'),
                         json={"action": "import"})
        with self.client.session_transaction() as session:
            state = session[external_connect.settings_oauth_state_key("spotify")]

        self.client.get(self.custom_url_for(
            'settings.music_services_callback', service_name='spotify', error='access_denied'
        ))
        with self.client.session_transaction() as session:
            self.assertEqual(session[external_connect.settings_oauth_state_key("spotify")], state)

    @patch('listenbrainz.domain.spotify.SpotifyService.fetch_access_token')
    def test_callback_without_a_pending_state_is_rejected(self, mock_fetch_access_token):
        """ A code we never asked for must not be exchanged, it could belong to anyone. """
        self.temporary_login(self.user['login_id'])

        r = self.client.get(self.custom_url_for(
            'settings.music_services_callback', service_name='spotify', code='attacker-code'
        ))
        self.assertStatus(r, 302)
        self.assertNotIn("accounts.spotify.com", r.location)
        mock_fetch_access_token.assert_not_called()
        with self.app.app_context():
            self.assertIsNone(self.service.get_user(self.user['id']))

    def test_authorizations_of_two_services_do_not_clobber_each_other(self):
        self.temporary_login(self.user['login_id'])
        self.client.post(self.custom_url_for('settings.music_services_disconnect', service_name='spotify'),
                         json={"action": "import"})
        self.client.post(self.custom_url_for('settings.music_services_disconnect', service_name='critiquebrainz'),
                         json={"action": "review"})

        with self.client.session_transaction() as session:
            self.assertIn(external_connect.settings_oauth_state_key("spotify"), session)
            self.assertNotEqual(session[external_connect.settings_oauth_state_key("spotify")],
                                session[external_connect.settings_oauth_state_key("critiquebrainz")])

    @patch('listenbrainz.domain.spotify.SpotifyService.fetch_access_token')
    def test_callback_rejects_mismatched_state(self, mock_fetch_access_token):
        self.connect()

        r = self.client.get(self.custom_url_for(
            'settings.music_services_callback', service_name='spotify', code='code', state='not-the-state'
        ))
        self.assert_returned_to_client(r, status="error", error=external_connect.ERROR_INVALID_REQUEST)
        mock_fetch_access_token.assert_not_called()
        with self.client.session_transaction() as session:
            self.assertIn(external_connect.SESSION_KEY, session)

    @patch('listenbrainz.domain.spotify.SpotifyService.fetch_access_token')
    def test_callback_returns_error_to_client_on_token_exchange_failure(self, mock_fetch_access_token):
        db_oauth.save_token(self.db_conn, user_id=self.user['id'], service=ExternalServiceType.SPOTIFY,
                            access_token='old', refresh_token='refresh', token_expires_ts=int(time.time()) + 3600,
                            record_listens=True, scopes=list(SPOTIFY_IMPORT_PERMISSIONS))
        mock_fetch_access_token.side_effect = Exception("boom")
        self.connect(permissions="listen", force=True)
        # Merely starting a replacement authorization must leave the working connection in
        # place in case the user abandons the flow.
        with self.app.app_context():
            self.assertEqual('old', self.service.get_user(self.user['id'])['access_token'])
            self.assertIsNotNone(self.service.get_user_connection_details(self.user['id']))
        with self.client.session_transaction() as session:
            oauth_state = session[external_connect.SESSION_KEY]["oauth_state"]

        r = self.client.get(self.custom_url_for(
            'settings.music_services_callback', service_name='spotify', code='code', state=oauth_state
        ))
        self.assert_returned_to_client(r, status="error", error=external_connect.ERROR_SERVER_ERROR)
        with self.app.app_context():
            self.assertEqual('old', self.service.get_user(self.user['id'])['access_token'])
            self.assertIsNotNone(self.service.get_user_connection_details(self.user['id']))

    def test_callback_rejects_a_different_logged_in_user(self):
        other_user = db_user.get_or_create(self.db_conn, 2, 'someone-else')
        db_user.agree_to_gdpr(self.db_conn, other_user['musicbrainz_id'])

        self.connect()
        with self.client.session_transaction() as session:
            oauth_state = session[external_connect.SESSION_KEY]["oauth_state"]

        self.temporary_login(other_user['login_id'])
        r = self.client.get(self.custom_url_for(
            'settings.music_services_callback', service_name='spotify', code='code', state=oauth_state
        ))
        self.assert_returned_to_client(r, status="error", error=external_connect.ERROR_INVALID_REQUEST)
        with self.app.app_context():
            self.assertIsNone(self.service.get_user(self.user['id']))
            self.assertIsNone(self.service.get_user(other_user['id']))

    def test_callback_requires_login_without_a_pending_request(self):
        r = self.client.get(self.custom_url_for(
            'settings.music_services_callback', service_name='spotify', code='code'
        ))
        self.assertStatus(r, 302)
        self.assertIn("/login/musicbrainz/", r.location)

    def test_callback_for_another_service_is_not_returned_to_client(self):
        """ A pending request for spotify must not hijack a soundcloud callback. """
        self.connect()
        self.temporary_login(self.user['login_id'])

        r = self.client.get(self.custom_url_for(
            'settings.music_services_callback', service_name='soundcloud', error='access_denied'
        ))
        self.assertStatus(r, 302)
        self.assertNotIn("fankee.example", r.location)
        with self.client.session_transaction() as session:
            self.assertIn(external_connect.SESSION_KEY, session)

    def test_token_flow_returns_single_use_url(self):
        with patch('listenbrainz.domain.musicbrainz.MusicBrainzService.get_user_info') as mock_introspect:
            mock_introspect.return_value = self.introspection_response()
            r = self.post_connect()
            mock_introspect.assert_called_once_with("meba_token")

        self.assert200(r)
        self.assertEqual(r.json["expires_in"], int(external_connect.TICKET_TTL.total_seconds()))
        self.assertIn("/connect/spotify/", r.json["url"])

    def test_token_flow_requires_authorization_header(self):
        self.assert401(self.post_connect(token=None))

    @patch('listenbrainz.domain.musicbrainz.MusicBrainzService.get_user_info')
    def test_token_flow_rejects_listenbrainz_user_token(self, mock_introspect):
        r = self.post_connect(token=self.user["auth_token"])
        self.assert401(r)
        mock_introspect.assert_not_called()

    @patch('listenbrainz.domain.musicbrainz.MusicBrainzService.get_user_info')
    def test_token_flow_requires_connect_services_scope(self, mock_introspect):
        for scope in [["profile", "email"], "profile email", [], None]:
            with self.subTest(scope=scope):
                mock_introspect.return_value = self.introspection_response(scope=scope)
                r = self.post_connect()
                self.assert401(r)
                self.assertIn(external_connect.CONNECT_SERVICES_SCOPE, r.json["error"])

    @patch('listenbrainz.domain.musicbrainz.MusicBrainzService.get_user_info')
    def test_token_flow_accepts_space_delimited_scope_for_compatibility(self, mock_introspect):
        mock_introspect.return_value = self.introspection_response(
            scope=f"profile {external_connect.CONNECT_SERVICES_SCOPE}"
        )
        self.assert200(self.post_connect())

    @patch('listenbrainz.domain.musicbrainz.MusicBrainzService.get_user_info')
    def test_token_flow_rejects_inactive_token(self, mock_introspect):
        mock_introspect.return_value = self.introspection_response(active=False)
        self.assert401(self.post_connect())

    @patch('listenbrainz.domain.musicbrainz.MusicBrainzService.get_user_info')
    def test_token_flow_rejects_expired_token(self, mock_introspect):
        mock_introspect.return_value = self.introspection_response(expires_at=int(time.time()) - 10)
        self.assert401(self.post_connect())

    @patch('listenbrainz.domain.musicbrainz.MusicBrainzService.get_user_info')
    def test_token_flow_rejects_user_without_listenbrainz_account(self, mock_introspect):
        mock_introspect.return_value = self.introspection_response(sub=99999, username="nosuchuser")
        self.assert401(self.post_connect())

    @patch('listenbrainz.domain.musicbrainz.MusicBrainzService.get_user_info')
    def test_token_flow_rejects_a_client_credentials_token(self, mock_introspect):
        """ A client credentials grant has no user behind it, MetaBrainz reports it as the
        sentinel subject -1. There is nobody to connect a music service for. """
        mock_introspect.return_value = self.introspection_response(sub="-1", username=None)
        self.assert401(self.post_connect())

    @patch('listenbrainz.domain.musicbrainz.MusicBrainzService.get_user_info')
    def test_token_flow_needs_no_credentials_beyond_the_token(self, mock_introspect):
        """ The scope is only granted to applications MetaBrainz approved, so the token is
        the whole of the authorization. ListenBrainz keeps no client registry. """
        mock_introspect.return_value = self.introspection_response()
        self.assert200(self.post_connect(client_id="anything", client_secret="anything"))
