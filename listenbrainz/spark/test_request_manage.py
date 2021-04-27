""" Tests the spark request manage.py commands and
helper functions
"""

# listenbrainz-server - Server for the ListenBrainz project.
#
# Copyright (C) 2019 Param Singh <iliekcomputers@gmail.com>
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
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA"

import ujson
import os
import unittest

from click.testing import CliRunner
from listenbrainz.spark import request_manage


class RequestManageTestCase(unittest.TestCase):

    def test_get_possible_queries(self):
        QUERIES_JSON_PATH = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'request_queries.json')
        with open(QUERIES_JSON_PATH) as f:
            expected_query_list = ujson.load(f)
        received_query_list = request_manage._get_possible_queries()
        self.assertDictEqual(expected_query_list, received_query_list)

    def test_prepare_query_message_exception_if_invalid_query(self):
        """ Testing all cases with invalid queries
        """
        # query name doesn't exist in the list
        with self.assertRaises(request_manage.InvalidSparkRequestError):
            request_manage._prepare_query_message('getmesomething')

        # extra parameter given
        with self.assertRaises(request_manage.InvalidSparkRequestError):
            request_manage._prepare_query_message('stats.user.listening_activity.week', {'musicbrainz_id': 'wtf'})

        # invalid parameter given
        with self.assertRaises(request_manage.InvalidSparkRequestError):
            request_manage._prepare_query_message('stats.user.entity.week', {'invalid_param': 'wtf'})

        # extra (unexpected) parameter passed
        with self.assertRaises(request_manage.InvalidSparkRequestError):
            request_manage._prepare_query_message('stats.user.entity.week', {'entity': 'recordings', 'param2': 'bbq'})

        # expected parameter not passed
        with self.assertRaises(request_manage.InvalidSparkRequestError):
            request_manage._prepare_query_message('stats.user.entity.week', {})

    def test_prepare_query_message_happy_path(self):
        expected_message = ujson.dumps({'query': 'stats.user.entity.week', 'params': {'entity': 'test'}})
        received_message = request_manage._prepare_query_message('stats.user.entity.week', params={'entity': 'test'})
        self.assertEqual(expected_message, received_message)

        expected_message = ujson.dumps({'query': 'stats.user.entity.month', 'params': {'entity': 'test'}})
        received_message = request_manage._prepare_query_message('stats.user.entity.month', params={'entity': 'test'})
        self.assertEqual(expected_message, received_message)

        expected_message = ujson.dumps({'query': 'stats.user.entity.year', 'params': {'entity': 'test'}})
        received_message = request_manage._prepare_query_message('stats.user.entity.year', params={'entity': 'test'})
        self.assertEqual(expected_message, received_message)

        expected_message = ujson.dumps({'query': 'stats.user.entity.all_time', 'params': {'entity': 'test'}})
        received_message = request_manage._prepare_query_message('stats.user.entity.all_time', params={'entity': 'test'})
        self.assertEqual(expected_message, received_message)

        expected_message = ujson.dumps({'query': 'stats.user.listening_activity.week'})
        received_message = request_manage._prepare_query_message('stats.user.listening_activity.week')
        self.assertEqual(expected_message, received_message)

        expected_message = ujson.dumps({'query': 'stats.user.listening_activity.month'})
        received_message = request_manage._prepare_query_message('stats.user.listening_activity.month')
        self.assertEqual(expected_message, received_message)

        expected_message = ujson.dumps({'query': 'stats.user.listening_activity.year'})
        received_message = request_manage._prepare_query_message('stats.user.listening_activity.year')
        self.assertEqual(expected_message, received_message)

        expected_message = ujson.dumps({'query': 'stats.user.listening_activity.all_time'})
        received_message = request_manage._prepare_query_message('stats.user.listening_activity.all_time')
        self.assertEqual(expected_message, received_message)

        expected_message = ujson.dumps({'query': 'stats.user.daily_activity.week'})
        received_message = request_manage._prepare_query_message('stats.user.daily_activity.week')
        self.assertEqual(expected_message, received_message)

        expected_message = ujson.dumps({'query': 'stats.user.daily_activity.month'})
        received_message = request_manage._prepare_query_message('stats.user.daily_activity.month')
        self.assertEqual(expected_message, received_message)

        expected_message = ujson.dumps({'query': 'stats.user.daily_activity.year'})
        received_message = request_manage._prepare_query_message('stats.user.daily_activity.year')
        self.assertEqual(expected_message, received_message)

        expected_message = ujson.dumps({'query': 'stats.user.daily_activity.all_time'})
        received_message = request_manage._prepare_query_message('stats.user.daily_activity.all_time')
        self.assertEqual(expected_message, received_message)

        expected_message = ujson.dumps({'query': 'stats.sitewide.entity.week', 'params': {
                                       'entity': 'test', 'use_mapping': False}})
        received_message = request_manage._prepare_query_message(
            'stats.sitewide.entity.week', params={'entity': 'test', 'use_mapping': False})
        self.assertEqual(expected_message, received_message)

        expected_message = ujson.dumps({'query': 'stats.sitewide.entity.month', 'params': {
                                       'entity': 'test', 'use_mapping': False}})
        received_message = request_manage._prepare_query_message(
            'stats.sitewide.entity.month', params={'entity': 'test', 'use_mapping': False})
        self.assertEqual(expected_message, received_message)

        expected_message = ujson.dumps({'query': 'stats.sitewide.entity.year', 'params': {
                                       'entity': 'test', 'use_mapping': False}})
        received_message = request_manage._prepare_query_message(
            'stats.sitewide.entity.year', params={'entity': 'test', 'use_mapping': False})
        self.assertEqual(expected_message, received_message)

        expected_message = ujson.dumps({'query': 'stats.sitewide.entity.all_time',
                                        'params': {'entity': 'test', 'use_mapping': False}})
        received_message = request_manage._prepare_query_message('stats.sitewide.entity.all_time', params={
                                                                 'entity': 'test', 'use_mapping': False})
        self.assertEqual(expected_message, received_message)

        message = {
            'query': 'cf.recommendations.recording.create_dataframes',
            'params': {
                'train_model_window': 20,
            }
        }
        expected_message = ujson.dumps(message)
        received_message = request_manage._prepare_query_message('cf.recommendations.recording.create_dataframes',
                                                                 message['params'])
        self.assertEqual(expected_message, received_message)

        message = {
            'query': 'cf.recommendations.recording.train_model',
            'params': {
                'ranks': [1, 2],
                'lambdas': [2.0, 3.0],
                'iterations': [2, 3],
                'alpha': 3.0,
            }
        }
        expected_message = ujson.dumps(message)
        received_message = request_manage._prepare_query_message('cf.recommendations.recording.train_model',
                                                                 message['params'])
        self.assertEqual(expected_message, received_message)

        message = {
            'query': 'cf.recommendations.recording.candidate_sets',
            'params': {
                'recommendation_generation_window': 7,
                'top_artist_limit': 10,
                'similar_artist_limit': 10,
                "users": ['vansika'],
                "html_flag": True
            }
        }
        expected_message = ujson.dumps(message)
        received_message = request_manage._prepare_query_message('cf.recommendations.recording.candidate_sets',
                                                                 message['params'])
        self.assertEqual(expected_message, received_message)

        message = {
            'query': 'cf.recommendations.recording.recommendations',
            'params': {
                'recommendation_top_artist_limit': 7,
                'recommendation_similar_artist_limit': 7,
                'users': ['vansika']
            }
        }
        expected_message = ujson.dumps(message)
        received_message = request_manage._prepare_query_message('cf.recommendations.recording.recommendations',
                                                                 message['params'])
        self.assertEqual(expected_message, received_message)

        expected_message = ujson.dumps({'query': 'import.mapping'})
        received_message = request_manage._prepare_query_message('import.mapping')
        self.assertEqual(expected_message, received_message)

        expected_message = ujson.dumps({'query': 'import.artist_relation'})
        received_message = request_manage._prepare_query_message('import.artist_relation')
        self.assertEqual(expected_message, received_message)
