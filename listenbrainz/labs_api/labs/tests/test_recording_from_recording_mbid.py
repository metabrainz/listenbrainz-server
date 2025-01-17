import json
from unittest.mock import patch

import flask_testing
from datasethoster import RequestSource
from datasethoster.main import create_app
from listenbrainz.labs_api.labs.api.recording_from_recording_mbid import RecordingFromRecordingMBIDQuery, \
    RecordingFromRecordingMBIDInput

json_request = [
    RecordingFromRecordingMBIDInput(recording_mbid="a96bf3b6-651d-49f4-9a89-eee27cecc18e"),
    RecordingFromRecordingMBIDInput(recording_mbid="8fa0023e-1268-4d32-8341-83bb7506086e"),
    RecordingFromRecordingMBIDInput(recording_mbid="5948f779-0b96-4eba-b6a7-d1f0f6c7cf9f"),
    RecordingFromRecordingMBIDInput(recording_mbid="a1e97901-7ddf-4a0d-87ff-7f601ad3ccd3"),
]

redirect_db_response = (
    [
        "1234a7ae-2af2-4291-aa84-bd0bafe291a1",
        "8fa0023e-1268-4d32-8341-83bb7506086e",
        "1636e7a9-229d-446d-aa81-e33071b42d7a",
        "a1e97901-7ddf-4a0d-87ff-7f601ad3ccd3"
    ],
    {
        "a96bf3b6-651d-49f4-9a89-eee27cecc18e": "1234a7ae-2af2-4291-aa84-bd0bafe291a1",
        "5948f779-0b96-4eba-b6a7-d1f0f6c7cf9f": "1636e7a9-229d-446d-aa81-e33071b42d7a"
    },
    {
        "1234a7ae-2af2-4291-aa84-bd0bafe291a1": "a96bf3b6-651d-49f4-9a89-eee27cecc18e",
        "1636e7a9-229d-446d-aa81-e33071b42d7a": "5948f779-0b96-4eba-b6a7-d1f0f6c7cf9f"
    }
)

canonical_db_response = [
    [
        "1234a7ae-2af2-4291-aa84-bd0bafe291a1",
        "ec5b8aa9-7483-4791-a185-1f599a0cdc35",
        "1636e7a9-229d-446d-aa81-e33071b42d7a",
        "a1e97901-7ddf-4a0d-87ff-7f601ad3ccd3"
    ],
    {"8fa0023e-1268-4d32-8341-83bb7506086e": "ec5b8aa9-7483-4791-a185-1f599a0cdc35"},
    {"ec5b8aa9-7483-4791-a185-1f599a0cdc35": "8fa0023e-1268-4d32-8341-83bb7506086e"}
]

metadata_db_response = {
    "1234a7ae-2af2-4291-aa84-bd0bafe291a1": {
        "artist_mbids": [
            "8f6bd1e4-fbe1-4f50-aa9b-94c450ec0f11"
        ],
        "artist_credit_id": 65,
        "artist": "Portishead",
        "length": 253000,
        "recording_mbid": "1234a7ae-2af2-4291-aa84-bd0bafe291a1",
        "title": "Sour Times",
        "release_mbid": "76df3287-6cda-33eb-8e9a-044b5e15ffdd",
        "release": "Dummy",
        "artists": [
            {
                "artist_mbid": "8f6bd1e4-fbe1-4f50-aa9b-94c450ec0f11",
                "artist_credit_name": "Portishead",
                "join_phrase": ""
            }
        ],
        "caa_id": None,
        "caa_release_mbid": None
    },
    "1636e7a9-229d-446d-aa81-e33071b42d7a": {
        "artist_mbids": [
            "4e024037-14b7-4aea-99ad-c6ace63b9620"
        ],
        "artist_credit_id": 92381,
        "artist": "Madvillain",
        "length": 111666,
        "recording_mbid": "1636e7a9-229d-446d-aa81-e33071b42d7a",
        "title": "Strange Ways",
        "release_mbid": "94c77483-c110-42d5-8d70-db496dc3deef",
        "release": "Madvillainy",
        "artists": [
            {
                "artist_mbid": "4e024037-14b7-4aea-99ad-c6ace63b9620",
                "artist_credit_name": "Madvillain",
                "join_phrase": ""
            }
        ],
        "caa_id": None,
        "caa_release_mbid": None
    },
    "8fa0023e-1268-4d32-8341-83bb7506086e": {
        "artist_mbids": [
            "31810c40-932a-4f2d-8cfd-17849844e2a6"
        ],
        "artist_credit_id": 11,
        "artist": "Squirrel Nut Zippers",
        "length": 275333,
        "recording_mbid": "8fa0023e-1268-4d32-8341-83bb7506086e",
        "release_mbid": "86b869c6-4a5b-4131-aff1-0edc25e18581",
        "release": "Erna 20: Swing und Blues",
        "title": "Blue Angel",
        "artists": [
            {
                "artist_mbid": "31810c40-932a-4f2d-8cfd-17849844e2a6",
                "artist_credit_name": "Squirrel Nut Zippers",
                "join_phrase": ""
            }
        ],
        "caa_id": None,
        "caa_release_mbid": None
    }
}

