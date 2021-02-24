from unittest.mock import patch

import flask_testing
from datasethoster.main import create_app
from listenbrainz.labs_api.labs.api.year_from_artist_credit_recording import YearFromArtistCreditRecordingQuery


json_request = [
    {
        "[artist_credit_name]": "Portishead",
        "[recording_name]": "Strangers"
    },
    {
        "[artist_credit_name]": "Rick Astley",
        "[recording_name]": "Never let you down"
    },
    {
        "[artist_credit_name]": "morcheeba",
        "[recording_name]": "trigger hippie"
    }
]

json_response = [
  {
    "artist_credit_name": "Portishead",
    "recording_name": "Strangers",
    "year": 1994
  },
  {
    "artist_credit_name": "Rick Astley",
    "recording_name": "Never let you down",
    "year": 1987
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
        q = YearFromArtistCreditRecordingQuery()
        self.assertEqual(q.names()[0], "year-artist-recording-year-lookup")
        self.assertEqual(q.names()[1], "MusicBrainz Recording Year lookup")
        self.assertNotEqual(q.introduction(), "")
        self.assertEqual(q.inputs(), ['[artist_credit_name]', '[recording_name]'])
        self.assertEqual(q.outputs(), ['artist_credit_name', 'recording_name', 'year'])

    @patch('psycopg2.connect')
    def test_fetch(self, mock_connect):
        mock_connect().__enter__().cursor().__enter__().fetchone.side_effect = [json_response[0], json_response[1], None]
        q = YearFromArtistCreditRecordingQuery()
        resp = q.fetch(json_request)
        self.assertEqual(len(resp), 2)
        self.assertDictEqual(resp[0], json_response[0])
        self.assertDictEqual(resp[1], json_response[1])
