import unittest
from unittest.mock import patch, MagicMock
import os
from listenbrainz import stats
from listenbrainz import bigquery
from listenbrainz.stats.exceptions import NoCredentialsVariableException, NoCredentialsFileException

from listenbrainz import config

bigquery_responses = {
    "done": {
        "jobReference": {
            "projectId": "test_project_id",
            "jobId": "test_job_id",
        },
        "totalRows": "2",
        "jobComplete": True,
        "rows": [
            {
                "f": [
                    {
                        "v": "Daft Punk"
                    },
                    {
                        "v": "72c41851-d1eb-441c-a1fa-046f996f36b0"
                    }
                ]
            },
            {
                "f": [
                    {
                        "v": "Animal Collective"
                    },
                    {
                        "v": "1a586268-204a-4691-9ee4-96269ff3cace"
                    }
                ]
            }
        ],
        "schema": {
            "fields": [
                {
                    "type": "STRING",
                    "name": "artist_name",
                    "mode": "NULLABLE"
                },
                {
                    "type": "STRING",
                    "name": "artist_msid",
                    "mode": "NULLABLE"
                }
            ]
        }
    }
}

expected_results = {
    'done': [
        {
            "artist_name": "Daft Punk",
            "artist_msid": "72c41851-d1eb-441c-a1fa-046f996f36b0"
        },
        {
            "artist_name": "Animal Collective",
            "artist_msid": "1a586268-204a-4691-9ee4-96269ff3cace"
        }
    ]
}


class StatsTestCase(unittest.TestCase):

    def test_get_parameters(self):

        params = [
            {
                'name': 'param1',
                'type': 'STRING',
                'value': '12312'
            }
        ]

        modified_params = bigquery.get_parameters_dict(params)

        self.assertIsInstance(modified_params, list)
        self.assertEqual(len(modified_params), 1)
        self.assertIsInstance(modified_params[0], dict)
        self.assertEqual(modified_params[0]['name'], params[0]['name'])
        self.assertIsInstance(modified_params[0]['parameterType'], dict)
        self.assertEqual(modified_params[0]['parameterType']['type'], params[0]['type'])
        self.assertIsInstance(modified_params[0]['parameterValue'], dict)
        self.assertEqual(modified_params[0]['parameterValue']['value'], params[0]['value'])

    def test_format_results(self):
        data = bigquery_responses['done']
        formatted_data = bigquery.format_results(data)
        self.assertEqual(len(formatted_data), 2)
        self.assertEqual(formatted_data[0]['artist_name'], data['rows'][0]['f'][0]['v'])
        self.assertEqual(formatted_data[0]['artist_msid'], data['rows'][0]['f'][1]['v'])
        self.assertEqual(formatted_data[1]['artist_name'], data['rows'][1]['f'][0]['v'])
        self.assertEqual(formatted_data[1]['artist_msid'], data['rows'][1]['f'][1]['v'])

    @patch('listenbrainz.bigquery.current_app') # patching current_app so that test doesn't have to run in app context
    def test_run_query_done(self, mock_current_app):
        """ Test run_query when the result is directly returned by the first api call to bigquery.jobs.query """

        mock_bigquery = MagicMock()
        # set the value returned by call to bigquery to a response which signifies completed query
        mock_bigquery.jobs.return_value.query.return_value.execute.return_value = bigquery_responses['done']

        # construct query and parameters
        query = """SELECT artist_msid, artist_name
                     FROM {dataset_id}.{table_id}
                    WHERE user_name = @username
                """.format(dataset_id=config.BIGQUERY_DATASET_ID, table_id=config.BIGQUERY_TABLE_ID)

        parameters = [{
            'name': 'username',
            'type': 'STRING',
            'value': 'testuser'
        }]

        result = bigquery.run_query(mock_bigquery, query, parameters)
        self.assertListEqual(result, expected_results['done'])