json_response = [
    {
        "artist_credit_mbids": [
            "8f6bd1e4-fbe1-4f50-aa9b-94c450ec0f11"
        ],
        "artist_credit_id": 65,
        "artist_credit_name": "Portishead",
        "length": 253000,
        "recording_mbid": "1234a7ae-2af2-4291-aa84-bd0bafe291a1",
        "canonical_recording_mbid": "1234a7ae-2af2-4291-aa84-bd0bafe291a1",
        "recording_name": "Sour Times",
        "release_mbid": "76df3287-6cda-33eb-8e9a-044b5e15ffdd",
        "release_name": "Dummy",
        "artists": [
            {
                "artist_mbid": "8f6bd1e4-fbe1-4f50-aa9b-94c450ec0f11",
                "artist_credit_name": "Portishead",
                "join_phrase": ""
            }
        ],
        "original_recording_mbid": "a96bf3b6-651d-49f4-9a89-eee27cecc18e"
    },
    {
        "artist_credit_mbids": [
            "31810c40-932a-4f2d-8cfd-17849844e2a6"
        ],
        "artist_credit_id": 11,
        "artist_credit_name": "Squirrel Nut Zippers",
        "length": 275333,
        "recording_mbid": "8fa0023e-1268-4d32-8341-83bb7506086e",
        "canonical_recording_mbid": "ec5b8aa9-7483-4791-a185-1f599a0cdc35",
        "recording_name": "Blue Angel",
        "release_mbid": "86b869c6-4a5b-4131-aff1-0edc25e18581",
        "artists": [
            {
                "artist_mbid": "31810c40-932a-4f2d-8cfd-17849844e2a6",
                "artist_credit_name": "Squirrel Nut Zippers",
                "join_phrase": ""
            }
        ],
        "release_name": "Erna 20: Swing und Blues",
        "original_recording_mbid": "8fa0023e-1268-4d32-8341-83bb7506086e"
    },
    {
        "artist_credit_mbids": [
            "4e024037-14b7-4aea-99ad-c6ace63b9620"
        ],
        "artist_credit_id": 92381,
        "artist_credit_name": "Madvillain",
        "length": 111666,
        "recording_mbid": "1636e7a9-229d-446d-aa81-e33071b42d7a",
        "canonical_recording_mbid": "1636e7a9-229d-446d-aa81-e33071b42d7a",
        "recording_name": "Strange Ways",
        "release_mbid": "94c77483-c110-42d5-8d70-db496dc3deef",
        "artists": [
            {
                "artist_mbid": "4e024037-14b7-4aea-99ad-c6ace63b9620",
                "artist_credit_name": "Madvillain",
                "join_phrase": ""
            }
        ],
        "release_name": "Madvillainy",
        "original_recording_mbid": "5948f779-0b96-4eba-b6a7-d1f0f6c7cf9f"
    },
    {
        "artist_credit_mbids": None,
        "artist_credit_id": None,
        "artist_credit_name": None,
        "length": None,
        "recording_mbid": None,
        "canonical_recording_mbid": None,
        "recording_name": None,
        "release_mbid": None,
        "release_name": None,
        "artists": [],
        "original_recording_mbid": "a1e97901-7ddf-4a0d-87ff-7f601ad3ccd3"
    }
]


