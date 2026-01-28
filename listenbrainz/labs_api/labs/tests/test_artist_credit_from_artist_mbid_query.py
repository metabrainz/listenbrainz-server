from unittest.mock import patch

import flask_testing
from datasethoster import RequestSource
from datasethoster.main import create_app
from listenbrainz.labs_api.labs.api.artist_credit_from_artist_mbid import ArtistCreditIdFromArtistMBIDQuery, \
    ArtistCreditIdFromArtistMBIDInput, ArtistCreditIdFromArtistMBIDOutput

json_request = [
    ArtistCreditIdFromArtistMBIDInput(artist_mbid="8f6bd1e4-fbe1-4f50-aa9b-94c450ec0f11"),
    ArtistCreditIdFromArtistMBIDInput(artist_mbid="a3cb23fc-acd3-4ce0-8f36-1e5aa6a18432")
]

json_response = [
    ArtistCreditIdFromArtistMBIDOutput(
        artist_credit_id=[65, 816454, 2666208],
        artist_mbid="8f6bd1e4-fbe1-4f50-aa9b-94c450ec0f11"
    ),
    ArtistCreditIdFromArtistMBIDOutput(
        artist_credit_id=[197, 883396, 883398],
        artist_mbid="a3cb23fc-acd3-4ce0-8f36-1e5aa6a18432"
    )
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
        q = ArtistCreditIdFromArtistMBIDQuery()
        self.assertEqual(q.names()[0], "artist-credit-from-artist-mbid")
        self.assertEqual(q.names()[1], "MusicBrainz Artist Credit From Artist MBID")
        self.assertNotEqual(q.introduction(), "")
        self.assertCountEqual(q.inputs().__fields__.keys(), ['artist_mbid'])
        self.assertCountEqual(q.outputs().__fields__.keys(), ['artist_mbid', 'artist_credit_id'])

    @patch('psycopg2.connect')
    def test_fetch(self, mock_connect):
        mock_connect().__enter__().cursor().__enter__().fetchone.side_effect = [json_response[0], json_response[1], None]
        q = ArtistCreditIdFromArtistMBIDQuery()
        resp = q.fetch(json_request, RequestSource.json_post)
        self.assertEqual(resp[0].dict(), json_response[0])
        self.assertEqual(resp[1].dict(), json_response[1])
        self.assertEqual(len(resp), 2)

    @patch('psycopg2.connect')
    def test_count(self, mock_connect):
        mock_connect().__enter__().cursor().__enter__().fetchone.side_effect = [json_response[0], None]
        q = ArtistCreditIdFromArtistMBIDQuery()
        resp = q.fetch(json_request, RequestSource.json_post, count=1)
        self.assertEqual(len(resp), 1)
        self.assertEqual(resp[0].dict(), json_response[0])

    @patch('psycopg2.connect')
    def test_offset(self, mock_connect):
        mock_connect().__enter__().cursor().__enter__().fetchone.side_effect = [json_response[1], None]
        q = ArtistCreditIdFromArtistMBIDQuery()
        resp = q.fetch(json_request, RequestSource.json_post, offset=1)
        self.assertEqual(len(resp), 1)
        self.assertEqual(resp[0].dict(), json_response[1])
