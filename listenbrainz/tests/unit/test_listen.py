import unittest
from listenbrainz.listen import Listen
from datetime import datetime
import time
import uuid
import orjson

class ListenTestCase(unittest.TestCase):

    def test_from_timescale(self):
        """ Test for the from_timescale method """

        timescale_row = {
            "listened_at": 1525557084,
            "created": 1525557084,
            "user_name": "iliekcomputers",
            "user_id": 1,
            "recording_msid": "db9a7483-a8f4-4a2c-99af-c8ab58850200",
            "track_metadata": {
                "track_name": "Every Step Every Way",
                "artist_name": "Majid Jordan",
                "release_name": "Majid Jordan",
                "additional_info": {
                    "artist_mbids": ["abaa7001-0d80-4e58-be5d-d2d246fd9d87"],
                    'release_mbid': '8294645a-f996-44b6-9060-7f189b9f59f3',
                    "recording_mbid": None,
                    "tags": ["sing, song"],
                    "best_song": "definitely",
                    "genius_link": "https://genius.com/Majid-jordan-every-step-every-way-lyrics",
                    "lastfm_link": "https://www.last.fm/music/Majid+Jordan/_/Every+Step+Every+Way",
                    "other_stuff": "teststuffplsignore",
                    "we_dict_now.hello": "afb",
                    "we_dict_now.we_nested_now.hi": "312"
                }
            }
        }

        listen = Listen.from_timescale(**timescale_row)

        # Check user name
        self.assertEqual(listen.user_name, timescale_row['user_name'])

        # Check time stamp
        ts = timescale_row['listened_at']
        self.assertEqual(listen.ts_since_epoch, ts)

        # Check artist mbids
        self.assertEqual(listen.data['additional_info']['artist_mbids'], timescale_row['track_metadata']['additional_info']['artist_mbids'])

        # Check tags
        self.assertEqual(listen.data['additional_info']['tags'], timescale_row['track_metadata']['additional_info']['tags'])

        # Check track name
        self.assertEqual(listen.data['track_name'], timescale_row['track_metadata']['track_name'])

        # Check additional info
        self.assertEqual(listen.data['additional_info']['best_song'], timescale_row['track_metadata']['additional_info']['best_song'])

        self.assertEqual(listen.data['track_name'], timescale_row['track_metadata']['track_name'])

        # make sure additional info does not contain stuff like artist names, track names
        self.assertNotIn('track_name', listen.data['additional_info'])
        self.assertNotIn('artist_name', listen.data['additional_info'])
        self.assertNotIn('release_name', listen.data['additional_info'])

    def test_to_timescale(self):
        listen = Listen(
            timestamp=int(time.time()),
            user_name='testuser',
            user_id=1,
            recording_msid=str(uuid.uuid4()),
            data={
                'artist_name': 'Radiohead',
                'track_name': 'True Love Waits',
                'additional_info': {
                    'release_type': ["ALBUM", "REMIX"],
                }
            }
        )

        listened_at, user_id, recording_msid, data = listen.to_timescale()

        # Check data is of type string
        self.assertIsInstance(data, str)

        # Convert returned data to json
        json_data = orjson.loads(data)

        # Check that the required fields are dumped into data
        self.assertIn('additional_info', json_data)

        # Check that the required fields are dumped into data
        self.assertEqual(listened_at, listen.timestamp)
        self.assertEqual(recording_msid, listen.recording_msid)
        self.assertEqual(user_id, listen.user_id)
        self.assertEqual(json_data['artist_name'], listen.data['artist_name'])

    def test_from_json(self):
        json_row = {"track_metadata": {"additional_info": {}}}

        json_row.update({'listened_at': 123456})
        listen = Listen.from_json(json_row)

        self.assertEqual(listen.timestamp, json_row['listened_at'])
