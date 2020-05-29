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
            request_manage._prepare_query_message('stats.user.all', {'musicbrainz_id': 'wtf'})

        # invalid parameter given
        with self.assertRaises(request_manage.InvalidSparkRequestError):
            request_manage._prepare_query_message('stats.user.for_one_user', {'invalid_param': 'wtf'})

        # extra (unexpected) parameter passed
        with self.assertRaises(request_manage.InvalidSparkRequestError):
            request_manage._prepare_query_message('stats.user.for_one_user', {'musicbrainz_id': 'wtf', 'param2': 'bbq'})

        # expected parameter not passed
        with self.assertRaises(request_manage.InvalidSparkRequestError):
            request_manage._prepare_query_message('stats.user.for_one_user', {})

    def test_prepare_query_message_happy_path(self):
        expected_message = ujson.dumps({'query': 'stats.user.all'})
        received_message = request_manage._prepare_query_message('stats.user.all')
        self.assertEqual(expected_message, received_message)

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

        message = {
            'query': 'cf_recording.recommendations.create_dataframes',
            'params': {
                'train_model_window': 20,
            }
        }
        expected_message = ujson.dumps(message)
        received_message = request_manage._prepare_query_message('cf_recording.recommendations.create_dataframes',
                                                                 message['params'])
        self.assertEqual(expected_message, received_message)

        expected_message = ujson.dumps({'query': 'cf_recording.recommendations.train_model'})
        received_message = request_manage._prepare_query_message('cf_recording.recommendations.train_model')
        self.assertEqual(expected_message, received_message)

        message = {
            'query': 'cf_recording.recommendations.candidate_sets',
            'params': {
                'recommendation_generation_window': 20,
            }
        }
        expected_message = ujson.dumps(message)
        received_message = request_manage._prepare_query_message('cf_recording.recommendations.candidate_sets',
                                                                 message['params'])
        self.assertEqual(expected_message, received_message)

        expected_message = ujson.dumps({'query': 'cf_recording.recommendations.recommend'})
        received_message = request_manage._prepare_query_message('cf_recording.recommendations.recommend')
        self.assertEqual(expected_message, received_message)
