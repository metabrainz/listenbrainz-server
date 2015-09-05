from db.testing import DatabaseTestCase, TEST_DATA_PATH
from db import data
import os.path
import json


class DataTestCase(DatabaseTestCase):

    def setUp(self):
        super(DataTestCase, self).setUp()
        self.test_mbid = "0dad432b-16cc-4bf0-8961-fd31d124b01b"
        self.test_lowlevel_data_json = open(os.path.join(TEST_DATA_PATH, self.test_mbid + '.json')).read()
        self.test_lowlevel_data = json.loads(self.test_lowlevel_data_json)

    def test_submit_low_level_data(self):
        data.submit_low_level_data(self.test_mbid, self.test_lowlevel_data)
        self.assertIsNotNone(data.load_low_level(self.test_mbid))

    def test_has_key(self):
        dictionary = {
            'test_1': {
                'inner_test': {
                    'secret_test_1': 'Hey there!',
                    'secret_test_2': 'Bye!',
                },
            },
            'test_2': 'Testing!',
        }

        self.assertTrue(data._has_key(dictionary, ['test_1', 'inner_test']))
        self.assertTrue(data._has_key(dictionary, ['test_1', 'inner_test', 'secret_test_2']))
        self.assertTrue(data._has_key(dictionary, ['test_2']))

        self.assertFalse(data._has_key(dictionary, ['test_3']))
        self.assertFalse(data._has_key(dictionary, ['test_1', 'inner_test', 'secret_test_3']))

    def test_sanity_check_data(self):
        d = {
            "metadata": {
                "audio_properties": {
                    "bit_rate": 253569,
                    "codec": "mp3",
                    "length": 280.685699463,
                    "lossless": False,
                },
                "tags": {
                    "file_name": "example.mp3",
                    "musicbrainz_recordingid": ["8c12af5a-f9a2-42fa-9dbe-032d7a1f4d5b"],
                },
                "version": {
                    "essentia": "2.1-beta2",
                    "essentia_build_sha": "26c37b627ab5a2028d412893e0969599b764ad4d",
                    "essentia_git_sha": "v2.1_beta2",
                    "extractor": "music 1.0"
                }
            },
            "lowlevel": None,
            "rhythm": None,
            "tonal": None,
        }
        self.assertIsNone(data.sanity_check_data(d))
        del d['metadata']['tags']['file_name']
        self.assertEquals(data.sanity_check_data(d), ['metadata', 'tags', 'file_name'])

    def test_clean_metadata(self):
        d = {
            "metadata": {
                "tags": {
                    "file_name": "example.mp3",
                    "musicbrainz_recordingid": ["8c12af5a-f9a2-42fa-9dbe-032d7a1f4d5b"],
                    "unknown_tag": "Hello! I am an unknown tag!",
                },
            },
        }
        data.clean_metadata(d)
        self.assertFalse('unknown_tag' in d['metadata']['tags'])
        self.assertTrue('file_name' in d['metadata']['tags'])
