# coding=utf-8
from __future__ import division, absolute_import, print_function, unicode_literals
from db.testing import DatabaseTestCase
import logging
from datetime import datetime
from .util import generate_data, to_epoch
from listenstore.listenstore import PostgresListenStore, MIN_ID
from webserver.postgres_connection import init_postgres_connection
import random


class TestPostgresListenStore(DatabaseTestCase):

    INITIAL_LISTENS = 10
    INITIAL_DATE = datetime.utcfromtimestamp(random.randint(MIN_ID, MIN_ID + 10000000))

    def setUp(self):
        super(TestPostgresListenStore, self).setUp()
        self.log = logging.getLogger(__name__)
        self.logstore = init_postgres_connection(self.config.TEST_SQLALCHEMY_DATABASE_URI)
        self._create_test_data()

    def tearDown(self):
        # self.logstore.drop_schema()
        self.logstore = None

    def _create_test_data(self):
        self.log.info("Inserting test data...")
        test_data = generate_data(self.INITIAL_DATE, self.INITIAL_LISTENS)
        self.logstore.insert_postgresql(test_data)
        self.log.info("Test data inserted")

    def test_insert_postgresql(self):
        count = random.randint(1, 100)
        initial_date = to_epoch(self.INITIAL_DATE)
        date = datetime.utcfromtimestamp(random.randint(initial_date, initial_date + 10000000))
        test_data = generate_data(date, count)
        self.logstore.insert_postgresql(test_data)
        self.assertEquals(len(list(self.logstore.fetch_listens("test", from_id=to_epoch(date)))), count)

    def test_fetch_listens(self):
        listens = self.logstore.fetch_listens(user_id="test", from_id=to_epoch(self.INITIAL_DATE), limit=10)
        self.assertEquals(len(list(listens)), 10)
