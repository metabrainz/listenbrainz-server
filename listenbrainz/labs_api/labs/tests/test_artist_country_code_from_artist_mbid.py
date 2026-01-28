from unittest.mock import patch

import flask_testing
from datasethoster import RequestSource
from datasethoster.main import create_app
from listenbrainz.labs_api.labs.api.artist_country_from_artist_mbid import ArtistCountryFromArtistMBIDQuery, \
    ArtistCountryFromArtistMBIDInput, ArtistCountryFromArtistMBIDOutput

json_request = [
    ArtistCountryFromArtistMBIDInput(artist_mbid="8f6bd1e4-fbe1-4f50-aa9b-94c450ec0f11"),
    ArtistCountryFromArtistMBIDInput(artist_mbid="164f0d73-1234-4e2c-8743-d77bf2191051"),
]

json_response = [
    ArtistCountryFromArtistMBIDOutput(
        artist_mbid="164f0d73-1234-4e2c-8743-d77bf2191051",
        artist_name="Kanye West",
        country_code="US",
        area_id=5099
    ),
    ArtistCountryFromArtistMBIDOutput(
        artist_mbid="8f6bd1e4-fbe1-4f50-aa9b-94c450ec0f11",
        artist_name="Portishead",
        country_code="GB",
        area_id=221
    )
]

area_response = [
    {'artist_mbid': '164f0d73-1234-4e2c-8743-d77bf2191051', "artist_name": 'Kanye West', 'area_id': 5099, 'country_code': None},
    {'artist_mbid': '8f6bd1e4-fbe1-4f50-aa9b-94c450ec0f11', "artist_name": 'Portishead', 'area_id': 221, 'country_code': 'GB'}
]

country_response = [
    {'area': 5099, 'country_code': 'US'}
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
        q = ArtistCountryFromArtistMBIDQuery()
        self.assertEqual(q.names()[0], "artist-country-code-from-artist-mbid")
        self.assertEqual(q.names()[1], "MusicBrainz Artist Country From Artist MBID")
        self.assertNotEqual(q.introduction(), "")
        self.assertCountEqual(q.inputs().__fields__.keys(), ['artist_mbid'])
        self.assertCountEqual(q.outputs().__fields__.keys(), ['artist_mbid', 'artist_name', 'area_id', 'country_code'])

    @patch('psycopg2.connect')
    def test_fetch(self, mock_connect):
        mock_connect().__enter__().cursor().__enter__().fetchone.side_effect = [
            area_response[0],
            area_response[1],
            None,
            country_response[0],
            None
        ]
        q = ArtistCountryFromArtistMBIDQuery()
        resp = q.fetch(json_request, RequestSource.json_post)
        self.assertEqual(resp, json_response)
        self.assertEqual(len(resp), 2)

    @patch('psycopg2.connect')
    def test_count(self, mock_connect):
        mock_connect().__enter__().cursor().__enter__().fetchone.side_effect = [
            area_response[0],
            None,
            country_response[0],
            None
        ]
        q = ArtistCountryFromArtistMBIDQuery()
        resp = q.fetch(json_request, RequestSource.json_post, count=1)
        self.assertEqual(len(resp), 1)
        self.assertEqual(resp[0].dict(), json_response[0])

    @patch('psycopg2.connect')
    def test_offset(self, mock_connect):
        mock_connect().__enter__().cursor().__enter__().fetchone.side_effect = [
            area_response[1],
            None,
            country_response[0],
            None
        ]
        q = ArtistCountryFromArtistMBIDQuery()
        resp = q.fetch(json_request, RequestSource.json_post, offset=1)
        self.assertEqual(len(resp), 1)
        self.assertEqual(resp[0].dict(), json_response[1])
