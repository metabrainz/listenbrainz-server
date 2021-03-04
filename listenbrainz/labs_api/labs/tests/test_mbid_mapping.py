from unittest.mock import patch

import flask_testing
from datasethoster.main import create_app
from listenbrainz.labs_api.labs.api.mbid_mapping import MBIDMappingQuery, COLLECTION_NAME


json_request = [
    {
        "[artist_credit_name]": "u2",
        "[recording_name]": "gloria"
    },
    {
        "[artist_credit_name]": "portishead",
        "[recording_name]": "strangers"
    },
    {
        "[artist_credit_name]": "portishead",
        "[recording_name]": "glory box (feat. your mom)"
    }
]

typesense_response = [
    {
        "hits": [{
            "document": {
                "artist_credit_arg": "u2",
                "artist_credit_id": 197,
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

json_response = [
    {
        "artist_credit_arg": "u2",
        "artist_credit_id": 197,
        "artist_credit_name": "U2",
        "index": 0,
        "recording_arg": "gloria",
        "recording_mbid": "398a5f12-80ba-4d29-8b6b-bfe2176341a6",
        "recording_name": "Gloria",
        "release_mbid": "7abd5878-4ea3-4b33-a5d2-7721317013d7",
        "release_name": "October"
    },
    {
        "artist_credit_arg": "portishead",
        "artist_credit_id": 65,
        "artist_credit_name": "Portishead",
        "index": 1,
        "recording_arg": "strangers",
        "recording_mbid": "e97f805a-ab48-4c52-855e-07049142113d",
        "recording_name": "Strangers",
        "release_mbid": "76df3287-6cda-33eb-8e9a-044b5e15ffdd",
        "release_name": "Dummy"
    },
    {
        "artist_credit_arg": "portishead",
        "artist_credit_id": 65,
        "artist_credit_name": "Portishead",
        "index": 2,
        "recording_arg": "glory box (feat. your mom)",
        "recording_mbid": "145f5c43-0ac2-4886-8b09-63d0e92ded5d",
        "recording_name": "Glory Box",
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
        self.assertEqual(
            q.inputs(), ['[artist_credit_name]', '[recording_name]'])
        self.assertEqual(q.outputs(), ['index', 'artist_credit_arg', 'recording_arg',
                                       'artist_credit_name', 'release_name', 'recording_name',
                                       'release_mbid', 'recording_mbid', 'artist_credit_id'])

    @patch('typesense.documents.Documents.search')
    def test_fetch(self, search):
        search.side_effect = typesense_response

        q = MBIDMappingQuery()
        resp = q.fetch(json_request)
        self.assertEqual(len(resp), 3)
        self.assertDictEqual(resp[0], json_response[0])
        self.assertDictEqual(resp[1], json_response[1])
        self.assertDictEqual(resp[2], json_response[2])
