from flask import url_for

import listenbrainz.db.user as db_user
from listenbrainz.db.testing import DatabaseTestCase
from listenbrainz.webserver.testing import ServerTestCase

from listenbrainz.listenstore.tests.util import create_test_data_for_influxlistenstore
from listenbrainz.webserver.influx_connection import init_influx_connection
from influxdb import InfluxDBClient
from listenbrainz import config
import logging


class UserViewsTestCase(ServerTestCase, DatabaseTestCase):
    def setUp(self):
        ServerTestCase.setUp(self)
        DatabaseTestCase.setUp(self)
        self.user = db_user.get_or_create('iliekcomputers')
        self.weirduser = db_user.get_or_create('weird\\user name')

        self.log = logging.getLogger(__name__)

        influx = InfluxDBClient(host=config.INFLUX_HOST, port=config.INFLUX_PORT, database=config.INFLUX_DB_NAME)
        influx.query('''drop database %s''' % config.INFLUX_DB_NAME)
        influx.query('''create database %s''' % config.INFLUX_DB_NAME)

        self.logstore = init_influx_connection(self.log, {
            'REDIS_HOST': config.REDIS_HOST,
            'REDIS_PORT': config.REDIS_PORT,
            'INFLUX_HOST': config.INFLUX_HOST,
            'INFLUX_PORT': config.INFLUX_PORT,
            'INFLUX_DB_NAME': config.INFLUX_DB_NAME,
        })

    def tearDown(self):
        self.logstore = None
        ServerTestCase.tearDown(self)
        DatabaseTestCase.tearDown(self)

    def test_user_page(self):
        response = self.client.get(url_for('user.profile', user_name=self.user['musicbrainz_id']))
        self.assert200(response)

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

    def _create_test_data(self, user_name):
        test_data = create_test_data_for_influxlistenstore(user_name)
        self.logstore.insert(test_data)

    def test_username_case(self):
        """Tests that the username in URL is case insenstive"""
        self._create_test_data(self.user['musicbrainz_id'])

        response1 = self.client.get(url_for('user.profile', user_name='iliekcomputers'))
        response2 = self.client.get(url_for('user.profile', user_name='IlieKcomPUteRs'))
        self.assert200(response1)
        self.assert200(response2)
        self.assertEqual(response1.data.decode('utf-8'), response2.data.decode('utf-8'))
