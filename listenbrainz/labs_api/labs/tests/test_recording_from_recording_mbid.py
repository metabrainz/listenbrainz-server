import os
import unittest
from unittest.mock import patch, call, MagicMock

import flask_testing
import flask
import psycopg2
from datasethoster.main import app
from listenbrainz.labs_api.labs.api.recording_from_recording_mbid import RecordingFromRecordingMBIDQuery


json_request = [
    {
        "[recording_mbid]": "a96bf3b6-651d-49f4-9a89-eee27cecc18e"
    },
    {
        "[recording_mbid]": "ec5b8aa9-7483-4791-a185-1f599a0cdc35"
    },
    {
        "[recording_mbid]": "1234a7ae-2af2-4291-aa84-bd0bafe291a1"
    }
]

redirect_db_response = [
    {
        "recording_mbid_old": "a96bf3b6-651d-49f4-9a89-eee27cecc18e",
        "recording_mbid_new": "2f020e89-6e85-4be9-9f04-519ec8ec8cfa"
    },
    {
        "recording_mbid_old": "ec5b8aa9-7483-4791-a185-1f599a0cdc35",
        "recording_mbid_new": "6efd976a-109e-4146-9277-fb2af7d44910"
    },
]

json_db_response = [
    {
        "artist_credit_mbids": [
            "8f6bd1e4-fbe1-4f50-aa9b-94c450ec0f11"
        ],
        "artist_credit_id": 65,
        "artist_credit_name": "Portishead",
        "comment": "",
        "length": 253000,
        "recording_mbid": "1234a7ae-2af2-4291-aa84-bd0bafe291a1",
        "recording_name": "Sour Times"
    },
    {
        "artist_credit_mbids": [
            "31810c40-932a-4f2d-8cfd-17849844e2a6"
        ],
        "artist_credit_id": 11,
        "artist_credit_name": "Squirrel Nut Zippers",
        "comment": "",
        "length": 228533,
        "recording_mbid": "a96bf3b6-651d-49f4-9a89-eee27cecc18e",
        "recording_name": "Bad Businessman"
    },
    {
        "artist_credit_mbids": [
            "31810c40-932a-4f2d-8cfd-17849844e2a6"
        ],
        "artist_credit_id": 11,
        "artist_credit_name": "Squirrel Nut Zippers",
        "comment": "",
        "length": 275333,
        "recording_mbid": "ec5b8aa9-7483-4791-a185-1f599a0cdc35",
        "recording_name": "Blue Angel"
    }

]

json_response = [
    {
        "[artist_credit_mbids]": [
            "8f6bd1e4-fbe1-4f50-aa9b-94c450ec0f11"
        ],
        "artist_credit_id": 65,
        "artist_credit_name": "Portishead",
        "comment": "",
        "length": 253000,
        "recording_mbid": "1234a7ae-2af2-4291-aa84-bd0bafe291a1",
        "recording_name": "Sour Times"
    },
    {
        "[artist_credit_mbids]": [
            "31810c40-932a-4f2d-8cfd-17849844e2a6"
        ],
        "artist_credit_id": 11,
        "artist_credit_name": "Squirrel Nut Zippers",
        "comment": "",
        "length": 228533,
        "recording_mbid": "a96bf3b6-651d-49f4-9a89-eee27cecc18e",
        "recording_name": "Bad Businessman"
    },
    {
        "[artist_credit_mbids]": [
            "31810c40-932a-4f2d-8cfd-17849844e2a6"
        ],
        "artist_credit_id": 11,
        "artist_credit_name": "Squirrel Nut Zippers",
        "comment": "",
        "length": 275333,
        "recording_mbid": "ec5b8aa9-7483-4791-a185-1f599a0cdc35",
        "recording_name": "Blue Angel"
    }

]




class MainTestCase(flask_testing.TestCase):

    def create_app(self):
        app.config['MB_DATABASE_URI'] = 'yermom'
        return app

    def setUp(self):
        flask_testing.TestCase.setUp(self)

    def tearDown(self):
        flask_testing.TestCase.tearDown(self)

    def test_basics(self):
        q = RecordingFromRecordingMBIDQuery()
        self.assertEqual(q.names()[0], "recording-mbid-lookup")
        self.assertEqual(q.names()[1], "MusicBrainz Recording by MBID Lookup")
        self.assertNotEqual(q.introduction(), "")
        self.assertEqual(q.inputs(), ['[recording_mbid]'])
        self.assertEqual(q.outputs(), ['recording_mbid', 'recording_name', 'length', 'comment',
            'artist_credit_id', 'artist_credit_name', '[artist_credit_mbids]'])

    @patch('psycopg2.connect')
    def test_fetch(self, mock_connect):
        mock_connect().__enter__().cursor().__enter__().fetchone.side_effect = [redirect_db_response[0], 
                                                                                redirect_db_response[1], 
                                                                                None, 
                                                                                json_db_response[0], 
                                                                                json_db_response[1], 
                                                                                json_db_response[2], 
                                                                                None]
        q = RecordingFromRecordingMBIDQuery()
        resp = q.fetch(json_request)
        self.assertDictEqual(resp[0], json_response[0])
        self.assertDictEqual(resp[1], json_response[1])
        self.assertEqual(len(resp), 3)

    @patch('psycopg2.connect')
    def test_count(self, mock_connect):
        mock_connect().__enter__().cursor().__enter__().fetchone.side_effect = [redirect_db_response[0], 
                                                                                redirect_db_response[1], 
                                                                                None, 
                                                                                json_db_response[0], 
                                                                                None]
        q = RecordingFromRecordingMBIDQuery()
        resp = q.fetch(json_request, count=1)
        self.assertEqual(len(resp), 1)
        self.assertDictEqual(resp[0], json_response[0])

    @patch('psycopg2.connect')
    def test_offset(self, mock_connect):
        mock_connect().__enter__().cursor().__enter__().fetchone.side_effect = [redirect_db_response[0], 
                                                                                redirect_db_response[1], 
                                                                                None, 
                                                                                json_db_response[1], 
                                                                                json_db_response[2], 
                                                                                None]
        q = RecordingFromRecordingMBIDQuery()
        resp = q.fetch(json_request, offset=1)
        self.assertEqual(len(resp), 2)
        self.assertDictEqual(resp[0], json_response[1])
        self.assertDictEqual(resp[1], json_response[2])
