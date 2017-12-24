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


from messybrainz import db
from messybrainz import data
from messybrainz.testing import DatabaseTestCase


recording = {
    'artist': 'Frank Ocean',
    'release': 'Blond',
    'title': 'Pretty Sweet',
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
