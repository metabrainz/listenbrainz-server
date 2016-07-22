# coding=utf-8
from __future__ import division, absolute_import, print_function, unicode_literals
from db.testing import DatabaseTestCase
import logging
from datetime import datetime
from .util import generate_data, to_epoch
from webserver.postgres_connection import init_postgres_connection


class TestListenStore(DatabaseTestCase):

    def setUp(self):
        super(TestListenStore, self).setUp()
        self.log = logging.getLogger(__name__)
        self.logstore = init_postgres_connection(self.config.TEST_SQLALCHEMY_DATABASE_URI)
        self._create_test_data()

    def tearDown(self):
        # self.logstore.drop_schema()
        self.logstore = None

    def _create_test_data(self):
        date = datetime(2015, 9, 3, 0, 0, 0)
        self.log.info("Inserting test data...")
        test_data = generate_data(date, 100)
        self.logstore.insert_postgresql(test_data)
        self.log.info("Test data inserted")

    def test_fetch_listens(self):
        date = datetime(2015, 9, 3, 0, 0, 0)
        listens = self.logstore.fetch_listens(user_id="test", from_ts=to_epoch(date), limit=10)
        self.assertEquals(len(list(listens)), 10)
