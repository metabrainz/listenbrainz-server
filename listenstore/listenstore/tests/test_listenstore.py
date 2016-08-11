# coding=utf-8
from __future__ import division, absolute_import, print_function, unicode_literals
from db.testing import DatabaseTestCase
import logging
from datetime import datetime
from .util import generate_data, to_epoch
from webserver.postgres_connection import init_postgres_connection
import db.user


class TestListenStore(DatabaseTestCase):

    def setUp(self):
        super(TestListenStore, self).setUp()
        self.log = logging.getLogger(__name__)
        self.logstore = init_postgres_connection(self.config.TEST_SQLALCHEMY_DATABASE_URI)
        self.testuser_id = db.user.create("test")
        self._create_test_data()

    def tearDown(self):
        # pass
        super(TestListenStore, self).tearDown()
        self.logstore = None

    def _create_test_data(self):
        date = datetime(2015, 9, 3, 0, 0, 0)
        self.log.info("Inserting test data...")
        test_data = generate_data(self.testuser_id, date, 100)
        self.logstore.insert(test_data)
        self.log.info("Test data inserted")

    def test_fetch_listens(self):
        date = datetime(2015, 9, 3, 0, 0, 0)
        test_data = generate_data(self.testuser_id, date, 100)
        self.logstore.insert(test_data)
        # self.AAA = to_epoch(date)
        listens = self.logstore.fetch_listens(user_id=self.testuser_id, from_ts=to_epoch(date), limit=10)
        self.assertEquals(len(listens), 10)
