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
from datetime import datetime, timedelta

from psycopg2.extras import DictCursor
from sqlalchemy import text

from listenbrainz import messybrainz
from listenbrainz.db import timescale
from listenbrainz.db.testing import TimescaleTestCase


recording = {
    'artist': 'Frank Ocean',
    'release': 'Blond',
    'title': 'Pretty Sweet',
    'additional_info': {
        'key1': 'Value1',
        'track_number': '5/12',
        'duration': 50000,
    },
    'recording_mbid': "5465ca86-3881-4349-81b2-6efbd3a59451"
}

recording2 = {
    'artist': 'FRANK OCEAN',
    'release': 'BLoNd',
    'title': 'PReTtY SWEET',
    'additional_info': {
        'key1': 'VaLue1',
        'track_number': '5/12',
        'duration': 50000
    },
    'recording_mbid': "5465ca86-3881-4349-81b2-6efbd3a59451"
}


class DataTestCase(TimescaleTestCase):

    def test_submit_recording(self):
        with timescale.engine.begin() as connection:
            title, artist, release, track_number, duration = \
                recording["title"], recording["artist"], recording["release"],\
                recording["additional_info"]["track_number"], recording["additional_info"]["duration"]
            recording_msid = messybrainz.submit_recording(connection, title, artist, release, track_number, duration)
            received_msid_1 = messybrainz.get_msid(connection, title, artist, release, track_number, duration)
            self.assertEqual(recording_msid, received_msid_1)

            # now test a listen with only partial data and check that a different msid is assigned from before

            recording_msid_2 = messybrainz.submit_recording(connection, title, artist, release)
            received_msid_2 = messybrainz.get_msid(connection, title, artist, release)
            self.assertEqual(recording_msid_2, received_msid_2)

            self.assertNotEqual(received_msid_1, received_msid_2)

    def test_add_recording_different_cases(self):
        """ Tests that recordings with only case differences get the same MessyBrainz ID.
        """
        with timescale.engine.begin() as connection:
            title1, artist1, release1, track_number1, duration1 = \
                recording["title"], recording["artist"], recording["release"], \
                recording["additional_info"]["track_number"], recording["additional_info"]["duration"]
            title2, artist2, release2, track_number2, duration2 = \
                recording2["title"], recording2["artist"], recording2["release"], \
                recording2["additional_info"]["track_number"], recording2["additional_info"]["duration"]
            msid1 = messybrainz.submit_recording(connection, title1, artist1, release1, track_number1, duration1)
            msid2 = messybrainz.get_msid(connection, title2, artist2, release2, track_number2, duration2)
            self.assertEqual(msid1, msid2)

    def test_load_recordings_from_msids(self):
        with timescale.engine.begin() as connection, connection.connection.cursor(cursor_factory=DictCursor) as curs:
            title, artist, release = recording["title"], recording["artist"], recording["release"]
            recording_msid = messybrainz.submit_recording(connection, title, artist, release)
            result = messybrainz.load_recordings_from_msids(curs, [recording_msid])
            self.assertDictEqual(result, {
                recording_msid: {
                    "msid": recording_msid,
                    "title": title,
                    "artist": artist,
                    "release": release,
                    "duration": None,
                    "track_number": None
                }
            })

    def test_get_msid_duplicates(self):
        """ Test that in case of duplicates the earliest submitted msid is returned """
        with timescale.engine.begin() as connection:
            args = {
                "msid1": "0becc74d-9ba9-44c5-afa4-2f4ffe380d67",
                "msid2": "9b750fdd-222e-4500-a22e-a0a942d5e342",
                "recording": "05 Mentira ...",
                "artist_credit": "Manu Chao",
                "release": "Clandestino",
                "submitted1": datetime.now(),
                "submitted2": datetime.now() + timedelta(days=1)
            }
            connection.execute(text("""
                INSERT INTO messybrainz.submissions (gid, recording, artist_credit, release, submitted)
                     VALUES (:msid1, :recording, :artist_credit, :release, :submitted1),
                            (:msid2, :recording, :artist_credit, :release, :submitted2)
            """), args)

            received_msid = messybrainz.get_msid(connection, args["recording"], args["artist_credit"], args["release"])
            self.assertEqual(args["msid1"], received_msid)

    def test_insert_all_in_transaction(self):
        submissions: list[dict] = [
            {
                'artist': 'Frank Ocean',
                'release': 'Blond',
                'title': 'Pretty Sweet'
            },
            {
                'artist': 'Frank Ocean',
                'release': 'Blond',
                'title': 'Pretty Sweet',
                'track_number': '5/12',
                'duration': 56000
            }
        ]
        msids = messybrainz.insert_all_in_transaction(self.ts_conn, submissions)
        with self.ts_conn.connection.cursor(cursor_factory=DictCursor) as curs:
            received = messybrainz.load_recordings_from_msids(curs, msids)

        submissions[0]['track_number'] = None
        submissions[0]['duration'] = None
        submissions[0]['msid'] = msids[0]
        submissions[1]['msid'] = msids[1]

        expected = {
            msids[0]: submissions[0],
            msids[1]: submissions[1]
        }

        self.assertDictEqual(expected, received)
