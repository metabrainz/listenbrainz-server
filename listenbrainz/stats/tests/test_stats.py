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
