# coding=utf-8
from __future__ import division, absolute_import, print_function, unicode_literals
import unittest2
import logging
from datetime import date, datetime
from .util import generate_data
from listenstore.listenstore import PostgresListenStore


class TestListenStore(unittest2.TestCase):

    @classmethod
    # @unittest2.skip("We don't have Postgres on Jenkins server")
    def setUpClass(self):
        self.log = logging.getLogger(__name__)
        conf = {
            "SQLALCHEMY_DATABASE_URI": "postgresql://lb_test@/lb_test"
        }
        self.logstore = PostgresListenStore(conf)
        self._create_test_data()

    @classmethod
    def _create_test_data(self):
        self.log.info("Inserting test data...")
        test_data = generate_data(datetime(2015, 9, 3, 0, 0, 0), 1000)
        self.logstore.insert_postgresql(test_data)
        self.log.info("Test data inserted")

    @classmethod
    def tearDownClass(self):
        #self.logstore.drop_schema()
        self.logstore = None

    # @unittest2.skip("We don't have Postgres on Jenkins server")
    def test_fetch_listens(self):
        listens = self.logstore.fetch_listens(user_id="test", limit=10)
        self.assertEqual(len(list(listens)), 10)
