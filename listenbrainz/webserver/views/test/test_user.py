import logging
import time
from unittest import mock

import ujson
from flask import url_for

import listenbrainz.db.user as db_user
from data.model.external_service import ExternalServiceType

from listenbrainz.db import external_service_oauth as db_oauth
from listenbrainz.listenstore.tests.util import create_test_data_for_timescalelistenstore
from listenbrainz.tests.integration import IntegrationTestCase
from listenbrainz.webserver import timescale_connection
from listenbrainz.webserver.login import User


class UserViewsTestCase(IntegrationTestCase):
    def setUp(self):
        super(UserViewsTestCase, self).setUp()

        self.log = logging.getLogger(__name__)
        self.logstore = timescale_connection._ts

        user = db_user.get_or_create(1, 'iliekcomputers')
        db_user.agree_to_gdpr(user['musicbrainz_id'])
        self.user = User.from_dbrow(user)

        weirduser = db_user.get_or_create(2, 'weird\\user name')
        self.weirduser = User.from_dbrow(weirduser)

        abuser = db_user.get_or_create(3, 'abuser')
        self.abuser = User.from_dbrow(abuser)

    def tearDown(self):
        self.logstore = None

    def test_redirects(self):
        """Test the /my/[something]/ endponts which redirect to the /user/ namespace"""
        # Not logged in
        response = self.client.get(url_for("redirect.redirect_listens"))
        self.assertRedirects(response, "/login/?next=%2Fmy%2Flistens%2F")

        # Logged in
        self.temporary_login(self.user.login_id)
        response = self.client.get(url_for("redirect.redirect_listens"))
        self.assertRedirects(response, "/user/iliekcomputers/")

        response = self.client.get(url_for("redirect.redirect_charts"))
        self.assertRedirects(response, "/user/iliekcomputers/charts/")

        response = self.client.get(url_for("redirect.redirect_charts") + "?foo=bar")
        self.assertRedirects(response, "/user/iliekcomputers/charts/?foo=bar")

    def test_user_redirects(self):
        response = self.client.get('/user/iliekcomputers/')
        self.assert200(response)
        response = self.client.get('/user/iliekcomputers')
        self.assertRedirects(response, '/user/iliekcomputers/', permanent=True)

        response = self.client.get('/user/iliekcomputers/charts/')
        self.assert200(response)
        response = self.client.get('/user/iliekcomputers/charts')
        self.assertRedirects(response, '/user/iliekcomputers/charts/', permanent=True)

        response = self.client.get('/user/iliekcomputers/reports/')
        self.assert200(response)
        response = self.client.get('/user/iliekcomputers/reports')
        self.assertRedirects(response, '/user/iliekcomputers/reports/', permanent=True)

        # these are permanent redirects to user/<username>/charts

        response = self.client.get('/user/iliekcomputers/history/')
        self.assertRedirects(
            response,
            '/user/iliekcomputers/charts/?entity=artist&page=1&range=all_time',
            permanent=True
        )
        response = self.client.get('/user/iliekcomputers/history')
        self.assertRedirects(response, '/user/iliekcomputers/history/', permanent=True)

        response = self.client.get('/user/iliekcomputers/artists/')
        self.assertRedirects(
            response,
            '/user/iliekcomputers/charts/?entity=artist&page=1&range=all_time',
            permanent=True
        )
        response = self.client.get('/user/iliekcomputers/artists')
        self.assertRedirects(response, '/user/iliekcomputers/artists/', permanent=True)

    def test_user_page(self):
        response = self.client.get(url_for('user.profile', user_name=self.user.musicbrainz_id))
        self.assert200(response)
        self.assertContext('active_section', 'listens')

    def test_spotify_token_access_no_login(self):
        db_oauth.save_token(user_id=self.user.id, service=ExternalServiceType.SPOTIFY,
                            access_token='token', refresh_token='refresh',
                            token_expires_ts=int(time.time()) + 1000, record_listens=True,
                            scopes=['user-read-recently-played', 'streaming'])

        response = self.client.get(url_for('user.profile', user_name=self.user.musicbrainz_id))
        self.assert200(response)
        self.assertTemplateUsed('user/profile.html')
        props = ujson.loads(self.get_context_variable("global_props"))
        self.assertDictEqual(props['spotify'], {})

    def test_spotify_token_access_unlinked(self):
        self.temporary_login(self.user.login_id)
        response = self.client.get(url_for('user.profile', user_name=self.user.musicbrainz_id))
        self.assert200(response)
        props = ujson.loads(self.get_context_variable("global_props"))
        self.assertDictEqual(props['spotify'], {})

    def test_spotify_token_access(self):
        db_oauth.save_token(user_id=self.user.id, service=ExternalServiceType.SPOTIFY,
                            access_token='token', refresh_token='refresh',
                            token_expires_ts=int(time.time()) + 1000, record_listens=True,
                            scopes=['user-read-recently-played', 'streaming'])

        self.temporary_login(self.user.login_id)

        response = self.client.get(url_for('user.profile', user_name=self.user.musicbrainz_id))
        self.assert200(response)

        props = ujson.loads(self.get_context_variable("global_props"))
        self.assertDictEqual(props['spotify'], {
            'access_token': 'token',
            'permission': ['user-read-recently-played', 'streaming'],
        })

        response = self.client.get(url_for('user.profile', user_name=self.weirduser.musicbrainz_id))
        self.assert200(response)
        props = ujson.loads(self.get_context_variable("global_props"))
        self.assertDictEqual(props['spotify'], {
            'access_token': 'token',
            'permission': ['user-read-recently-played', 'streaming'],
        })

    @mock.patch('listenbrainz.webserver.views.user.db_user_relationship.is_following_user')
    def test_logged_in_user_follows_user_props(self, mock_is_following_user):
        response = self.client.get(url_for('user.profile', user_name=self.user.musicbrainz_id))
        self.assert200(response)
        self.assertTemplateUsed('user/profile.html')
        props = ujson.loads(self.get_context_variable('props'))
        self.assertIsNone(props['logged_in_user_follows_user'])

        self.temporary_login(self.user.login_id)
        mock_is_following_user.return_value = False
        response = self.client.get(url_for('user.profile', user_name=self.user.musicbrainz_id))
        self.assert200(response)
        props = ujson.loads(self.get_context_variable('props'))
        self.assertFalse(props['logged_in_user_follows_user'])

    def _create_test_data(self, user_name):
        min_ts = -1
        max_ts = -1
        self.test_data = create_test_data_for_timescalelistenstore(user_name, 1)
        for listen in self.test_data:
            if min_ts < 0 or listen.ts_since_epoch < min_ts:
                min_ts = listen.ts_since_epoch
            if max_ts < 0 or listen.ts_since_epoch > max_ts:
                max_ts = listen.ts_since_epoch

        self.logstore.insert(self.test_data)
        return (min_ts, max_ts)

    def test_username_case(self):
        """Tests that the username in URL is case insensitive"""
        self._create_test_data('iliekcomputers')

        response1 = self.client.get(url_for('user.profile', user_name='iliekcomputers'))
        self.assertContext('user', self.user)
        response2 = self.client.get(url_for('user.profile', user_name='IlieKcomPUteRs'))
        self.assertContext('user', self.user)
        self.assert200(response1)
        self.assert200(response2)

    @mock.patch('listenbrainz.webserver.timescale_connection._ts.fetch_listens')
    def test_ts_filters(self, timescale):
        """Check that max_ts and min_ts are passed to timescale """
        user = User.from_dbrow(db_user.get(1)).to_dict()
        timescale.return_value = ([], 0, 0)

        # If no parameter is given, use current time as the to_ts
        self.client.get(url_for('user.profile', user_name='iliekcomputers'))
        req_call = mock.call(user, limit=25, from_ts=None)
        timescale.assert_has_calls([req_call])
        timescale.reset_mock()

        # max_ts query param -> to_ts timescale param
        self.client.get(url_for('user.profile', user_name='iliekcomputers'), query_string={'max_ts': 1520946000})
        req_call = mock.call(user, limit=25, to_ts=1520946000)
        timescale.assert_has_calls([req_call])
        timescale.reset_mock()

        # min_ts query param -> from_ts timescale param
        self.client.get(url_for('user.profile', user_name='iliekcomputers'), query_string={'min_ts': 1520941000})
        req_call = mock.call(user, limit=25, from_ts=1520941000)
        timescale.assert_has_calls([req_call])
        timescale.reset_mock()

        # If max_ts and min_ts set, only max_ts is used
        self.client.get(url_for('user.profile', user_name='iliekcomputers'),
                        query_string={'min_ts': 1520941000, 'max_ts': 1520946000})
        req_call = mock.call(user, limit=25, to_ts=1520946000)
        timescale.assert_has_calls([req_call])

    @mock.patch('listenbrainz.webserver.timescale_connection._ts.fetch_listens')
    def test_ts_filters_errors(self, timescale):
        """If max_ts and min_ts are not integers, show an error page"""
        (min_ts, max_ts) = self._create_test_data('iliekcomputers')

        response = self.client.get(url_for('user.profile', user_name='iliekcomputers'),
                                   query_string={'max_ts': 'a'})
        self.assert400(response)
        self.assertIn(b'Incorrect timestamp argument max_ts: a', response.data)

        response = self.client.get(url_for('user.profile', user_name='iliekcomputers'),
                                   query_string={'min_ts': 'b'})
        self.assert400(response)
        self.assertIn(b'Incorrect timestamp argument min_ts: b', response.data)

        timescale.assert_not_called()

    def test_report_abuse(self):
        # Assert user is not already reported by current user
        already_reported_user = db_user.is_user_reported(self.user.id, self.abuser.id)
        self.assertFalse(already_reported_user)

        self.temporary_login(self.user.login_id)
        # Assert reporting works
        data = {
            'reason': 'This user is cramping my style and I dont like it'
        }
        response = self.client.post(
            url_for('user.report_abuse', user_name=self.abuser.musicbrainz_id),
            json=data,
        )
        self.assert200(response, "%s has been reported successfully." % self.abuser.musicbrainz_id)
        already_reported_user = db_user.is_user_reported(self.user.id, self.abuser.id)
        self.assertTrue(already_reported_user)

        # Assert a user cannot report themselves
        response = self.client.post(
            url_for('user.report_abuse', user_name=self.user.musicbrainz_id),
            json=data,
        )
        self.assert400(response, "You cannot report yourself.")
        already_reported_user = db_user.is_user_reported(self.user.id, self.user.id)
        self.assertFalse(already_reported_user)

        # Assert reason must be of type string
        data = {
            'reason': {'youDoneGoofed': 1234}
        }
        response = self.client.post(
            url_for('user.report_abuse', user_name=self.abuser.musicbrainz_id),
            json=data,
        )
        self.assert400(response, "Reason must be a string.")
