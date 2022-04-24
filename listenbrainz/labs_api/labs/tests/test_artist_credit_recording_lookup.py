from unittest.mock import patch

import flask_testing
from datasethoster.main import create_app
from listenbrainz.labs_api.labs.api.artist_credit_recording_lookup import ArtistCreditRecordingLookupQuery


json_request = [
    {
        "[artist_credit_name]": "portishead",
        "[recording_name]": "strangers"
    },
    {
        "[artist_credit_name]": "morcheeba",
        "[recording_name]": "trigger hippie"
    },
    {
        "[artist_credit_name]": "Reo's mum",
        "[recording_name]": "is never going to be found."
    }
]

db_response = [
    {
        "artist_credit_id": 963,
        "artist_mbids": ['067102ea-9519-4622-9077-57ca4164cfbb'],
        "artist_credit_name": "Morcheeba",
        "combined_lookup": "morcheebatriggerhippie",
        "recording_mbid": "97e69767-5d34-4c97-b36a-f3b2b1ef9dae",
        "recording_name": "Trigger Hippie",
        "release_mbid": "9db51cd6-38f6-3b42-8ad5-559963d68f35",
        "release_name": "Who Can You Trust?",
        "year": 1996
    },
    {
        "artist_credit_id": 65,
        "artist_credit_name": "Portishead",
        "artist_mbids": ['8f6bd1e4-fbe1-4f50-aa9b-94c450ec0f11'],
        "combined_lookup": "portisheadstrangers",
        "recording_mbid": "e97f805a-ab48-4c52-855e-07049142113d",
        "recording_name": "Strangers",
        "release_mbid": "76df3287-6cda-33eb-8e9a-044b5e15ffdd",
        "release_name": "Dummy",
        "year": 1995
    }

]

json_response = [
    {
        "artist_credit_arg": "morcheeba",
        "artist_credit_id": 963,
        "artist_mbids": ['067102ea-9519-4622-9077-57ca4164cfbb'],
        "artist_credit_name": "Morcheeba",
        "combined_lookup": "morcheebatriggerhippie",
        "index": 1,
        "recording_arg": "trigger hippie",
        "recording_mbid": "97e69767-5d34-4c97-b36a-f3b2b1ef9dae",
        "recording_name": "Trigger Hippie",
        "release_mbid": "9db51cd6-38f6-3b42-8ad5-559963d68f35",
        "release_name": "Who Can You Trust?",
        "year": 1996
    },
    {
        "artist_credit_arg": "portishead",
        "artist_credit_id": 65,
        "artist_mbids": ['8f6bd1e4-fbe1-4f50-aa9b-94c450ec0f11'],
        "artist_credit_name": "Portishead",
        "combined_lookup": "portisheadstrangers",
        "index": 0,
        "recording_arg": "strangers",
        "recording_mbid": "e97f805a-ab48-4c52-855e-07049142113d",
        "recording_name": "Strangers",
        "release_mbid": "76df3287-6cda-33eb-8e9a-044b5e15ffdd",
        "release_name": "Dummy",
        "year": 1995
    }
]


class MainTestCase(flask_testing.TestCase):

    def create_app(self):
        app = create_app()
        app.config['MB_DATABASE_URI'] = 'yermom'
        return app

    def setUp(self):
        flask_testing.TestCase.setUp(self)

    def tearDown(self):
        flask_testing.TestCase.tearDown(self)

    def test_basics(self):
        q = ArtistCreditRecordingLookupQuery()
        self.assertEqual(q.names()[0], "acr-lookup")
        self.assertEqual(
            q.names()[1], "MusicBrainz Artist Credit Recording lookup")
        self.assertNotEqual(q.introduction(), "")
        self.assertEqual(
            q.inputs(), ['[artist_credit_name]', '[recording_name]'])
        self.assertEqual(q.outputs(), ['index', 'artist_credit_arg', 'recording_arg',
                                       'artist_credit_name', 'release_name', 'recording_name',
                                       'artist_credit_id', 'artist_mbids', 'release_mbid', 'recording_mbid', 'year'])

    @patch('psycopg2.connect')
    def test_fetch(self, mock_connect):
        mock_connect().__enter__().cursor().__enter__().fetchone.side_effect = [
            db_response[0], db_response[1], None]
        q = ArtistCreditRecordingLookupQuery()
        resp = q.fetch(json_request)
        self.assertDictEqual(resp[0], json_response[0])
        self.assertDictEqual(resp[1], json_response[1])
        self.assertEqual(len(resp), 2)
