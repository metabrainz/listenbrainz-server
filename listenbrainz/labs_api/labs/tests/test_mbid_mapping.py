import json
from unittest.mock import patch

import flask_testing
from datasethoster import RequestSource
from datasethoster.main import create_app
from listenbrainz.labs_api.labs.api.mbid_mapping import MBIDMappingQuery, MBIDMappingInput

json_request_0 = [
    MBIDMappingInput(artist_credit_name="u2", recording_name="gloria"),
    MBIDMappingInput(artist_credit_name="portishead", recording_name="strangers"),
    MBIDMappingInput(artist_credit_name="portishead", recording_name="glory box (feat. your mom)"),
]

json_request_1 = [
    MBIDMappingInput(artist_credit_name="portishead", recording_name="strangers a")
]

typesense_response_0 = [
    {
        "hits": [{
            "document": {
                "artist_credit_arg": "u2",
                "artist_credit_id": 197,
                "artist_mbids": "{a3cb23fc-acd3-4ce0-8f36-1e5aa6a18432}",
                "artist_credit_name": "U2",
                "recording_arg": "gloria",
                "recording_mbid": "398a5f12-80ba-4d29-8b6b-bfe2176341a6",
                "recording_name": "Gloria",
                "release_mbid": "7abd5878-4ea3-4b33-a5d2-7721317013d7",
                "release_name": "October"
            },
        }
        ]
    },
    {
        "hits": [
            {
                "document": {
                    "artist_credit_arg": "portishead",
                    "artist_credit_id": 65,
                    "artist_mbids": "{8f6bd1e4-fbe1-4f50-aa9b-94c450ec0f11}",
                    "artist_credit_name": "Portishead",
                    "recording_arg": "strangers",
                    "recording_mbid": "e97f805a-ab48-4c52-855e-07049142113d",
                    "recording_name": "Strangers",
                    "release_mbid": "76df3287-6cda-33eb-8e9a-044b5e15ffdd",
                    "release_name": "Dummy"
                }
            }
        ]
    },
    {
        "hits": []
    },
    {
        "hits": [{
            "document": {
                "artist_credit_arg": "portishead",
                "artist_credit_id": 65,
                "artist_mbids": "{8f6bd1e4-fbe1-4f50-aa9b-94c450ec0f11}",
                "artist_credit_name": "Portishead",
                "recording_arg": "glory box (feat. your mom)",
                "recording_mbid": "145f5c43-0ac2-4886-8b09-63d0e92ded5d",
                "recording_name": "Glory Box",
                "release_mbid": "76df3287-6cda-33eb-8e9a-044b5e15ffdd",
                "release_name": "Dummy"
            }
        }
        ]
    }
]

typesense_response_1 = [
    {
        "hits": [
            {
                "document": {
                    "artist_credit_arg": "portishead",
                    "artist_credit_id": 65,
                    "artist_mbids": "{8f6bd1e4-fbe1-4f50-aa9b-94c450ec0f11}",
                    "artist_credit_name": "Portishead",
                    "recording_arg": "strangers",
                    "recording_mbid": "e97f805a-ab48-4c52-855e-07049142113d",
                    "recording_name": "Strangers",
                    "release_mbid": "76df3287-6cda-33eb-8e9a-044b5e15ffdd",
                    "release_name": "Dummy"
                }
            }
        ]
    }
]

json_response_0 = [
    {
        "artist_credit_arg": "u2",
        "artist_credit_id": 197,
        "artist_mbids": ["a3cb23fc-acd3-4ce0-8f36-1e5aa6a18432"],
        "artist_credit_name": "U2",
        "index": 0,
        "match_type": 4,
        "recording_arg": "gloria",
        "recording_mbid": "398a5f12-80ba-4d29-8b6b-bfe2176341a6",
        "recording_name": "Gloria",
        "release_mbid": "7abd5878-4ea3-4b33-a5d2-7721317013d7",
        "release_name": "October"
    },
    {
        "artist_credit_arg": "portishead",
        "artist_credit_id": 65,
        "artist_mbids": ["8f6bd1e4-fbe1-4f50-aa9b-94c450ec0f11"],
        "artist_credit_name": "Portishead",
        "index": 1,
        "match_type": 4,
        "recording_arg": "strangers",
        "recording_mbid": "e97f805a-ab48-4c52-855e-07049142113d",
        "recording_name": "Strangers",
        "release_mbid": "76df3287-6cda-33eb-8e9a-044b5e15ffdd",
        "release_name": "Dummy"
    },
    {
        "artist_credit_arg": "portishead",
        "artist_credit_id": 65,
        "artist_mbids": ["8f6bd1e4-fbe1-4f50-aa9b-94c450ec0f11"],
        "artist_credit_name": "Portishead",
        "index": 2,
        "match_type": 1,
        "recording_arg": "glory box (feat. your mom)",
        "recording_mbid": "145f5c43-0ac2-4886-8b09-63d0e92ded5d",
        "recording_name": "Glory Box",
        "release_mbid": "76df3287-6cda-33eb-8e9a-044b5e15ffdd",
        "release_name": "Dummy"
    }
]

json_response_1 = [
    {
        "artist_credit_arg": "portishead",
        "artist_credit_id": 65,
        "artist_mbids": ["8f6bd1e4-fbe1-4f50-aa9b-94c450ec0f11"],
        "artist_credit_name": "Portishead",
        "index": 0,
        "match_type": 3,
        "recording_arg": "strangers a",
        "recording_mbid": "e97f805a-ab48-4c52-855e-07049142113d",
        "recording_name": "Strangers",
        "release_mbid": "76df3287-6cda-33eb-8e9a-044b5e15ffdd",
        "release_name": "Dummy"
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
        q = MBIDMappingQuery()
        self.assertEqual(q.names()[0], "mbid-mapping")
        self.assertEqual(q.names()[1], "MusicBrainz ID Mapping lookup")
        self.assertNotEqual(q.introduction(), "")
        self.assertCountEqual(
            q.inputs().__fields__.keys(),
            ['artist_credit_name', 'recording_name']
        )
        self.assertCountEqual(
            q.outputs().__fields__.keys(),
            ['index', 'artist_credit_arg', 'recording_arg',  'artist_credit_name',
             'artist_mbids', 'release_name', 'recording_name', 'release_mbid', 'recording_mbid',
             'artist_credit_id', 'match_type'])

    @patch('typesense.documents.Documents.search')
    def test_fetch(self, search):
        search.side_effect = typesense_response_0

        q = MBIDMappingQuery()
        resp = q.fetch(json_request_0, RequestSource.json_post)
        self.assertEqual(len(resp), 3)
        self.assertDictEqual(json.loads(resp[0].json()), json_response_0[0])
        self.assertDictEqual(json.loads(resp[1].json()), json_response_0[1])
        self.assertDictEqual(json.loads(resp[2].json()), json_response_0[2])

    @patch('typesense.documents.Documents.search')
    def test_fetch_without_stop_words(self, search):
        search.side_effect = typesense_response_1

        q = MBIDMappingQuery(remove_stop_words=True)
        resp = q.fetch(json_request_1, RequestSource.json_post)
        self.assertEqual(len(resp), 1)
        self.maxDiff = None
        self.assertDictEqual(json.loads(resp[0].json()), json_response_1[0])
