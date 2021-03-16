import listenbrainz.db.stats as db_stats
import listenbrainz.db.user as db_user
import listenbrainz.db.user_relationship as db_user_relationship
from time import sleep
import json
import ujson
from unittest import mock

from flask import url_for, current_app
from data.model.user_artist_stat import UserArtistStatJson

from listenbrainz.db.testing import DatabaseTestCase
from listenbrainz.listenstore.tests.util import create_test_data_for_timescalelistenstore
from listenbrainz.webserver.timescale_connection import init_timescale_connection
from listenbrainz.webserver.login import User
from listenbrainz.webserver.testing import ServerTestCase

import listenbrainz.db.user as db_user
import logging


class UserViewsTestCase(ServerTestCase, DatabaseTestCase):
    def setUp(self):
        ServerTestCase.setUp(self)
        DatabaseTestCase.setUp(self)

        self.log = logging.getLogger(__name__)
        self.logstore = init_timescale_connection(self.log, {
            'REDIS_HOST': current_app.config['REDIS_HOST'],
            'REDIS_PORT': current_app.config['REDIS_PORT'],
            'REDIS_NAMESPACE': current_app.config['REDIS_NAMESPACE'],
            'SQLALCHEMY_TIMESCALE_URI': self.app.config['SQLALCHEMY_TIMESCALE_URI']
        })

        user = db_user.get_or_create(1, 'iliekcomputers')
        db_user.agree_to_gdpr(user['musicbrainz_id'])
        self.user = User.from_dbrow(user)

        weirduser = db_user.get_or_create(2, 'weird\\user name')
        self.weirduser = User.from_dbrow(weirduser)

    def tearDown(self):
        self.logstore = None
        ServerTestCase.tearDown(self)
        DatabaseTestCase.tearDown(self)

    def test_redirects(self):
        # Not logged in
        response = self.client.get(url_for("redirect.redirect_listens"))
        self.assertEqual(response.status_code, 302)
        assert response.location.endswith("/login/?next=%2Fmy%2Flistens")

        self.temporary_login(self.user.login_id)
        response = self.client.get(url_for("redirect.redirect_listens"))
        self.assertEqual(response.status_code, 302)
        assert response.location.endswith("/user/iliekcomputers")

        response = self.client.get(url_for("redirect.redirect_charts"))
        self.assertEqual(response.status_code, 302)
        assert response.location.endswith("/user/iliekcomputers/charts")

        response = self.client.get(url_for("redirect.redirect_charts") + "?foo=bar")
        self.assertEqual(response.status_code, 302)
        assert response.location.endswith("/user/iliekcomputers/charts?foo=bar")

    def test_user_page(self):
        response = self.client.get(url_for('user.profile', user_name=self.user.musicbrainz_id))
        self.assert200(response)
        self.assertContext('active_section', 'listens')

        # check that artist count is not shown if stats haven't been calculated yet
        response = self.client.get(url_for('user.profile', user_name=self.user.musicbrainz_id))
        self.assert200(response)
        self.assertTemplateUsed('user/profile.html')
        props = ujson.loads(self.get_context_variable('props'))
        self.assertIsNone(props['artist_count'])

        with open(self.path_to_data_file('user_top_artists_db.json')) as f:
            artists_data = ujson.load(f)

        db_stats.insert_user_artists(
            user_id=self.user.id,
            artists=UserArtistStatJson(**{'all_time': artists_data})
        )
        response = self.client.get(url_for('user.profile', user_name=self.user.musicbrainz_id))
        self.assert200(response)
        self.assertTemplateUsed('user/profile.html')
        props = ujson.loads(self.get_context_variable('props'))
        self.assertEqual(props['artist_count'], '2')
        self.assertDictEqual(props['spotify'], {})

    @mock.patch('listenbrainz.webserver.views.user.spotify')
    def test_spotify_token_access(self, mock_domain_spotify):
        response = self.client.get(url_for('user.profile', user_name=self.user.musicbrainz_id))
        self.assert200(response)
        self.assertTemplateUsed('user/profile.html')
        props = ujson.loads(self.get_context_variable('props'))
        self.assertDictEqual(props['spotify'], {})

        self.temporary_login(self.user.login_id)
        mock_domain_spotify.get_user_dict.return_value = {}
        response = self.client.get(url_for('user.profile', user_name=self.user.musicbrainz_id))
        self.assert200(response)
        props = ujson.loads(self.get_context_variable('props'))
        self.assertDictEqual(props['spotify'], {})

        mock_domain_spotify.get_user_dict.return_value = {
            'access_token': 'token',
            'permission': 'permission',
        }
        response = self.client.get(url_for('user.profile', user_name=self.user.musicbrainz_id))
        self.assert200(response)
        props = ujson.loads(self.get_context_variable('props'))
        mock_domain_spotify.get_user_dict.assert_called_with(self.user.id)
        self.assertDictEqual(props['spotify'], {
            'access_token': 'token',
            'permission': 'permission',
        })

        response = self.client.get(url_for('user.profile', user_name=self.weirduser.musicbrainz_id))
        self.assert200(response)
        props = ujson.loads(self.get_context_variable('props'))
        mock_domain_spotify.get_user_dict.assert_called_with(self.user.id)
        self.assertDictEqual(props['spotify'], {
            'access_token': 'token',
            'permission': 'permission',
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

    def test_follow_user(self):
        followed_user = db_user.get_or_create(3, 'followed_user')

        self.temporary_login(self.user.login_id)
        r = self.client.post('/user/followed_user/follow')
        self.assert200(r)
        self.assertTrue(db_user_relationship.is_following_user(self.user.id, followed_user['id']))

    def test_follow_user_requires_login(self):
        r = self.client.post('/user/followed_user/follow')
        self.assertNotEqual(r.status_code, 200)

    def test_following_a_nonexistent_user_errors_out(self):
        self.temporary_login(self.user.login_id)
        r = self.client.post('/user/user_doesnt_exist_lol/follow')
        self.assertEqual(r.status_code, 404)

    def test_following_yourself_errors_out(self):
        self.temporary_login(self.user.login_id)
        r = self.client.post(f'/user/{self.user.musicbrainz_id}/follow')
        self.assert400(r)

    def test_follow_user_twice_leads_to_error(self):
        followed_user = db_user.get_or_create(3, 'followed_user')

        self.temporary_login(self.user.login_id)
        r = self.client.post('/user/followed_user/follow')
        self.assert200(r)
        self.assertTrue(db_user_relationship.is_following_user(self.user.id, followed_user['id']))

        # now, try to follow again, this time expecting a 400
        r = self.client.post('/user/followed_user/follow')
        self.assert400(r)

    def test_unfollow_user(self):
        followed_user = db_user.get_or_create(3, 'followed_user')

        self.temporary_login(self.user.login_id)

        # first, follow the user
        r = self.client.post('/user/followed_user/follow')
        self.assert200(r)
        self.assertTrue(db_user_relationship.is_following_user(self.user.id, followed_user['id']))

        # now, unfollow and check the db
        r = self.client.post('/user/followed_user/unfollow')
        self.assert200(r)
        self.assertFalse(db_user_relationship.is_following_user(self.user.id, followed_user['id']))

    def test_unfollow_user_requires_login(self):
        r = self.client.post('/user/followed_user/unfollow')
        self.assertNotEqual(r.status_code, 200)

    def _create_test_data(self, user_name):
        min_ts = -1
        max_ts = -1
        self.test_data = create_test_data_for_timescalelistenstore(user_name)
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

    @mock.patch('listenbrainz.webserver.timescale_connection._ts.get_timestamps_for_user')
    @mock.patch('listenbrainz.webserver.timescale_connection._ts.fetch_listens')
    def test_ts_filters(self, timescale, timestamps):
        """Check that max_ts and min_ts are passed to timescale """
        (min_ts, max_ts) = self._create_test_data('iliekcomputers')
        timestamps.return_value = (min_ts, max_ts)

        # If no parameter is given, use current time as the to_ts
        self.client.get(url_for('user.profile', user_name='iliekcomputers'))
        req_call = mock.call('iliekcomputers', limit=25, to_ts=1400000201)
        timescale.assert_has_calls([req_call])
        timescale.reset_mock()

        # max_ts query param -> to_ts timescale param
        self.client.get(url_for('user.profile', user_name='iliekcomputers'), query_string={'max_ts': 1520946000})
        req_call = mock.call('iliekcomputers', limit=25, to_ts=1520946000)
        timescale.assert_has_calls([req_call])
        timescale.reset_mock()

        # min_ts query param -> from_ts timescale param
        self.client.get(url_for('user.profile', user_name='iliekcomputers'), query_string={'min_ts': 1520941000})
        req_call = mock.call('iliekcomputers', limit=25, from_ts=1520941000)
        timescale.assert_has_calls([req_call])
        timescale.reset_mock()

        # If max_ts and min_ts set, only max_ts is used
        self.client.get(url_for('user.profile', user_name='iliekcomputers'),
                        query_string={'min_ts': 1520941000, 'max_ts': 1520946000})
        req_call = mock.call('iliekcomputers', limit=25, to_ts=1520946000)
        timescale.assert_has_calls([req_call])

    @mock.patch('listenbrainz.webserver.timescale_connection._ts.get_timestamps_for_user')
    @mock.patch('listenbrainz.webserver.timescale_connection._ts.fetch_listens')
    def test_ts_filters_errors(self, timescale, timestamps):
        """If max_ts and min_ts are not integers, show an error page"""
        (min_ts, max_ts) = self._create_test_data('iliekcomputers')
        timestamps.return_value = (min_ts, max_ts)

        response = self.client.get(url_for('user.profile', user_name='iliekcomputers'),
                                   query_string={'max_ts': 'a'})
        self.assert400(response)
        self.assertIn(b'Incorrect timestamp argument max_ts: a', response.data)

        response = self.client.get(url_for('user.profile', user_name='iliekcomputers'),
                                   query_string={'min_ts': 'b'})
        self.assert400(response)
        self.assertIn(b'Incorrect timestamp argument min_ts: b', response.data)

        timescale.assert_not_called()
