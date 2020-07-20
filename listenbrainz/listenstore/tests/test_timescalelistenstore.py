# coding=utf-8

import os
from time import time
from datetime import datetime
import logging
import shutil
import subprocess
import tarfile
import tempfile
import random

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
        ts.run_sql_script(os.path.join(TIMESCALE_SQL_DIR, 'create_tables.sql'))
        ts.run_sql_script(os.path.join(TIMESCALE_SQL_DIR, 'create_functions.sql'))
        ts.run_sql_script(os.path.join(TIMESCALE_SQL_DIR, 'create_views.sql'))
        ts.run_sql_script(os.path.join(TIMESCALE_SQL_DIR, 'create_indexes.sql'))
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

    def test_check_listen_count_view_exists(self):
        try:
            with ts.engine.connect() as connection:
                result = connection.execute(sqlalchemy.text("""SELECT column_name
                                                                 FROM information_schema.columns
                                                                WHERE table_name = 'listen_count'
                                                             ORDER BY column_name"""))
                cols = result.fetchall()
        except psycopg2.OperationalError as e:
            self.log.error("Cannot query timescale listen_count: %s" % str(e), exc_info=True)
            raise
        self.assertEqual(cols[0][0], "count")
        self.assertEqual(cols[1][0], "listened_at_bucket")
        self.assertEqual(cols[2][0], "user_name")

    # The test test_aaa_get_total_listen_count is gone because all it did was test to see if the
    # timescale continuous aggregate works and often times it didn't work fast enough. We don't care
    # about immediate correctness, but eventual correctness, so test tossed.

    def test_insert_timescale(self):
        count = self._create_test_data(self.testuser_name)
        self.assertEqual(len(self.logstore.fetch_listens(user_name=self.testuser_name, from_ts=1399999999)), count)

    def test_fetch_listens_0(self):
        self._create_test_data(self.testuser_name)
        listens = self.logstore.fetch_listens(user_name=self.testuser_name, from_ts=1400000000, limit=1)
        self.assertEqual(len(listens), 1)
        self.assertEqual(listens[0].ts_since_epoch, 1400000050)

    def test_fetch_listens_1(self):
        self._create_test_data(self.testuser_name)
        listens = self.logstore.fetch_listens(user_name=self.testuser_name, from_ts=1400000000)
        self.assertEqual(len(listens), 4)
        self.assertEqual(listens[0].ts_since_epoch, 1400000200)
        self.assertEqual(listens[1].ts_since_epoch, 1400000150)
        self.assertEqual(listens[2].ts_since_epoch, 1400000100)
        self.assertEqual(listens[3].ts_since_epoch, 1400000050)

    def test_fetch_listens_2(self):
        self._create_test_data(self.testuser_name)
        listens = self.logstore.fetch_listens(user_name=self.testuser_name, from_ts=1400000100)
        self.assertEqual(len(listens), 2)
        self.assertEqual(listens[0].ts_since_epoch, 1400000200)
        self.assertEqual(listens[1].ts_since_epoch, 1400000150)

    def test_fetch_listens_3(self):
        self._create_test_data(self.testuser_name)
        listens = self.logstore.fetch_listens(user_name=self.testuser_name, to_ts=1400000300)
        self.assertEqual(len(listens), 5)
        self.assertEqual(listens[0].ts_since_epoch, 1400000200)
        self.assertEqual(listens[1].ts_since_epoch, 1400000150)
        self.assertEqual(listens[2].ts_since_epoch, 1400000100)
        self.assertEqual(listens[3].ts_since_epoch, 1400000050)
        self.assertEqual(listens[4].ts_since_epoch, 1400000000)

    def test_fetch_listens_time_range(self):
        self._create_test_data(self.testuser_name,
                               test_data_file_name='timescale_listenstore_test_listens_over_greater_time_range.json')

        # test to_ts without time_range
        listens = self.logstore.fetch_listens(user_name=self.testuser_name, to_ts=1402000050)
        self.assertEqual(len(listens), 1)
        self.assertEqual(listens[0].ts_since_epoch, 1402000000)

        # test to_ts with time_range=5
        listens = self.logstore.fetch_listens(user_name=self.testuser_name, to_ts=1402000050, time_range=5)
        self.assertEqual(len(listens), 6)
        self.assertEqual(listens[0].ts_since_epoch, 1402000000)
        self.assertEqual(listens[1].ts_since_epoch, 1400000200)
        self.assertEqual(listens[2].ts_since_epoch, 1400000150)
        self.assertEqual(listens[3].ts_since_epoch, 1400000100)
        self.assertEqual(listens[4].ts_since_epoch, 1400000050)
        self.assertEqual(listens[5].ts_since_epoch, 1400000000)

        # test to_ts with time_range=-1
        listens = self.logstore.fetch_listens(user_name=self.testuser_name, to_ts=1402000050, time_range=-1)
        self.assertEqual(len(listens), 7)
        self.assertEqual(listens[0].ts_since_epoch, 1402000000)
        self.assertEqual(listens[1].ts_since_epoch, 1400000200)
        self.assertEqual(listens[2].ts_since_epoch, 1400000150)
        self.assertEqual(listens[3].ts_since_epoch, 1400000100)
        self.assertEqual(listens[4].ts_since_epoch, 1400000050)
        self.assertEqual(listens[5].ts_since_epoch, 1400000000)
        self.assertEqual(listens[6].ts_since_epoch, 1398000000)

        # test from_ts without time_range
        listens = self.logstore.fetch_listens(user_name=self.testuser_name, from_ts=1397999999)
        self.assertEqual(len(listens), 1)
        self.assertEqual(listens[0].ts_since_epoch, 1398000000)

        # test from_ts with time_range=5
        listens = self.logstore.fetch_listens(user_name=self.testuser_name, from_ts=1397999999, time_range=5)
        self.assertEqual(len(listens), 6)
        self.assertEqual(listens[0].ts_since_epoch, 1400000200)
        self.assertEqual(listens[1].ts_since_epoch, 1400000150)
        self.assertEqual(listens[2].ts_since_epoch, 1400000100)
        self.assertEqual(listens[3].ts_since_epoch, 1400000050)
        self.assertEqual(listens[4].ts_since_epoch, 1400000000)
        self.assertEqual(listens[5].ts_since_epoch, 1398000000)

        # test from_ts with time_range=-1
        listens = self.logstore.fetch_listens(user_name=self.testuser_name, from_ts=1397999999, time_range=-1)
        self.assertEqual(len(listens), 7)
        self.assertEqual(listens[0].ts_since_epoch, 1402000000)
        self.assertEqual(listens[1].ts_since_epoch, 1400000200)
        self.assertEqual(listens[2].ts_since_epoch, 1400000150)
        self.assertEqual(listens[3].ts_since_epoch, 1400000100)
        self.assertEqual(listens[4].ts_since_epoch, 1400000050)
        self.assertEqual(listens[5].ts_since_epoch, 1400000000)
        self.assertEqual(listens[6].ts_since_epoch, 1398000000)

    def test_get_listen_count_for_user(self):
        uid = random.randint(2000, 1 << 31)
        testuser = db_user.get_or_create(uid, "user_%d" % uid)
        testuser_name = testuser['musicbrainz_id']

        count = self._create_test_data(testuser_name)
        listen_count = self.logstore.get_listen_count_for_user(user_name=testuser_name)
        self.assertEqual(count, listen_count)

    def test_fetch_recent_listens(self):
        user = db_user.get_or_create(2, 'someuser')
        user_name = user['musicbrainz_id']
        self._create_test_data(user_name)

        user2 = db_user.get_or_create(3, 'otheruser')
        user_name2 = user2['musicbrainz_id']
        self._create_test_data(user_name2)

        recent = self.logstore.fetch_recent_listens_for_users([user_name, user_name2], limit=1, max_age=10000000000)
        self.assertEqual(len(recent), 2)

        recent = self.logstore.fetch_recent_listens_for_users([user_name, user_name2], max_age=10000000000)
        self.assertEqual(len(recent), 4)

        recent = self.logstore.fetch_recent_listens_for_users([user_name], max_age=int(time()) -
                                                              recent[0].ts_since_epoch + 1)
        self.assertEqual(len(recent), 1)
        self.assertEqual(recent[0].ts_since_epoch, 1400000200)

    def test_dump_listens(self):
        self._create_test_data(self.testuser_name)
        temp_dir = tempfile.mkdtemp()
        dump = self.logstore.dump_listens(
            location=temp_dir,
            dump_id=1,
            end_time=datetime.now(),
        )
        self.assertTrue(os.path.isfile(dump))
        shutil.rmtree(temp_dir)

    def test_incremental_dump(self):
        base = 1500000000
        listens = generate_data(1, self.testuser_name, base + 1, 5)  # generate 5 listens with ts 1-5
        self.logstore.insert(listens)
        listens = generate_data(1, self.testuser_name, base + 6, 5)  # generate 5 listens with ts 6-10
        self.logstore.insert(listens)
        temp_dir = tempfile.mkdtemp()
        dump_location = self.logstore.dump_listens(
            location=temp_dir,
            dump_id=1,
            start_time=datetime.utcfromtimestamp(base + 6),
            end_time=datetime.utcfromtimestamp(base + 10)
        )
        self.assertTrue(os.path.isfile(dump_location))
        self.reset_timescale_db()
        self.logstore.import_listens_dump(dump_location)
        listens = self.logstore.fetch_listens(user_name=self.testuser_name, to_ts=base + 11)
        self.assertEqual(len(listens), 5)
        self.assertEqual(listens[0].ts_since_epoch, base + 10)
        self.assertEqual(listens[1].ts_since_epoch, base + 9)
        self.assertEqual(listens[2].ts_since_epoch, base + 8)
        self.assertEqual(listens[3].ts_since_epoch, base + 7)
        self.assertEqual(listens[4].ts_since_epoch, base + 6)

        shutil.rmtree(temp_dir)

    def test_time_range_full_dumps(self):
        base = 1500000000
        listens = generate_data(1, self.testuser_name, base + 1, 5)  # generate 5 listens with ts 1-5
        self.logstore.insert(listens)
        listens = generate_data(1, self.testuser_name, base + 6, 5)  # generate 5 listens with ts 6-10
        self.logstore.insert(listens)
        temp_dir = tempfile.mkdtemp()
        dump_location = self.logstore.dump_listens(
            location=temp_dir,
            dump_id=1,
            end_time=datetime.utcfromtimestamp(base + 5)
        )
        self.assertTrue(os.path.isfile(dump_location))
        self.reset_timescale_db()
        self.logstore.import_listens_dump(dump_location)
        listens = self.logstore.fetch_listens(user_name=self.testuser_name, to_ts=base + 11)
        self.assertEqual(len(listens), 5)
        self.assertEqual(listens[0].ts_since_epoch, base + 5)
        self.assertEqual(listens[1].ts_since_epoch, base + 4)
        self.assertEqual(listens[2].ts_since_epoch, base + 3)
        self.assertEqual(listens[3].ts_since_epoch, base + 2)
        self.assertEqual(listens[4].ts_since_epoch, base + 1)

    # tests test_full_dump_listen_with_no_created
    # and test_incremental_dumps_listen_with_no_created have been removed because
    # with timescale all the missing inserted timestamps will have been
    # been assigned sane created timestamps by the migration script
    # and timescale will not allow blank created timestamps, so this test is pointless

    def test_import_listens(self):
        self._create_test_data(self.testuser_name)
        temp_dir = tempfile.mkdtemp()
        dump_location = self.logstore.dump_listens(
            location=temp_dir,
            dump_id=1,
            end_time=datetime.now(),
        )
        self.assertTrue(os.path.isfile(dump_location))
        self.reset_timescale_db()
        self.logstore.import_listens_dump(dump_location)
        listens = self.logstore.fetch_listens(user_name=self.testuser_name, to_ts=1400000300)
        self.assertEqual(len(listens), 5)
        self.assertEqual(listens[0].ts_since_epoch, 1400000200)
        self.assertEqual(listens[1].ts_since_epoch, 1400000150)
        self.assertEqual(listens[2].ts_since_epoch, 1400000100)
        self.assertEqual(listens[3].ts_since_epoch, 1400000050)
        self.assertEqual(listens[4].ts_since_epoch, 1400000000)
        shutil.rmtree(temp_dir)

    def test_dump_and_import_listens_escaped(self):
        user = db_user.get_or_create(3, 'i have a\\weird\\user, na/me"\n')
        self._create_test_data(user['musicbrainz_id'])

        self._create_test_data(self.testuser_name)

        temp_dir = tempfile.mkdtemp()
        dump_location = self.logstore.dump_listens(
            location=temp_dir,
            dump_id=1,
            end_time=datetime.now(),
        )
        self.assertTrue(os.path.isfile(dump_location))
        self.reset_timescale_db()

        self.logstore.import_listens_dump(dump_location)

        listens = self.logstore.fetch_listens(user_name=user['musicbrainz_id'], to_ts=1400000300)
        self.assertEqual(len(listens), 5)
        self.assertEqual(listens[0].ts_since_epoch, 1400000200)
        self.assertEqual(listens[1].ts_since_epoch, 1400000150)
        self.assertEqual(listens[2].ts_since_epoch, 1400000100)
        self.assertEqual(listens[3].ts_since_epoch, 1400000050)
        self.assertEqual(listens[4].ts_since_epoch, 1400000000)

        listens = self.logstore.fetch_listens(user_name=self.testuser_name, to_ts=1400000300)
        self.assertEqual(len(listens), 5)
        self.assertEqual(listens[0].ts_since_epoch, 1400000200)
        self.assertEqual(listens[1].ts_since_epoch, 1400000150)
        self.assertEqual(listens[2].ts_since_epoch, 1400000100)
        self.assertEqual(listens[3].ts_since_epoch, 1400000050)
        self.assertEqual(listens[4].ts_since_epoch, 1400000000)
        shutil.rmtree(temp_dir)

    # test test_import_dump_many_users is gone -- why are we testing user dump/restore here??

    def create_test_dump(self, archive_name, archive_path, schema_version=None):
        """ Creates a test dump to test the import listens functionality.

        Args:
            archive_name (str): the name of the archive
            archive_path (str): the full path to the archive
            schema_version (int): the version of the schema to be written into SCHEMA_SEQUENCE
                                  if not provided, the SCHEMA_SEQUENCE file is not added to the archive

        Returns:
            the full path to the archive created
        """

        temp_dir = tempfile.mkdtemp()
        with tarfile.open(archive_path, mode='w|xz') as tar:
            schema_version_path = os.path.join(temp_dir, 'SCHEMA_SEQUENCE')
            with open(schema_version_path, 'w') as f:
                f.write(str(schema_version or ' '))
            tar.add(schema_version_path,
                    arcname=os.path.join(archive_name, 'SCHEMA_SEQUENCE'))

        return archive_path

    def test_schema_mismatch_exception_for_dump_incorrect_schema(self):
        """ Tests that SchemaMismatchException is raised when the schema of the dump is old """

        # create a temp archive with incorrect SCHEMA_VERSION
        temp_dir = tempfile.mkdtemp()
        archive_name = 'temp_dump'
        archive_path = os.path.join(temp_dir, archive_name + '.tar.xz')
        archive_path = self.create_test_dump(
            archive_name=archive_name,
            archive_path=archive_path,
            schema_version=LISTENS_DUMP_SCHEMA_VERSION - 1
        )
        with self.assertRaises(SchemaMismatchException):
            self.logstore.import_listens_dump(archive_path)

    def test_schema_mismatch_exception_for_dump_no_schema(self):
        """ Tests that SchemaMismatchException is raised when there is no schema version in the archive """

        temp_dir = tempfile.mkdtemp()
        archive_name = 'temp_dump'
        archive_path = os.path.join(temp_dir, archive_name + '.tar.xz')

        archive_path = self.create_test_dump(
            archive_name=archive_name,
            archive_path=archive_path,
            schema_version=None
        )

        with self.assertRaises(SchemaMismatchException):
            self.logstore.import_listens_dump(archive_path)

    def test_listen_counts_in_cache(self):
        count = self._create_test_data(self.testuser_name)
        self.assertEqual(count, self.logstore.get_listen_count_for_user(self.testuser_name, need_exact=True))
        user_key = '{}{}'.format(self.ns + REDIS_TIMESCALE_USER_LISTEN_COUNT, self.testuser_name)
        self.assertEqual(count, int(cache.get(user_key, decode=False)))

        batch = generate_data(self.testuser_id, self.testuser_name, int(time()), 1)
        self.logstore.insert(batch)
        self.assertEqual(count + 1, int(cache.get(user_key, decode=False)))

    def test_delete_listens(self):
        self._create_test_data(self.testuser_name)
        listens = self.logstore.fetch_listens(user_name=self.testuser_name, to_ts=1400000300)
        self.assertEqual(len(listens), 5)
        self.assertEqual(listens[0].ts_since_epoch, 1400000200)
        self.assertEqual(listens[1].ts_since_epoch, 1400000150)
        self.assertEqual(listens[2].ts_since_epoch, 1400000100)
        self.assertEqual(listens[3].ts_since_epoch, 1400000050)
        self.assertEqual(listens[4].ts_since_epoch, 1400000000)

        self.logstore.delete(self.testuser_name)
        listens = self.logstore.fetch_listens(user_name=self.testuser_name, to_ts=1400000300)
        self.assertEqual(len(listens), 0)

    def test_delete_listens_escaped(self):
        user = db_user.get_or_create(213, 'i have a\\weird\\user, na/me"\n')
        self._create_test_data(user['musicbrainz_id'])
        listens = self.logstore.fetch_listens(user_name=user['musicbrainz_id'], to_ts=1400000300)
        self.assertEqual(len(listens), 5)
        self.assertEqual(listens[0].ts_since_epoch, 1400000200)
        self.assertEqual(listens[1].ts_since_epoch, 1400000150)
        self.assertEqual(listens[2].ts_since_epoch, 1400000100)
        self.assertEqual(listens[3].ts_since_epoch, 1400000050)
        self.assertEqual(listens[4].ts_since_epoch, 1400000000)

        self.logstore.delete(user['musicbrainz_id'])
        listens = self.logstore.fetch_listens(user_name=user['musicbrainz_id'], to_ts=1400000300)
        self.assertEqual(len(listens), 0)
