from unittest.mock import patch

import flask_testing
from datasethoster.main import create_app
from listenbrainz.labs_api.labs.api.artist_country_from_artist_credit_id import ArtistCountryFromArtistCreditIdQuery


json_request = [
    {
        "[artist_credit_id]": 810828
    },
    {
        "[artist_credit_id]": 2925190
    }
]

json_response = [
    {
        "area_id": 221,
        'artist_credit_id': 810828,
        "artist_mbid": "0383dadf-2a4e-4d10-a46a-e9e041da8eb3",
        "country_code": "GB"
    },
    {
        "area_id": 221,
        'artist_credit_id': 810828,
        "artist_mbid": "5441c29d-3602-4898-b1a1-b77fa23b8e50",
        "country_code": "GB"
    },
    {
        "area_id": 67,
        'artist_credit_id': 2925190,
        "artist_mbid": "21e7faaf-2540-47d1-99a1-496b69081818",
        "country_code": "EE"
    },
    {
        "area_id": 72,
        'artist_credit_id': 2925190,
        "artist_mbid": "318e7af0-a6b5-44f3-b7d9-b5d33a377b99",
        "country_code": "FI"
    }
]

area_response = [
    {'artist_credit_id': 810828, 'artist_mbid': '0383dadf-2a4e-4d10-a46a-e9e041da8eb3', 'area_id': 221, 'country_code': 'GB'},
    {'artist_credit_id': 810828, 'artist_mbid': '5441c29d-3602-4898-b1a1-b77fa23b8e50', 'area_id': 221, 'country_code': 'GB'},
    {'artist_credit_id': 2925190, 'artist_mbid': '21e7faaf-2540-47d1-99a1-496b69081818', 'area_id': 67, 'country_code': 'EE'},
    {'artist_credit_id': 2925190, 'artist_mbid': '318e7af0-a6b5-44f3-b7d9-b5d33a377b99', 'area_id': 72, 'country_code': 'FI'}
]

country_response = [
    {'area': 221, 'country_code': 'GB'},
    {'area': 67, 'country_code': 'EE'},
    {'area': 72, 'country_code': 'FI'}
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
        q = ArtistCountryFromArtistCreditIdQuery()
        self.assertEqual(q.names()[0], "artist-country-code-from-artist-credit-id")
        self.assertEqual(q.names()[1], "MusicBrainz Artist Country From Artist Credit Id")
        self.assertNotEqual(q.introduction(), "")
        self.assertEqual(q.inputs(), ['[artist_credit_id]'])
        self.assertEqual(q.outputs(), ['artist_credit_id', 'artist_mbid', 'country_code'])

    @patch('psycopg2.connect')
    def test_fetch(self, mock_connect):
        mock_connect().__enter__().cursor().__enter__().fetchone.side_effect = [
            area_response[0],
            area_response[1],
            area_response[2],
            area_response[3],
            None,
            country_response[0],
            country_response[1],
            country_response[2],
            None
        ]
        q = ArtistCountryFromArtistCreditIdQuery()
        resp = q.fetch(json_request)
        self.assertEqual(resp, json_response)
        self.assertEqual(len(resp), 4)

    @patch('psycopg2.connect')
    def test_count(self, mock_connect):
        mock_connect().__enter__().cursor().__enter__().fetchone.side_effect = [
            area_response[0],
            None,
            country_response[0],
            None
        ]
        q = ArtistCountryFromArtistCreditIdQuery()
        resp = q.fetch(json_request, count=1)
        self.assertEqual(len(resp), 1)
        self.assertEqual(resp[0], json_response[0])

    @patch('psycopg2.connect')
    def test_offset(self, mock_connect):
        mock_connect().__enter__().cursor().__enter__().fetchone.side_effect = [
            area_response[1],
            None,
            country_response[0],
            None
        ]
        q = ArtistCountryFromArtistCreditIdQuery()
        resp = q.fetch(json_request, offset=1)
        self.assertEqual(len(resp), 1)
        self.assertEqual(resp[0], json_response[1])
