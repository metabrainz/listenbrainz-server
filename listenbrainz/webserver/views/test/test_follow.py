import listenbrainz.db.user as db_user
import ujson
from unittest import mock

from flask import url_for, current_app
from influxdb import InfluxDBClient
from listenbrainz.db.testing import DatabaseTestCase
from listenbrainz.listenstore.tests.util import create_test_data_for_influxlistenstore
from listenbrainz.webserver.influx_connection import init_influx_connection
from listenbrainz.webserver.login import User
from listenbrainz.webserver.testing import ServerTestCase

import listenbrainz.db.user as db_user


class FollowViewsTestCase(ServerTestCase, DatabaseTestCase):
    def setUp(self):
        ServerTestCase.setUp(self)
        DatabaseTestCase.setUp(self)

        user = db_user.get_or_create(1, 'iliekcomputers')
        self.user = User.from_dbrow(user)


    def tearDown(self):
        ServerTestCase.tearDown(self)
        DatabaseTestCase.tearDown(self)


    def test_follow_page(self):
        response = self.client.get(url_for('follow.follow', user_name=self.user.musicbrainz_id))
        self.assert200(response)
        self.assertContext('active_section', 'listens')


    def test_user_info_not_logged_in(self):
        """Tests user follow view when not logged in"""
        response = self.client.get(url_for('follow.follow'))
        self.assertStatus(response, 200)
