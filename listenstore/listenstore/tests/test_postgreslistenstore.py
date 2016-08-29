# coding=utf-8
from __future__ import division, absolute_import, print_function, unicode_literals
from db.testing import DatabaseTestCase
import logging
from datetime import datetime
from .util import generate_data, to_epoch
from listen import Listen
from listenstore.listenstore import PostgresListenStore, MIN_ID
from webserver.postgres_connection import init_postgres_connection
import random
import uuid
from collections import OrderedDict
from sqlalchemy import text
import db.user

class TestPostgresListenStore(DatabaseTestCase):

    def setUp(self):
        super(TestPostgresListenStore, self).setUp()
        self.log = logging.getLogger(__name__)
        self.logstore = init_postgres_connection(self.config.TEST_SQLALCHEMY_DATABASE_URI)
        self.testuser_id = db.user.create("test")
        user = db.user.get(self.testuser_id)
        print(user)
        self.testuser_name = db.user.get(self.testuser_id)['musicbrainz_id']

    def tearDown(self):
        self.logstore = None
        super(TestPostgresListenStore, self).tearDown()

    def _create_test_data(self, from_ts=MIN_ID + 1, num_listens=random.randint(1, 100)):
        self.log.info("Inserting test data...")
        test_data = generate_data(self.testuser_id, from_ts, num_listens)
        self.logstore.insert(test_data)
        self.log.info("Test data inserted")
        return from_ts, num_listens

    def test_insert_postgresql(self):
        from_ts, count = self._create_test_data()
        self.assertEquals(len(self.logstore.fetch_listens(self.testuser_id, from_ts=from_ts)), count)

    def test_fetch_listens(self):
        from_ts, count = self._create_test_data()
        listens = self.logstore.fetch_listens(user_id=self.testuser_id, from_ts=from_ts, limit=count)
        self.assertEquals(len(listens), count)

    def test_convert_row(self):
        now = datetime.utcnow()
        data = [('id', 1), ('user_id', self.testuser_id), ('timestamp', now), ('artist_msid', str(uuid.uuid4())),
                ('album_msid', str(uuid.uuid4())), ('recording_msid', str(uuid.uuid4())), ('data', "{'additional_info':{}}"),
                ('ts_since_epoch', to_epoch(now)), ('user_name', self.testuser_name)]
        row = OrderedDict([(str(k), v) for (k, v) in data[1:]])
        listen = self.logstore.convert_row([1] + row.values())
        self.assertIsInstance(listen, Listen)
        print("Listen ", listen.__dict__)
        print("row ", dict(row))
        self.assertDictEqual(listen.__dict__, dict(row))
