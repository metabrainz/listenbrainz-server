import unittest
from listenbrainz.listen import Listen
from datetime import datetime
import time
import uuid


class ListenTestCase(unittest.TestCase):

    def test_from_timescale(self):
        """ Test for the from_timescale method """

        timescale_row = {
            "listened_at": 1525557084,
            "user_name": "iliekcomputers",
            "recording_msid": "db9a7483-a8f4-4a2c-99af-c8ab58850200",
            "data": {
                'track_metadata': {
                    "track_name": "Every Step Every Way",
                    "artist_name": "Majid Jordan",
                    "release_name": "Majid Jordan",
                    'additional_info': {
                        "artist_msid": "aa6130f2-a12d-47f3-8ffd-d0f71340de1f",
                        "artist_mbids": ["abaa7001-0d80-4e58-be5d-d2d246fd9d87"],
                        "release_msid": "cf138a00-05d5-4b35-8fce-181efcc15785",
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
                },
                "user_id": 1
            }
        }

        listen = Listen.from_timescale(
            timescale_row['listened_at'], timescale_row['recording_msid'], timescale_row['user_name'], timescale_row['data'])

        # Check user name
        self.assertEqual(listen.user_name, timescale_row['user_name'])

        # Check time stamp
        ts = timescale_row['listened_at']
        self.assertEqual(listen.ts_since_epoch, ts)

        # Check artist mbids
        self.assertEqual(listen.data['additional_info']['artist_mbids'],
                         timescale_row['data']['track_metadata']['additional_info']['artist_mbids'])

        # Check tags
        self.assertEqual(listen.data['additional_info']['tags'], timescale_row['data']
                         ['track_metadata']['additional_info']['tags'])

        # Check track name
        self.assertEqual(listen.data['track_name'], timescale_row['data']
                         ['track_metadata']['track_name'])

        # Check additional info
        self.assertEqual(listen.data['additional_info']['best_song'],
                         timescale_row['data']['track_metadata']['additional_info']['best_song'])

        # Check msids
        self.assertEqual(
            listen.artist_msid, timescale_row['data']['track_metadata']['additional_info']['artist_msid'])
        self.assertEqual(
            listen.release_msid, timescale_row['data']['track_metadata']['additional_info']['release_msid'])
        self.assertEqual(listen.recording_msid, timescale_row['recording_msid'])

        # make sure additional info does not contain stuff like artist names, track names
        self.assertNotIn('track_name', listen.data['additional_info'])
        self.assertNotIn('artist_name', listen.data['additional_info'])
        self.assertNotIn('release_name', listen.data['additional_info'])

    def test_to_timescale(self):
        listen = Listen(
            timestamp=int(time.time()),
            user_name='testuser',
            artist_msid=uuid.uuid4(),
            recording_msid=uuid.uuid4(),
            dedup_tag=3,
            data={
                'artist_name': 'Radiohead',
                'track_name': 'True Love Waits',
                'additional_info': {
                    'release_type': ["ALBUM", "REMIX"],
                }
            }
        )

        data = listen.to_timescale(listen)

        # Make sure every value that we don't explicitly support is a string
        for key in data['fields']:
            if key not in Listen.SUPPORTED_KEYS and key not in Listen.PRIVATE_KEYS:
                self.assertIsInstance(data['fields'][key], str)

        # Check values
        self.assertEqual(data['measurement'], listen.user_name)
        self.assertEqual(data['time'], listen.ts_since_epoch)
        self.assertEqual(data['tags']['dedup_tag'], listen.dedup_tag)
        self.assertEqual(data['fields']['user_name'], listen.user_name)
        self.assertEqual(data['fields']['artist_msid'], listen.artist_msid)
        self.assertEqual(data['fields']['recording_msid'], listen.recording_msid)
        self.assertEqual(data['fields']['track_name'], listen.data['track_name'])
        self.assertEqual(data['fields']['artist_name'], listen.data['artist_name'])

        self.assertIn('inserted_timestamp', data['fields'])


    def test_from_json(self):
        json_row = {
                    "track_metadata": {
                      "additional_info": {}
                      }
                    }

        json_row.update({'listened_at': 123456})
        listen = Listen.from_json(json_row) 

        self.assertEqual(listen.timestamp, json_row['listened_at'])

        del json_row['listened_at']
        json_row.update({'playing_now': True})
        listen = Listen.from_json(json_row)

        self.assertEqual(listen.timestamp, None)