class MainTestCase(flask_testing.TestCase):

    def create_app(self):
        app = create_app()
        app.config['MB_DATABASE_URI'] = 'yermom'
        app.config['SQLALCHEMY_TIMESCALE_URI'] = 'yermom'
        return app

    def setUp(self):
        self.maxDiff = None
        flask_testing.TestCase.setUp(self)
        mock_resolve_redirect_mbids = patch(
            "listenbrainz.db.recording.resolve_redirect_mbids",
            return_value=redirect_db_response
        )
        mock_resolve_canonical_mbids = patch(
            "listenbrainz.db.recording.resolve_canonical_mbids",
            return_value=canonical_db_response
        )
        mock_metadata_db_response = patch(
            "listenbrainz.db.recording.load_recordings_from_mbids",
            return_value=metadata_db_response
        )
        mock_resolve_redirect_mbids.start()
        mock_resolve_canonical_mbids.start()
        mock_metadata_db_response.start()

        self.addCleanup(mock_resolve_redirect_mbids.stop)
        self.addCleanup(mock_resolve_canonical_mbids.stop)
        self.addCleanup(mock_metadata_db_response.stop)

    def tearDown(self):
        flask_testing.TestCase.tearDown(self)

    def test_basics(self):
        q = RecordingFromRecordingMBIDQuery()
        self.assertEqual(q.names()[0], "recording-mbid-lookup")
        self.assertEqual(q.names()[1], "MusicBrainz Recording by MBID Lookup")
        self.assertNotEqual(q.introduction(), "")
        self.assertCountEqual(q.inputs().__fields__.keys(), ['recording_mbid'])
        self.assertCountEqual(q.outputs().__fields__.keys(), [
            'recording_mbid', 'recording_name', 'length', 'artist_credit_id', 'artist_credit_name',
            'artist_credit_mbids', 'canonical_recording_mbid', 'original_recording_mbid', 'release_name',
            'release_mbid', 'artists'])

    @patch('psycopg2.connect')
    def test_fetch(self, mock_connect):
        q = RecordingFromRecordingMBIDQuery()
        resp = q.fetch(json_request, RequestSource.json_post)
        self.assertEqual(len(resp), 4)
        self.assertDictEqual(json.loads(resp[0].json()), json_response[0])
        self.assertDictEqual(json.loads(resp[1].json()), json_response[1])
        self.assertDictEqual(json.loads(resp[2].json()), json_response[2])
        self.assertDictEqual(json.loads(resp[3].json()), json_response[3])

    @patch('psycopg2.connect')
    def test_count(self, mock_connect):
        q = RecordingFromRecordingMBIDQuery()
        resp = q.fetch(json_request, RequestSource.json_post, count=1)
        self.assertEqual(len(resp), 1)
        self.assertDictEqual(json.loads(resp[0].json()), json_response[0])

    @patch('psycopg2.connect')
    def test_offset(self, mock_connect):
        q = RecordingFromRecordingMBIDQuery()
        resp = q.fetch(json_request, RequestSource.json_post, offset=1)
        self.assertEqual(len(resp), 3)
        self.assertDictEqual(json.loads(resp[0].json()), json_response[1])
        self.assertDictEqual(json.loads(resp[1].json()), json_response[2])
        self.assertDictEqual(json.loads(resp[2].json()), json_response[3])

    @patch('psycopg2.connect')
    def test_count_and_offset(self, mock_connect):
        q = RecordingFromRecordingMBIDQuery()
        resp = q.fetch(json_request, RequestSource.json_post, count=1, offset=1)
        self.assertEqual(len(resp), 1)
        self.assertDictEqual(json.loads(resp[0].json()), json_response[1])
