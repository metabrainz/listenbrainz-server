from unittest.mock import patch

import flask_testing
from datasethoster import RequestSource
from datasethoster.main import create_app
from listenbrainz.labs_api.labs.api.tag_similarity import TagSimilarityQuery, TagSimilarityInput, TagSimilarityOutput

json_request = [
    TagSimilarityInput(tag="trip-hop")
]

db_response = [
    {
        "tag_0": "trippy",
        "tag_1": "trip-hop",
        "count": 9
    },
    {
        "tag_0": "welsh",
        "tag_1": "trip-hop",
        "count": 8
    },
]

json_response = [
    {
        "similar_tag": "trippy",
        "count": 9
    },
    {
        "similar_tag": "welsh",
        "count": 8
    },
]


class MainTestCase(flask_testing.TestCase):

    def create_app(self):
        app = create_app()
        app.config['MB_DATABASE_URI'] = 'fuss'
        app.config['SQLALCHEMY_TIMESCALE_URI'] = 'mip'
        return app

    def setUp(self):
        flask_testing.TestCase.setUp(self)

    def tearDown(self):
        flask_testing.TestCase.tearDown(self)

    def test_basics(self):
        q = TagSimilarityQuery()
        self.assertEqual(q.names()[0], "tag-similarity")
        self.assertEqual(q.names()[1], "ListenBrainz Tag Similarity")
        self.assertNotEqual(q.introduction(), "")
        self.assertCountEqual(q.inputs().__fields__.keys(), ['tag'])
        self.assertCountEqual(q.outputs().__fields__.keys(), ['similar_tag', 'count'])

    @patch('psycopg2.connect')
    def test_fetch(self, mock_connect):
        mock_connect().__enter__().cursor().__enter__().fetchone.side_effect = [db_response[0], db_response[1], None]
        q = TagSimilarityQuery()
        resp = q.fetch(json_request, RequestSource.json_post)
        self.assertEqual(len(resp), 2)
        self.assertDictEqual(resp[0].dict(), json_response[0])
        self.assertDictEqual(resp[1].dict(), json_response[1])
