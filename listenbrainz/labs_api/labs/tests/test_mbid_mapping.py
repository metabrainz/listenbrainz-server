from unittest.mock import patch

import flask_testing
from datasethoster.main import create_app
from listenbrainz.labs_api.labs.api.mbid_mapping import MBIDMappingQuery, COLLECTION_NAME


json_request = [
    {
        "[artist_credit_name]": "u2",
        "[recording_name]": "gloria"
    }
]

typesense_response = {
    "hits" : [ {
        "artist_credit_arg": "u2",
        "artist_credit_id": 197,
        "artist_credit_name": "U2",
        "recording_arg": "gloria",
        "recording_mbid": "398a5f12-80ba-4d29-8b6b-bfe2176341a6",
        "recording_name": "Gloria",
        "release_mbid": "7abd5878-4ea3-4b33-a5d2-7721317013d7",
        "release_name": "October"
    } ]
} 

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
        self.assertEqual(q.inputs(), ['[artist_credit_name]', '[recording_name]'])
        self.assertEqual(q.outputs(), ['index', 'artist_credit_arg', 'recording_arg',
                         'artist_credit_name', 'release_name', 'recording_name',
                         'release_mbid', 'recording_mbid', 'artist_credit_id'])

    @patch('typesense.Client')
    def test_fetch(self, client):
        client.collections[COLLECTION_NAME].documents.search.return_value = typesense_response

        q = MBIDMappingQuery()
        print(client.call_count)
        resp = q.fetch(json_request)
        print(client.call_count)
        self.assertEqual(len(resp), 1)
        self.assertDictEqual(resp[0], json_response[0])
