import os
import unittest
import json

JSON_FILE_PATH = os.path.join(os.path.dirname(os.path.realpath(__file__)), '../request_queries.json')


class QueryJSONTestCase(unittest.TestCase):

    def test_valid_request_queries_json(self):
        with open(JSON_FILE_PATH) as f:
            query_list = json.load(f)
            self.assertIsNotNone(query_list)
