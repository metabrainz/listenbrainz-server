# coding=utf-8

import logging
import random
import uuid
from collections import OrderedDict
from datetime import datetime

import listenbrainz.db.user as db_user
from listenbrainz.db.testing import DatabaseTestCase
from listenbrainz.listen import Listen
from listenbrainz.listenstore import MIN_ID
from listenbrainz.listenstore.tests.util import generate_data, to_epoch
from listenbrainz.webserver.postgres_connection import init_postgres_connection


class TestPostgresListenStore(DatabaseTestCase):

    def setUp(self):
        super(TestPostgresListenStore, self).setUp()
        self.log = logging.getLogger(__name__)
        self.logstore = init_postgres_connection(self.config.SQLALCHEMY_DATABASE_URI)
        self.testuser_id = db_user.create("test")
        self.testuser_name = db_user.get(self.testuser_id)['musicbrainz_id']

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
        self.assertEqual(len(self.logstore.fetch_listens(user_name=self.testuser_name, from_ts=from_ts, limit=count)), count)

    def test_fetch_listens(self):
        from_ts, count = self._create_test_data()
        listens = self.logstore.fetch_listens(user_name=self.testuser_name, from_ts=from_ts, limit=count)
        self.assertEqual(len(listens), count)

    def test_convert_row(self):
        now = datetime.utcnow()
        data = [('id', 1), ('user_id', self.testuser_id), ('user_name', self.testuser_name), ('timestamp', now),
                ('artist_msid', str(uuid.uuid4())), ('release_msid', str(uuid.uuid4())), ('recording_msid', str(uuid.uuid4())),
                ('data', "{'additional_info':{}}"), ('ts_since_epoch', to_epoch(now))]
        row = OrderedDict([(str(k), v) for (k, v) in data[1:]])
        listen = self.logstore.convert_row([1] + list(row.values()))
        self.assertIsInstance(listen, Listen)
        self.assertEqual(listen.user_name, row['user_name'])
        self.assertEqual(listen.ts_since_epoch, row['ts_since_epoch'])
        self.assertEqual(listen.artist_msid, row['artist_msid'])
        self.assertEqual(listen.release_msid, row['release_msid'])
        self.assertEqual(listen.recording_msid, row['recording_msid'])
