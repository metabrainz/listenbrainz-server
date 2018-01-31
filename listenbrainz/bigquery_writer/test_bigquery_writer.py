""" Tests for BigQueryWriter """

# listenbrainz-server - Server for the ListenBrainz project
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
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.

import unittest
from listenbrainz.bigquery_writer.bigquery_writer import BigQueryWriter

class BigQueryWriterTestCase(unittest.TestCase):


    def setUp(self):
        self.bqwriter = BigQueryWriter()


    def test_convert_listens_to_bigquery_payload(self):
        listens = [
            {
                'user_name': 'iliekcomputers',
                'listened_at': 1514304044,
                'recording_msid': '868f2a3e-c97a-416e-82ee-5a0f74015aa8',
                'track_metadata': {
                    'track_name': 'Good Guy',
                    'artist_name': 'Frank Ocean',
                    'additional_info': {
                        'artist_msid': '145bdcc6-35c3-4456-9257-0af8c9e79bed',
                    }
                }
            },
            {
                'user_name': 'iliekcomputers',
                'listened_at': 1514304050,
                'recording_msid': '868f2a3e-c97a-416e-82ee-5a0f74015aa8',
                'track_metadata': {
                    'track_name': 'Good Guy',
                    'artist_name': 'Frank Ocean',
                    'release_name': 'Blonde',
                    'additional_info': {
                        'artist_msid': '145bdcc6-35c3-4456-9257-0af8c9e79bed',
                        'artist_mbids': ['e520459c-dff4-491d-a6e4-c97be35e0044'],
                        'release_msid': '9c42ded3-f344-48e8-b939-874aa94cbe20',
                        'release_mbid': '8294645a-f996-44b6-9060-7f189b9f59f3',
                        'recording_mbid': 'c4625cbf-f5a8-46d9-baa5-ba8c3b9127bc',
                        'tags': ['rnb', 'pop'],
                    }
                }
            },
        ]

        payload = self.bqwriter.convert_to_bigquery_payload(listens)
        self.assertEqual(len(payload), 2)
        self.assertEqual(payload[0]['insertId'], 'iliekcomputers-1514304044-868f2a3e-c97a-416e-82ee-5a0f74015aa8')
        self.assertDictEqual(payload[0]['json'], {
            'user_name': 'iliekcomputers',
            'listened_at': 1514304044,
            'artist_msid': '145bdcc6-35c3-4456-9257-0af8c9e79bed',
            'artist_name': 'Frank Ocean',
            'artist_mbids': '',
            'release_msid': '',
            'release_mbid': '',
            'release_name': '',
            'track_name': 'Good Guy',
            'recording_msid': '868f2a3e-c97a-416e-82ee-5a0f74015aa8',
            'recording_mbid': '',
            'tags': '',
        })


        self.assertEqual(payload[1]['insertId'], 'iliekcomputers-1514304050-868f2a3e-c97a-416e-82ee-5a0f74015aa8')
        self.assertDictEqual(payload[1]['json'], {
            'user_name': 'iliekcomputers',
            'listened_at': 1514304050,
            'artist_msid': '145bdcc6-35c3-4456-9257-0af8c9e79bed',
            'artist_name': 'Frank Ocean',
            'artist_mbids': 'e520459c-dff4-491d-a6e4-c97be35e0044',
            'release_msid': '9c42ded3-f344-48e8-b939-874aa94cbe20',
            'release_mbid': '8294645a-f996-44b6-9060-7f189b9f59f3',
            'release_name': 'Blonde',
            'track_name': 'Good Guy',
            'recording_msid': '868f2a3e-c97a-416e-82ee-5a0f74015aa8',
            'recording_mbid': 'c4625cbf-f5a8-46d9-baa5-ba8c3b9127bc',
            'tags': 'rnb,pop',
        })
