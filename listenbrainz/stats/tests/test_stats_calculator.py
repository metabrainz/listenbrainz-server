""" This module contains unit tests for the stats_calculator module.
"""

# listenbrainz-server - Server for the ListenBrainz project.
#
# Copyright (C) 2017 MetaBrainz Foundation Inc.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along
# with this program; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA

import os
import listenbrainz.db.stats as db_stats
import listenbrainz.db.user as db_user
import unittest

from listenbrainz import stats
from listenbrainz.db.testing import DatabaseTestCase
from listenbrainz.stats.exceptions import NoCredentialsVariableException, NoCredentialsFileException
from listenbrainz.stats.stats_calculator import StatsCalculator
from listenbrainz.webserver import create_app
from unittest.mock import patch


class StatsCalculatorTestCase(DatabaseTestCase):

    def setUp(self):
        super(StatsCalculatorTestCase, self).setUp()
        self.app = create_app() # create a flask app for config purposes
        self.sc = StatsCalculator()
        self.user = db_user.get_or_create('stats_calculator_test_user')

    @patch('listenbrainz.stats.user.get_top_recordings', side_effect=lambda x: {})
    @patch('listenbrainz.stats.user.get_top_artists', side_effect=lambda x: {})
    @patch('listenbrainz.stats.user.get_top_releases', side_effect=lambda x: {})
    @patch('listenbrainz.stats.user.get_artist_count', side_effect=lambda x: 1)
    def test_calculate_stats_for_user(self, get_top_recordings, get_top_artists, get_top_releases, get_artist_count):
        # invalid user data
        self.assertFalse(self.sc.calculate_stats_for_user({}))

        # now for a valid user
        user = {
            'id': self.user['id'],
            'musicbrainz_id': self.user['musicbrainz_id'],
        }
        self.assertTrue(self.sc.calculate_stats_for_user(user))
        data = db_stats.get_all_user_stats(self.user['id'])
        self.assertIsNotNone(data)
        self.assertEqual(data['artist']['count'], 1)


        # now that we've inserted valid data and 7 days haven't passed,
        # calling the function should return false
        self.assertFalse(self.sc.calculate_stats_for_user(user))
