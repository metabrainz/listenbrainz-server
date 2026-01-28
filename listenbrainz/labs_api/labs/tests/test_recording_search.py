import json
from unittest.mock import patch

import flask_testing
from datasethoster import RequestSource
from datasethoster.main import create_app
from listenbrainz.labs_api.labs.api.recording_search import RecordingSearchQuery, RecordingSearchInput

json_request = [
    RecordingSearchInput(query="sun shines tv"),
    RecordingSearchInput(query="portishead strangers"),
    RecordingSearchInput(query="morcheeba good girl down"),
]

typesense_response = [
    {
        "hits": [{
            "document": {
                "artist_credit_id": 1769257,
                "artist_credit_name": "a‐ha",
                "recording_mbid": "9efc9217-d8cc-4f3b-b019-4a53a81e37b0",
                "recording_name": "The Sun Always Shines on T.V.",
                "release_mbid": "181b9a01-0446-4601-99be-b011ab615631",
                "release_name": "Hunting High and Low"
            },
        }
        ]
    },
    {
        "hits": [
            {
                "document": {
                    "artist_credit_id": 65,
                    "artist_credit_name": "Portishead",
                    "recording_mbid": "e97f805a-ab48-4c52-855e-07049142113d",
                    "recording_name": "Strangers",
                    "release_mbid": "76df3287-6cda-33eb-8e9a-044b5e15ffdd",
                    "release_name": "Dummy"
                }
            }
        ]
    },
    {
        "hits": [{
            "document": {
                "artist_credit_id": 947235,
                "artist_credit_name": "Morcheeba feat. Bahamadia",
                "recording_mbid": "0a35350f-8074-462f-9473-db0f08568285",
                "recording_name": "Good Girl Down",
                "release_mbid": "90ed8b8c-ea11-3ee1-8da6-ed32f39fdac8",
                "release_name": "Fragments of Freedom"
            }
        }
        ]
    }
]

json_response = [
    {
        "artist_credit_id": 1769257,
        "artist_credit_name": "a‐ha",
        "recording_mbid": "9efc9217-d8cc-4f3b-b019-4a53a81e37b0",
        "recording_name": "The Sun Always Shines on T.V.",
        "release_mbid": "181b9a01-0446-4601-99be-b011ab615631",
        "release_name": "Hunting High and Low"
    },
    {
        "artist_credit_id": 65,
        "artist_credit_name": "Portishead",
        "recording_mbid": "e97f805a-ab48-4c52-855e-07049142113d",
        "recording_name": "Strangers",
        "release_mbid": "76df3287-6cda-33eb-8e9a-044b5e15ffdd",
        "release_name": "Dummy"
    },
    {
        "artist_credit_id": 947235,
        "artist_credit_name": "Morcheeba feat. Bahamadia",
        "recording_mbid": "0a35350f-8074-462f-9473-db0f08568285",
        "recording_name": "Good Girl Down",
        "release_mbid": "90ed8b8c-ea11-3ee1-8da6-ed32f39fdac8",
        "release_name": "Fragments of Freedom"
    }
]


class MainTestCase(flask_testing.TestCase):

    def create_app(self):
        app = create_app()
        return app

    def setUp(self):
        flask_testing.TestCase.setUp(self)

    def tearDown(self):
        flask_testing.TestCase.tearDown(self)

    def test_basics(self):
        q = RecordingSearchQuery()
        self.assertEqual(q.names()[0], "recording-search")
        self.assertEqual(q.names()[1], "MusicBrainz Recording search")
        self.assertNotEqual(q.introduction(), "")
        self.assertCountEqual(q.inputs().__fields__.keys(), ['query'])
        self.assertCountEqual(q.outputs().__fields__.keys(),
                         ['recording_name', 'recording_mbid', 'release_name',
                          'release_mbid', 'artist_credit_name', 'artist_credit_id'])

    @patch('typesense.documents.Documents.search')
    def test_fetch(self, search):
        search.side_effect = typesense_response

        q = RecordingSearchQuery()
        resp = q.fetch([json_request[0]], RequestSource.json_post)
        self.assertEqual(len(resp), 1)
        self.assertDictEqual(json.loads(resp[0].json()), json_response[0])

        resp = q.fetch([json_request[1]], RequestSource.json_post)
        self.assertEqual(len(resp), 1)
        self.assertDictEqual(json.loads(resp[0].json()), json_response[1])

        resp = q.fetch([json_request[2]], RequestSource.json_post)
        self.assertEqual(len(resp), 1)
        self.assertDictEqual(json.loads(resp[0].json()), json_response[2])
