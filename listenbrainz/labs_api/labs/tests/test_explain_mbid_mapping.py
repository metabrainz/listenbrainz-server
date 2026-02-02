import flask_testing
from datasethoster.main import create_app
from listenbrainz.labs_api.labs.api.explain_mbid_mapping import ExplainMBIDMappingQuery, ExplainMBIDMappingInput

json_request_0 = [
    ExplainMBIDMappingInput(artist_credit_name="u2", recording_name="gloria", release_name=" "),
    ExplainMBIDMappingInput(artist_credit_name="portishead", recording_name="strangers", release_name=" "),
    ExplainMBIDMappingInput(artist_credit_name="portishead", recording_name="glory box (feat. your mom)", release_name=" ")
]

json_request_1 = [
    ExplainMBIDMappingInput(artist_credit_name="portishead", recording_name="strangers a", release_name=" ")
]

typesense_response_0 = [
    {
        "hits": [{
            "document": {
                "artist_credit_arg": "u2",
                "artist_credit_id": 197,
                "artist_mbids": ["a3cb23fc-acd3-4ce0-8f36-1e5aa6a18432"],
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
                    "artist_mbids": ["8f6bd1e4-fbe1-4f50-aa9b-94c450ec0f11"],
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
                "artist_mbids": ["8f6bd1e4-fbe1-4f50-aa9b-94c450ec0f11"],
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
                    "artist_mbids": ["8f6bd1e4-fbe1-4f50-aa9b-94c450ec0f11"],
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
        "match_type": 4,
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
        q = ExplainMBIDMappingQuery()
        self.assertEqual(q.names()[0], "explain-mbid-mapping")
        self.assertEqual(q.names()[1], "Explain MusicBrainz ID Mapping lookup")
        self.assertNotEqual(q.introduction(), "")
        self.assertCountEqual(q.inputs().__fields__.keys(), ['artist_credit_name', 'recording_name', 'release_name'])
