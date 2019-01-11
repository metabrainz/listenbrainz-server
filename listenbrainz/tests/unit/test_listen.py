import unittest
from listenbrainz.listen import Listen
from datetime import datetime
from listenbrainz.utils import quote
import time
import uuid


class ListenTestCase(unittest.TestCase):

    def test_from_influx(self):
        """ Test for the from_influx method """

        influx_row = {
            "time": "2017-06-07T17:23:05Z",
            "artist_mbids": "abaa7001-0d80-4e58-be5d-d2d246fd9d87",
            "artist_msid": "aa6130f2-a12d-47f3-8ffd-d0f71340de1f",
            "artist_name": "Majid Jordan",
            "best_song": "definitely",
            "genius_link": "https://genius.com/Majid-jordan-every-step-every-way-lyrics",
            "lastfm_link": "https://www.last.fm/music/Majid+Jordan/_/Every+Step+Every+Way",
            "other_stuff": "teststuffplsignore",
            "recording_mbid": None,
            "recording_msid": "db9a7483-a8f4-4a2c-99af-c8ab58850200",
            "release_msid": "cf138a00-05d5-4b35-8fce-181efcc15785",
            "release_name": "Majid Jordan",
            "track_name": "Every Step Every Way",
            "user_name": "iliekcomputers",
            "we_dict_now.hello": "afb",
            "we_dict_now.we_nested_now.hi": "312",
            "tags": "sing, song",
            "inserted_timestamp": 1525557084,
        }

        listen = Listen.from_influx(influx_row)

        # Check user name
        self.assertEqual(listen.user_name, influx_row['user_name'])

        # Check time stamp
        dt = datetime.strptime(influx_row['time'] , '%Y-%m-%dT%H:%M:%SZ')
        ts = int(dt.strftime("%s"))
        self.assertEqual(listen.ts_since_epoch, ts)

        # Check artist mbids
        self.assertIsInstance(listen.data['additional_info']['artist_mbids'], list)
        self.assertEqual(listen.data['additional_info']['artist_mbids'], influx_row['artist_mbids'].split(','))

        # Check tags
        self.assertIsInstance(listen.data['additional_info']['tags'], list)
        self.assertEqual(listen.data['additional_info']['tags'], influx_row['tags'].split(','))

        # Check track name
        self.assertEqual(listen.data['track_name'], influx_row['track_name'])

        # Check additional info
        self.assertEqual(listen.data['additional_info']['best_song'], influx_row['best_song'])

        # Check msids
        self.assertEqual(listen.artist_msid, influx_row['artist_msid'])
        self.assertEqual(listen.release_msid, influx_row['release_msid'])
        self.assertEqual(listen.recording_msid, influx_row['recording_msid'])

        # make sure additional info does not contain stuff like artist names, track names
        self.assertNotIn('track_name', listen.data['additional_info'])
        self.assertNotIn('artist_name', listen.data['additional_info'])
        self.assertNotIn('release_name', listen.data['additional_info'])

    def test_to_influx(self):
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

        data = listen.to_influx(quote(listen.user_name))

        # Make sure every value that we don't explicitly support is a string
        for key in data['fields']:
            if key not in Listen.SUPPORTED_KEYS and key not in Listen.PRIVATE_KEYS:
                self.assertIsInstance(data['fields'][key], str)

        # Check values
        self.assertEqual(data['measurement'], quote(listen.user_name))
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