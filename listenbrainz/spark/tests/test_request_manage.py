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

import os
import unittest

import orjson

from listenbrainz.spark import request_manage


class RequestManageTestCase(unittest.TestCase):

    def test_get_possible_queries(self):
        QUERIES_JSON_PATH = os.path.join(os.path.dirname(os.path.realpath(__file__)), '../request_queries.json')
        with open(QUERIES_JSON_PATH) as f:
            expected_query_list = orjson.loads(f.read())
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
            request_manage._prepare_query_message('stats.user.listening_activity.week', musicbrainz_id='wtf')

        # invalid parameter given
        with self.assertRaises(request_manage.InvalidSparkRequestError):
            request_manage._prepare_query_message('stats.user.entity', invalid_param='wtf')

        # extra (unexpected) parameter passed
        with self.assertRaises(request_manage.InvalidSparkRequestError):
            request_manage._prepare_query_message('stats.user.entity', entity='recordings', param2='bbq')

        # expected parameter not passed
        with self.assertRaises(request_manage.InvalidSparkRequestError):
            request_manage._prepare_query_message('stats.user.entity')

    def test_prepare_query_message_happy_path(self):
        expected_message = orjson.dumps({'query': 'stats.user.entity', 'params': {'entity': 'test', 'stats_range': 'week', 'database': 'test_week_20220718'}})
        received_message = request_manage._prepare_query_message('stats.user.entity', entity='test', stats_range='week', database='test_week_20220718')
        self.assertEqual(expected_message, received_message)

        expected_message = orjson.dumps({'query': 'stats.user.entity', 'params': {'entity': 'test', 'stats_range': 'month', 'database': 'test_month_20220718'}})
        received_message = request_manage._prepare_query_message('stats.user.entity', entity='test', stats_range='month', database='test_month_20220718')
        self.assertEqual(expected_message, received_message)

        expected_message = orjson.dumps({'query': 'stats.user.entity', 'params': {'entity': 'test', 'stats_range': 'year', 'database': 'test_year_20220718'}})
        received_message = request_manage._prepare_query_message('stats.user.entity', entity='test', stats_range='year', database='test_year_20220718')
        self.assertEqual(expected_message, received_message)

        expected_message = orjson.dumps({'query': 'stats.user.entity', 'params': {'entity': 'test', 'stats_range': 'all_time', 'database': 'test_all_time_20220718'}})
        received_message = request_manage._prepare_query_message('stats.user.entity', entity='test', stats_range='all_time', database='test_all_time_20220718')
        self.assertEqual(expected_message, received_message)

        expected_message = orjson.dumps({'query': 'stats.user.listening_activity', 'params': {'stats_range': 'week', 'database': 'test_week_20220718'}})
        received_message = request_manage._prepare_query_message('stats.user.listening_activity', stats_range='week', database='test_week_20220718')
        self.assertEqual(expected_message, received_message)

        expected_message = orjson.dumps({'query': 'stats.user.listening_activity', 'params': {'stats_range': 'month', 'database': 'test_month_20220718'}})
        received_message = request_manage._prepare_query_message('stats.user.listening_activity', stats_range='month', database='test_month_20220718')
        self.assertEqual(expected_message, received_message)

        expected_message = orjson.dumps({'query': 'stats.user.listening_activity', 'params': {'stats_range': 'year', 'database': 'test_year_20220718'}})
        received_message = request_manage._prepare_query_message('stats.user.listening_activity', stats_range='year', database='test_year_20220718')
        self.assertEqual(expected_message, received_message)

        expected_message = orjson.dumps({'query': 'stats.user.listening_activity', 'params': {'stats_range': 'all_time', 'database': 'test_all_time_20220718'}})
        received_message = request_manage._prepare_query_message('stats.user.listening_activity', stats_range='all_time', database='test_all_time_20220718')
        self.assertEqual(expected_message, received_message)

        expected_message = orjson.dumps({'query': 'stats.user.daily_activity', 'params': {'stats_range': 'week', 'database': 'daily_activity_week_20220718'}})
        received_message = request_manage._prepare_query_message('stats.user.daily_activity', stats_range='week', database='daily_activity_week_20220718')
        self.assertEqual(expected_message, received_message)

        expected_message = orjson.dumps({'query': 'stats.user.daily_activity', 'params': {'stats_range': 'month', 'database': 'daily_activity_month_20220718'}})
        received_message = request_manage._prepare_query_message('stats.user.daily_activity', stats_range='month', database='daily_activity_month_20220718')
        self.assertEqual(expected_message, received_message)

        expected_message = orjson.dumps({'query': 'stats.user.daily_activity', 'params': {'stats_range': 'year', 'database': 'daily_activity_year_20220718'}})
        received_message = request_manage._prepare_query_message('stats.user.daily_activity', stats_range='year', database='daily_activity_year_20220718')
        self.assertEqual(expected_message, received_message)

        expected_message = orjson.dumps({'query': 'stats.user.daily_activity', 'params': {'stats_range': 'all_time', 'database': 'daily_activity_all_time_20220718'}})
        received_message = request_manage._prepare_query_message('stats.user.daily_activity', stats_range='all_time', database='daily_activity_all_time_20220718')
        self.assertEqual(expected_message, received_message)

        expected_message = orjson.dumps({'query': 'stats.sitewide.entity', 'params': {'entity': 'test', 'stats_range': 'week'}})
        received_message = request_manage._prepare_query_message('stats.sitewide.entity', entity='test', stats_range='week')
        self.assertEqual(expected_message, received_message)

        expected_message = orjson.dumps({'query': 'stats.sitewide.entity', 'params': {'entity': 'test', 'stats_range': 'month'}})
        received_message = request_manage._prepare_query_message('stats.sitewide.entity', entity='test', stats_range='month')
        self.assertEqual(expected_message, received_message)

        expected_message = orjson.dumps({'query': 'stats.sitewide.entity', 'params': {'entity': 'test', 'stats_range': 'year'}})
        received_message = request_manage._prepare_query_message('stats.sitewide.entity', entity='test', stats_range='year')
        self.assertEqual(expected_message, received_message)

        expected_message = orjson.dumps({'query': 'stats.sitewide.entity', 'params': {'entity': 'test', 'stats_range': 'all_time'}})
        received_message = request_manage._prepare_query_message('stats.sitewide.entity', entity='test', stats_range='all_time')
        self.assertEqual(expected_message, received_message)

        message = {
            'query': 'cf.recommendations.recording.create_dataframes',
            'params': {
                'train_model_window': 20,
                'job_type': "recommendation_recording",
                'minimum_listens_threshold': 0,
            }
        }
        expected_message = orjson.dumps(message)
        received_message = request_manage._prepare_query_message('cf.recommendations.recording.create_dataframes',
                                                                 **message['params'])
        self.assertEqual(expected_message, received_message)

        message = {
            'query': 'cf.recommendations.recording.train_model',
            'params': {
                'ranks': [1, 2],
                'lambdas': [2.0, 3.0],
                'iterations': [2, 3],
                'alphas': [3.0],
                'use_transformed_listencounts': False
            }
        }
        expected_message = orjson.dumps(message)
        received_message = request_manage._prepare_query_message('cf.recommendations.recording.train_model',
                                                                 **message['params'])
        self.assertEqual(expected_message, received_message)

        message = {
            'query': 'cf.recommendations.recording.recommendations',
            'params': {
                'recommendation_raw_limit': 7,
                'users': ['vansika']
            }
        }
        expected_message = orjson.dumps(message)
        received_message = request_manage._prepare_query_message('cf.recommendations.recording.recommendations',
                                                                 **message['params'])
        self.assertEqual(expected_message, received_message)

        message = {
            'query': 'similarity.similar_users',
            'params': {
                'max_num_users': 25 
            }
        }
        expected_message = orjson.dumps(message)
        received_message = request_manage._prepare_query_message('similarity.similar_users', max_num_users=25)
        self.assertEqual(expected_message, received_message)
