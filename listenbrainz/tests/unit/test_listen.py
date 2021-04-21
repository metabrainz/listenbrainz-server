import unittest
from listenbrainz.listen import Listen
from datetime import datetime
import time
import uuid
import ujson

class ListenTestCase(unittest.TestCase):

    def test_from_timescale(self):
        """ Test for the from_timescale method """

        timescale_row = {
            "listened_at": 1525557084,
            "created": 1525557084,
            "track_name": "Every Step Every Way",
            "user_name": "iliekcomputers",
            "data": {
                'track_metadata': {
                    "artist_name": "Majid Jordan",
                    "release_name": "Majid Jordan",
                    'additional_info': {
                        "artist_msid": "aa6130f2-a12d-47f3-8ffd-d0f71340de1f",
                        "artist_mbids": ["abaa7001-0d80-4e58-be5d-d2d246fd9d87"],
                        "release_msid": "cf138a00-05d5-4b35-8fce-181efcc15785",
                        'release_mbid': '8294645a-f996-44b6-9060-7f189b9f59f3',
                        "recording_mbid": None,
                        "recording_msid": "db9a7483-a8f4-4a2c-99af-c8ab58850200",
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

        listen = Listen.from_timescale(timescale_row['listened_at'],
                                       timescale_row['track_name'],
                                       timescale_row['user_name'],
                                       timescale_row['created'],
                                       timescale_row['data'])

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
        self.assertEqual(listen.data['track_name'], timescale_row['track_name'])

        # make sure additional info does not contain stuff like artist names, track names
        self.assertNotIn('track_name', listen.data['additional_info'])
        self.assertNotIn('artist_name', listen.data['additional_info'])
        self.assertNotIn('release_name', listen.data['additional_info'])

    def test_to_timescale(self):
        listen = Listen(
            timestamp=int(time.time()),
            user_name='testuser',
            artist_msid=str(uuid.uuid4()),
            dedup_tag=3,
            user_id=1,
            data={
                'artist_name': 'Radiohead',
                'track_name': 'True Love Waits',
                'additional_info': {
                    'release_type': ["ALBUM", "REMIX"],
                    'recording_msid': str(uuid.uuid4()),
                }
            }
        )

        listened_at, track_name, user_name, data = listen.to_timescale()

        # Check data is of type string
        self.assertIsInstance(data, str)

        # Convert returned data to json
        json_data = ujson.loads(data)

        # Check that the required fields are dumped into data
        self.assertIn('track_metadata', json_data)
        self.assertIn('additional_info', json_data['track_metadata'])

        # Check that the required fields are dumped into data
        self.assertEqual(listened_at, listen.ts_since_epoch)
        self.assertEqual(track_name, listen.data['track_name'])
        self.assertEqual(user_name, listen.user_name)
        self.assertEqual(json_data['user_id'], listen.user_id)
        self.assertEqual(json_data['track_metadata']['artist_name'], listen.data['artist_name'])

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

    def test_from_json_null_values(self):
        data = {
            "listened_at": 1618353413, "track_metadata": {
                "additional_info": {"recording_mbid": "99e087e1-5649-4e8c-b84f-eea05b8e143a",
                                    "release_mbid": "4b6ca48c-f7db-439d-ba57-6104b5fec61e",
                                    "artist_mbid": "e1564e98-978b-4947-8698-f6fd6f8b0181\u0000\ufeff9ad10546-b081-4cc8-a487-3d2eece82d9e\u0000\ufeff5245e5cd-4408-4d9e-a037-c71a53edce83",
                                    "artist_msid": "392f2883-724f-4c63-b155-81a7cc89a499",
                                    "release_msid": "632207f8-150f-4342-99ad-0fd5a6687e63"},
                "artist_name": "Fort Minor Feat. Holly Brook & Jonah Matranga", "track_name": "some name"}
            }
        with self.assertRaises(ValueError):
            Listen.from_json(data)
