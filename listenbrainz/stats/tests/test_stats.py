import unittest
import os
from listenbrainz import stats
from listenbrainz.stats.exceptions import NoCredentialsVariableException, NoCredentialsFileException


class StatsTestCase(unittest.TestCase):

    def test_init_bigquery(self):
        """ Test for BigQuery connection initialization """

        if not stats.APP_CREDENTIALS_FILE:
            with self.assertRaises(NoCredentialsVariableException):
                stats.init_bigquery_connection()
        elif not os.path.exists(stats.APP_CREDENTIALS_FILE):
            with self.assertRaises(NoCredentialsFileException):
                stats.init_bigquery_connection()
        else:
            stats.init_bigquery_connection()
            self.assertIsNotNone(stats.bigquery)

    def test_get_parameters(self):

        params = [
            {
                'name': 'param1',
                'type': 'STRING',
                'value': '12312'
            }
        ]

        modified_params = stats.get_parameters_dict(params)

        self.assertIsInstance(modified_params, list)
        self.assertEqual(len(modified_params), 1)
        self.assertIsInstance(modified_params[0], dict)
        self.assertEqual(modified_params[0]['name'], params[0]['name'])
        self.assertIsInstance(modified_params[0]['parameterType'], dict)
        self.assertEqual(modified_params[0]['parameterType']['type'], params[0]['type'])
        self.assertIsInstance(modified_params[0]['parameterValue'], dict)
        self.assertEqual(modified_params[0]['parameterValue']['value'], params[0]['value'])
