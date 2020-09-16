import os
import unittest
from unittest.mock import patch, call, MagicMock

import flask_testing
import flask
import psycopg2
from datasethoster.main import app
from listenbrainz.labs_api.labs.api.artist_credit_from_artist_msid import ArtistCreditIdFromArtistMSIDQuery


json_request = [
    {
        "artist_msid": "ea7e58c9-949d-4843-a869-6a93b96ae786"
    },
    {
        "artist_msid": "9c1d9739-e40a-47b8-b3be-8076344e51ed"
    }
]

json_data = [
    {
        "artist_credit_mbid": [ "51ed973d-95c7-4a12-a11c-8c8581a5872a" ],
        "artist_msid": "ea7e58c9-949d-4843-a869-6a93b96ae786",
        "artist_credit_id": 129493,
        "artist_credit_name": "Frank Reyes",
        "artist_msid": "ea7e58c9-949d-4843-a869-6a93b96ae786"
    },
    {
        "artist_credit_mbid": [ "0383dadf-2a4e-4d10-a46a-e9e041da8eb3","5441c29d-3602-4898-b1a1-b77fa23b8e50"],
        "artist_msid": "9c1d9739-e40a-47b8-b3be-8076344e51ed",
        "artist_credit_id": 810828,
        "artist_credit_name": "Queen & David Bowie",
        "artist_msid": "9c1d9739-e40a-47b8-b3be-8076344e51ed"
    }
]
json_response = [
    {
        "[artist_credit_mbid]": [
            "51ed973d-95c7-4a12-a11c-8c8581a5872a"
        ],
        "artist_msid": "ea7e58c9-949d-4843-a869-6a93b96ae786",
        "artist_credit_id": 129493,
        "artist_credit_name": "Frank Reyes",
        "artist_msid": "ea7e58c9-949d-4843-a869-6a93b96ae786"
    },
    {
        "[artist_credit_mbid]": [
            "0383dadf-2a4e-4d10-a46a-e9e041da8eb3",
            "5441c29d-3602-4898-b1a1-b77fa23b8e50"
        ],
        "artist_msid": "9c1d9739-e40a-47b8-b3be-8076344e51ed",
        "artist_credit_id": 810828,
        "artist_credit_name": "Queen & David Bowie",
        "artist_msid": "9c1d9739-e40a-47b8-b3be-8076344e51ed"
    }
]


class MainTestCase(flask_testing.TestCase):

    def create_app(self):
        app.config['DB_CONNECT_MAPPING'] = 'yermom'
        return app

    def setUp(self):
        flask_testing.TestCase.setUp(self)

    def tearDown(self):
        flask_testing.TestCase.tearDown(self)

    def test_basics(self):
        q = ArtistCreditIdFromArtistMSIDQuery()
        self.assertEqual(q.names()[0], "artist-credit-from-artist-msid")
        self.assertEqual(q.names()[1], "MusicBrainz Artist Credit From Artist MSID")
        self.assertNotEqual(q.introduction(), "")
        self.assertEqual(q.inputs(), ['artist_msid'])
        self.assertEqual(q.outputs(), ['artist_msid', 'artist_credit_id', '[artist_credit_mbid]', 'artist_credit_name'])

    @patch('psycopg2.connect')
    def test_fetch(self, mock_connect):
        mock_connect().__enter__().cursor().__enter__().fetchone.side_effect = [json_data[0], json_data[1], None]
        q = ArtistCreditIdFromArtistMSIDQuery()
        resp = q.fetch(json_request)
        self.assertEqual(len(resp), 2)
        self.assertDictEqual(resp[0], json_response[0])
        self.assertDictEqual(resp[1], json_response[1])

    @patch('psycopg2.connect')
    def test_count(self, mock_connect):
        mock_connect().__enter__().cursor().__enter__().fetchone.side_effect = [json_data[0], None]
        q = ArtistCreditIdFromArtistMSIDQuery()
        resp = q.fetch(json_request, count=1)
        self.assertEqual(len(resp), 1)
        self.assertDictEqual(resp[0], json_response[0])

    @patch('psycopg2.connect')
    def test_offset(self, mock_connect):
        mock_connect().__enter__().cursor().__enter__().fetchone.side_effect = [json_data[1], None]
        q = ArtistCreditIdFromArtistMSIDQuery()
        resp = q.fetch(json_request, offset=1)
        self.assertEqual(len(resp), 1)
        self.assertDictEqual(resp[0], json_response[1])
