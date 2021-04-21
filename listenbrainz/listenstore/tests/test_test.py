# coding=utf-8
import sys
import os
from time import sleep, time
from datetime import datetime, timedelta
import logging
import shutil
import subprocess
import tarfile
import tempfile

import ujson
import psycopg2
import sqlalchemy
import listenbrainz.db.user as db_user
from listenbrainz.db.testing import DatabaseTestCase
from listenbrainz.db import timescale as ts
from listenbrainz import config
from listenbrainz.listenstore.tests.util import create_test_data_for_timescalelistenstore, generate_data
from listenbrainz.webserver.timescale_connection import init_timescale_connection
from listenbrainz.db.dump import SchemaMismatchException
from listenbrainz.listenstore import LISTENS_DUMP_SCHEMA_VERSION
from listenbrainz.listenstore.timescale_listenstore import REDIS_TIMESCALE_USER_LISTEN_COUNT
from brainzutils import cache

TIMESCALE_SQL_DIR = os.path.join(os.path.dirname(os.path.realpath(__file__)), '..', '..', '..', 'admin', 'timescale')


class TestTimescaleListenStore(DatabaseTestCase):

    def reset_timescale_db(self):

        ts.init_db_connection(config.TIMESCALE_ADMIN_URI)
        ts.run_sql_script_without_transaction(os.path.join(TIMESCALE_SQL_DIR, 'drop_db.sql'))
        ts.run_sql_script_without_transaction(os.path.join(TIMESCALE_SQL_DIR, 'create_db.sql'))
        ts.engine.dispose()

        ts.init_db_connection(config.TIMESCALE_ADMIN_LB_URI)
        ts.run_sql_script_without_transaction(os.path.join(TIMESCALE_SQL_DIR, 'create_extensions.sql'))
        ts.engine.dispose()

        ts.init_db_connection(config.SQLALCHEMY_TIMESCALE_URI)
        ts.run_sql_script(os.path.join(TIMESCALE_SQL_DIR, 'create_schemas.sql'))
        ts.run_sql_script(os.path.join(TIMESCALE_SQL_DIR, 'create_tables.sql'))
        ts.run_sql_script(os.path.join(TIMESCALE_SQL_DIR, 'create_functions.sql'))
        ts.run_sql_script(os.path.join(TIMESCALE_SQL_DIR, 'create_views.sql'))
        ts.run_sql_script(os.path.join(TIMESCALE_SQL_DIR, 'create_indexes.sql'))
        ts.run_sql_script(os.path.join(TIMESCALE_SQL_DIR, 'create_primary_keys.sql'))
        ts.run_sql_script(os.path.join(TIMESCALE_SQL_DIR, 'create_foreign_keys.sql'))
        ts.engine.dispose()

    def setUp(self):
        super(TestTimescaleListenStore, self).setUp()
        self.log = logging.getLogger(__name__)
        self.reset_timescale_db()

        self.ns = config.REDIS_NAMESPACE
        self.logstore = init_timescale_connection(self.log, {
            'REDIS_HOST': config.REDIS_HOST,
            'REDIS_PORT': config.REDIS_PORT,
            'REDIS_NAMESPACE': config.REDIS_NAMESPACE,
            'SQLALCHEMY_TIMESCALE_URI': config.SQLALCHEMY_TIMESCALE_URI,
        })

        self.testuser_id = db_user.create(1, "test")
        self.testuser_name = db_user.get(self.testuser_id)['musicbrainz_id']

    def tearDown(self):
        self.logstore = None
        super(TestTimescaleListenStore, self).tearDown()

    def _create_test_data(self, user_name, test_data_file_name=None):
        test_data = create_test_data_for_timescalelistenstore(user_name, test_data_file_name)
        self.logstore.insert(test_data)
        return len(test_data)

    def set_created_to_NULL_in_DB(self):
        try:
            with ts.engine.connect() as connection:
                connection.execute(sqlalchemy.text("UPDATE listen SET created = NULL"))
        except psycopg2.OperationalError as e:
            self.log.error("Cannot query timescale listen_count: %s" % str(e), exc_info=True)
            raise
