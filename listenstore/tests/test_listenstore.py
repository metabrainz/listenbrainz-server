# coding=utf-8
from __future__ import division, absolute_import, print_function, unicode_literals
import unittest2
import logging
from datetime import date, datetime
from .util import generate_data
from listenstore.listenstore import ListenStore

class TestListenStore(unittest2.TestCase):
    @classmethod
    def setUpClass(self):
        self.log = logging.getLogger(__name__)
        conf = {"replication_factor": 1,
                "cassandra_keyspace": "listenbrainz_integration_test",
                "cassandra_server": "localhost:9092"}
        self.logstore = ListenStore(conf)
        self._create_test_data()

    @classmethod
    def _create_test_data(self):
        self.log.info("Inserting test data...")
        test_data = generate_data(datetime(2015, 9, 3, 0, 0, 0), 1000)
        self.logstore.insert_batch(test_data)
        self.log.info("Test data inserted")

    @classmethod
    def tearDownClass(self):
        #self.logstore.drop_schema()
        self.logstore = None

    def test_fetch_listens(self):
        listens = self.logstore.fetch_listens(uid="test", limit=10)
        self.assertEqual(len(list(listens)), 10)
