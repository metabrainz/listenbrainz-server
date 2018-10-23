# messybrainz-server - Server for the MessyBrainz project
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
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA)

import json

from messybrainz import db
from messybrainz.db import data
from messybrainz.db.testing import DatabaseTestCase


recording = {
    'artist': 'Frank Ocean',
    'release': 'Blond',
    'title': 'Pretty Sweet',
    'additional_info': {
        'key1': 'Value1',
    },
}

recording_diff_case = {
    'artist': 'FRANK OCEAN',
    'release': 'BLoNd',
    'title': 'PReTtY SWEET',
    'additional_info': {
        'key1': 'VaLue1',
    },
}

class DataTestCase(DatabaseTestCase):

    def test_get_id_from_meta_hash(self):
        with db.engine.connect() as connection:
            recording_msid = data.submit_recording(connection, recording)
            self.assertEqual(recording_msid, str(data.get_id_from_meta_hash(connection, recording)))


    def test_submit_recording(self):
        with db.engine.connect() as connection:
            recording_msid = data.submit_recording(connection, recording)
            self.assertEqual(recording_msid, str(data.get_id_from_recording(connection, recording)))


    def test_get_artist_credit(self):
        with db.engine.connect() as connection:
            recording_msid = data.submit_recording(connection, recording)
            artist_msid = data.get_artist_credit(connection, recording['artist'])
            recording_data = data.load_recording(connection, recording_msid)
            self.assertEqual(artist_msid, recording_data['ids']['artist_msid'])


    def test_get_release(self):
        with db.engine.connect() as connection:
            recording_msid = data.submit_recording(connection, recording)
            release_msid = data.get_release(connection, recording['release'])
            recording_data = data.load_recording(connection, recording_msid)
            self.assertEqual(release_msid, recording_data['ids']['release_msid'])


    def test_add_artist_credit(self):
        with db.engine.connect() as connection:
            artist_msid = data.add_artist_credit(connection, 'Kanye West')
            self.assertEqual(artist_msid, data.get_artist_credit(connection, 'Kanye West'))


    def test_add_release(self):
        with db.engine.connect() as connection:
            release_msid = data.add_release(connection, 'The College Dropout')
            self.assertEqual(release_msid, data.get_release(connection, 'The College Dropout'))

    def test_add_recording_different_cases(self):
        """ Tests that recordings with only case differences get the same MessyBrainz ID.
        """
        with db.engine.connect() as connection:
            msid1 = data.submit_recording(connection, recording)
            msid2 = str(data.get_id_from_recording(connection, recording_diff_case))
            self.assertEqual(msid1, msid2)

    def test_load_recording(self):
        with db.engine.connect() as connection:
            recording_msid = data.submit_recording(connection, recording)
            result = data.load_recording(connection, recording_msid)
            self.assertDictEqual(result['payload'], recording)

    def test_convert_to_messybrainz_json(self):
        transformed_json = data.convert_to_messybrainz_json(recording, transform=True)
        result = json.loads(transformed_json)
        self.assertEqual(result['artist'], recording['artist'].lower())
        self.assertEqual(result['release'], recording['release'].lower())
        self.assertEqual(result['title'], recording['title'].lower())
        self.assertEqual(result['additional_info']['key1'], recording['additional_info']['key1'].lower())

        non_transformed_json = data.convert_to_messybrainz_json(recording, transform=False)
        self.assertDictEqual(json.loads(non_transformed_json), recording)
