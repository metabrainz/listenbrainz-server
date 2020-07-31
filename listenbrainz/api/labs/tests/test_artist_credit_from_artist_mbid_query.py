import os
import unittest
from unittest.mock import patch, call

import flask_testing
import flask
import psycopg2
from datasethoster.main import app
from listenbrainz.api.labs.api.artist_credit_from_artist_mbid import ArtistCreditIdFromArtistMBIDQuery

json_request = [
    {
        "artist_mbid": "8f6bd1e4-fbe1-4f50-aa9b-94c450ec0f11"
    }
]

json_response = {
    "artist_credit_ids": [ 2751078, 2666208, 2570655 ],
    "artist_mbid": "8f6bd1e4-fbe1-4f50-aa9b-94c450ec0f11"
}

class MainTestCase(flask_testing.TestCase):

    def create_app(self):
        app.config['DB_CONNECT_MB'] = 'yermom'
        return app

    def setUp(self):
        flask_testing.TestCase.setUp(self)

    def tearDown(self):
        flask_testing.TestCase.tearDown(self)

    def test_basics(self):
        q = ArtistCreditIdFromArtistMBIDQuery()
        self.assertEqual(q.names()[0], "artist-credit-from-artist-mbid")
        self.assertEqual(q.names()[1], "MusicBrainz Artist Credit From Artist MBID")
        self.assertNotEqual(q.introduction(), "")
        self.assertEqual(q.inputs(), ['artist_mbid'])
        self.assertEqual(q.outputs(), ['artist_mbid', 'artist_credit_id'])

    @patch('psycopg2.connect')
    def test_fetch(self, connect):

        connect.cursor.return_value.fetchone.return_value = json_response
        q = ArtistCreditIdFromArtistMBIDQuery()
        resp = q.fetch(json_request)
        self.assertEqual(q.fetch(json_request), json_response)
