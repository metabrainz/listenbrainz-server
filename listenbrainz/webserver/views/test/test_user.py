import listenbrainz.db.stats as db_stats
import listenbrainz.db.user as db_user
import ujson
from unittest import mock

from flask import url_for, current_app
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
<<<<<<< HEAD
=======

>>>>>>> 3cf80797c8b11f4e51303d59f70927f102a6b6e4
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

        # check that artist count is shown if stats have been calculated
        db_stats.insert_user_stats(
            user_id=self.user.id,
            artists={},
            recordings={},
            releases={},
            artist_count=2,
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

    def test_top_artists(self):
        """ Tests the artist stats view """

        # when no stats in db, it should redirect to the profile page
        r = self.client.get(url_for('user.artists', user_name=self.user.musicbrainz_id))
        self.assertRedirects(r, url_for('user.profile', user_name=self.user.musicbrainz_id))

        r = self.client.get(url_for('user.artists', user_name=self.user.musicbrainz_id), follow_redirects=True)
        self.assert200(r)
        self.assertIn('No data calculated', r.data.decode('utf-8'))

        # add some artist stats to the db
        with open(self.path_to_data_file('user_top_artists.json')) as f:
            artists = ujson.load(f)

        # insert empty documents to check for KeyError / ISE
        db_stats.insert_user_stats(
            user_id=self.user.id,
            artists={},
            recordings={},
            releases={},
            artist_count=2,
        )

        r = self.client.get(url_for('user.artists', user_name=self.user.musicbrainz_id))
        self.assert200(r)
        self.assertContext('active_section', 'artists')

        db_stats.insert_user_stats(
            user_id=self.user.id,
            artists=artists,
            recordings={},
            releases={},
            artist_count=2,
        )

        r = self.client.get(url_for('user.artists', user_name=self.user.musicbrainz_id))
        self.assert200(r)
        self.assertContext('active_section', 'artists')

    def _create_test_data(self, user_name):
        test_data = create_test_data_for_timescalelistenstore(user_name)
        self.logstore.insert(test_data)

    def test_username_case(self):
        """Tests that the username in URL is case insensitive"""
        self._create_test_data('iliekcomputers')

        response1 = self.client.get(url_for('user.profile', user_name='iliekcomputers'))
        self.assertContext('user', self.user)
        response2 = self.client.get(url_for('user.profile', user_name='IlieKcomPUteRs'))
        self.assertContext('user', self.user)
        self.assert200(response1)
        self.assert200(response2)

    @mock.patch('listenbrainz.webserver.views.user.time')
    @mock.patch('listenbrainz.webserver.timescale_connection._ts.fetch_listens')
    def test_ts_filters(self, timescale, m_time):
        """Check that max_ts and min_ts are passed to timescale """
        # If no parameter is given, use current time as the to_ts
        m_time.time.return_value = 1520946608
        self.client.get(url_for('user.profile', user_name='iliekcomputers'))
        req_call = mock.call('iliekcomputers', limit=25, to_ts=1520946608)
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


    @mock.patch('listenbrainz.webserver.timescale_connection._ts.fetch_listens')
    def test_ts_filters_errors(self, timescale):
        """If max_ts and min_ts are not integers, show an error page"""
        self._create_test_data('iliekcomputers')
        response = self.client.get(url_for('user.profile', user_name='iliekcomputers'),
                                   query_string={'max_ts': 'a'})
        self.assert400(response)
        self.assertIn(b'Incorrect timestamp argument max_ts: a', response.data)

        response = self.client.get(url_for('user.profile', user_name='iliekcomputers'),
                                   query_string={'min_ts': 'b'})
        self.assert400(response)
        self.assertIn(b'Incorrect timestamp argument min_ts: b', response.data)

        timescale.assert_not_called()
