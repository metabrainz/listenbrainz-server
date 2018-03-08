import listenbrainz.db.stats as db_stats
import listenbrainz.db.user as db_user
import ujson

from flask import url_for, current_app
from influxdb import InfluxDBClient
from listenbrainz.db.testing import DatabaseTestCase
from listenbrainz.listenstore.tests.util import create_test_data_for_influxlistenstore
from listenbrainz.webserver.influx_connection import init_influx_connection
from listenbrainz.webserver.testing import ServerTestCase

import listenbrainz.db.user as db_user
import logging


class UserViewsTestCase(ServerTestCase, DatabaseTestCase):
    def setUp(self):
        ServerTestCase.setUp(self)
        DatabaseTestCase.setUp(self)
        self.user = db_user.get_or_create('iliekcomputers')
        self.weirduser = db_user.get_or_create('weird\\user name')

        self.log = logging.getLogger(__name__)
        self.influx = InfluxDBClient(
            host=current_app.config['INFLUX_HOST'],
            port=current_app.config['INFLUX_PORT'],
            database=current_app.config['INFLUX_DB_NAME'],
        )

        self.influx.query('''create database %s''' % current_app.config['INFLUX_DB_NAME'])

        self.logstore = init_influx_connection(self.log, {
            'REDIS_HOST': current_app.config['REDIS_HOST'],
            'REDIS_PORT': current_app.config['REDIS_PORT'],
            'REDIS_NAMESPACE': current_app.config['REDIS_NAMESPACE'],
            'INFLUX_HOST': current_app.config['INFLUX_HOST'],
            'INFLUX_PORT': current_app.config['INFLUX_PORT'],
            'INFLUX_DB_NAME': current_app.config['INFLUX_DB_NAME'],
        })

    def tearDown(self):
        self.influx.query('''drop database %s''' % current_app.config['INFLUX_DB_NAME'])
        self.logstore = None

        ServerTestCase.tearDown(self)
        DatabaseTestCase.tearDown(self)

    def test_user_page(self):
        response = self.client.get(url_for('user.profile', user_name=self.user['musicbrainz_id']))
        self.assert200(response)
        self.assertContext('section', 'listens')

        # check that artist count is not shown if stats haven't been calculated yet
        response = self.client.get(url_for('user.profile', user_name=self.user['musicbrainz_id']))
        self.assert200(response)
        self.assertTemplateUsed('user/profile.html')
        self.assertContext('artist_count', None)

        # check that artist count is shown if stats have been calculated
        db_stats.insert_user_stats(
            user_id=self.user['id'],
            artists={},
            recordings={},
            releases={},
            artist_count=2,
        )
        response = self.client.get(url_for('user.profile', user_name=self.user['musicbrainz_id']))
        self.assert200(response)
        self.assertTemplateUsed('user/profile.html')
        self.assertContext('artist_count', '2')


    def test_scraper_username(self):
        """ Tests that the username is correctly rendered in the last.fm importer """
        response = self.client.get(
            url_for('user.lastfmscraper', user_name=self.user['musicbrainz_id']),
            query_string={
                'user_token': self.user['auth_token'],
                'lastfm_username': 'dummy',
            }
        )
        self.assert200(response)
        self.assertIn('var user_name = "iliekcomputers";', response.data.decode('utf-8'))

        response = self.client.get(
            url_for('user.lastfmscraper', user_name=self.weirduser['musicbrainz_id']),
            query_string={
                'user_token': self.weirduser['auth_token'],
                'lastfm_username': 'dummy',
            }
        )
        self.assert200(response)
        self.assertIn('var user_name = "weird%5Cuser%20name";', response.data.decode('utf-8'))

    def test_top_artists(self):
        """ Tests the artist stats view """

        # when no stats in db, it should redirect to the profile page
        r = self.client.get(url_for('user.artists', user_name=self.user['musicbrainz_id']))
        self.assertRedirects(r, url_for('user.profile', user_name=self.user['musicbrainz_id']))

        r = self.client.get(url_for('user.artists', user_name=self.user['musicbrainz_id']), follow_redirects=True)
        self.assert200(r)
        self.assertIn('No data calculated', r.data.decode('utf-8'))

        # add some artist stats to the db
        with open(self.path_to_data_file('user_top_artists.json')) as f:
            artists = ujson.load(f)

        db_stats.insert_user_stats(
            user_id=self.user['id'],
            artists=artists,
            recordings={},
            releases={},
            artist_count=2,
        )

        r = self.client.get(url_for('user.artists', user_name=self.user['musicbrainz_id']))
        self.assert200(r)
        self.assertContext('section', 'artists')


    def _create_test_data(self, user_name):
        test_data = create_test_data_for_influxlistenstore(user_name)
        self.logstore.insert(test_data)


    def test_username_case(self):
        """Tests that the username in URL is case insensitive"""
        self._create_test_data('iliekcomputers')

        response1 = self.client.get(url_for('user.profile', user_name='iliekcomputers'))
        response2 = self.client.get(url_for('user.profile', user_name='IlieKcomPUteRs'))
        self.assert200(response1)
        self.assert200(response2)
        self.assertEqual(response1.data.decode('utf-8'), response2.data.decode('utf-8'))
