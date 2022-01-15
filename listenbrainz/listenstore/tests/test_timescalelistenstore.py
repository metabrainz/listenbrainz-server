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
from psycopg2.extras import execute_values
from listenbrainz.db.testing import DatabaseTestCase
from listenbrainz.db import timescale as ts
from listenbrainz import config
from listenbrainz.listenstore.tests.util import create_test_data_for_timescalelistenstore, generate_data
from listenbrainz.webserver.timescale_connection import init_timescale_connection
from listenbrainz.db.dump import SchemaMismatchException
from listenbrainz.listenstore import LISTENS_DUMP_SCHEMA_VERSION
from listenbrainz.listenstore.timescale_listenstore import REDIS_USER_LISTEN_COUNT, REDIS_USER_TIMESTAMPS
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
        ts.run_sql_script(os.path.join(TIMESCALE_SQL_DIR, 'create_types.sql'))
        ts.run_sql_script(os.path.join(TIMESCALE_SQL_DIR, 'create_tables.sql'))
        ts.run_sql_script(os.path.join(TIMESCALE_SQL_DIR, 'create_functions.sql'))
        ts.run_sql_script_without_transaction(os.path.join(TIMESCALE_SQL_DIR, 'create_views.sql'))
        ts.run_sql_script(os.path.join(TIMESCALE_SQL_DIR, 'create_indexes.sql'))
        ts.create_view_indexes()
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
        cache._r.flushdb()
        super(TestTimescaleListenStore, self).tearDown()

    def _create_test_data(self, user_name, user_id, test_data_file_name=None):
        test_data = create_test_data_for_timescalelistenstore(user_name, user_id, test_data_file_name)
        self.logstore.insert(test_data)
        return len(test_data)

    def _insert_mapping_metadata(self, msid):
        """ Insert mapping test data into the mapping tables """

        query = """INSERT INTO mbid_mapping_metadata
                               (recording_mbid, release_mbid, release_name, artist_credit_id, 
                                artist_mbids, artist_credit_name, recording_name)
                        VALUES ('076255b4-1575-11ec-ac84-135bf6a670e3',
                                '1fd178b4-1575-11ec-b98a-d72392cd8c97',
                                'release_name',
                                65,
                                '{6a221fda-2200-11ec-ac7d-dfa16a57158f}'::UUID[],
                                'artist name', 'recording name')"""

        join_query = """INSERT INTO mbid_mapping
                               (recording_msid, recording_mbid, match_type)
                        VALUES ('%s', '%s', 'exact_match')""" % (msid, '076255b4-1575-11ec-ac84-135bf6a670e3')

        with ts.engine.connect() as connection:
            connection.execute(sqlalchemy.text(query))
            connection.execute(sqlalchemy.text(join_query))

    def _insert_with_created(self, listens):
        """ Insert a batch of listens with 'created' field.
        """
        submit = []
        for listen in listens:
            submit.append((*listen.to_timescale(), listen.inserted_timestamp))

        query = """INSERT INTO listen (listened_at, track_name, user_name, user_id, data, created)
                        VALUES %s
                   ON CONFLICT (listened_at, track_name, user_id)
                    DO NOTHING
                """

        conn = ts.engine.raw_connection()
        with conn.cursor() as curs:
            execute_values(curs, query, submit, template=None)

        conn.commit()

    def test_check_listen_count_view_exists(self):
        try:
            with ts.engine.connect() as connection:
                result = connection.execute(sqlalchemy.text("""SELECT column_name
                                                                 FROM information_schema.columns
                                                                WHERE table_name = 'listen_count_30day'
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
        count = self._create_test_data(self.testuser_name, self.testuser_id)
        listens, min_ts, max_ts = self.logstore.fetch_listens(user_id=self.testuser_id, from_ts=1399999999)
        self.assertEqual(len(listens), count)

    def test_fetch_listens_0(self):
        self._create_test_data(self.testuser_name, self.testuser_id)
        listens, min_ts, max_ts = self.logstore.fetch_listens(user_id=self.testuser_id, from_ts=1400000000, limit=1)
        self.assertEqual(len(listens), 1)
        self.assertEqual(listens[0].ts_since_epoch, 1400000050)
        self.assertEqual(min_ts, 1400000000)
        self.assertEqual(max_ts, 1400000200)

    def test_fetch_listens_1(self):
        self._create_test_data(self.testuser_name, self.testuser_id)
        listens, min_ts, max_ts = self.logstore.fetch_listens(user_id=self.testuser_id, from_ts=1400000000)
        self.assertEqual(len(listens), 4)
        self.assertEqual(listens[0].ts_since_epoch, 1400000200)
        self.assertEqual(listens[1].ts_since_epoch, 1400000150)
        self.assertEqual(listens[2].ts_since_epoch, 1400000100)
        self.assertEqual(listens[3].ts_since_epoch, 1400000050)

    def test_fetch_listens_2(self):
        self._create_test_data(self.testuser_name, self.testuser_id)
        listens, min_ts, max_ts = self.logstore.fetch_listens(user_id=self.testuser_id, from_ts=1400000100)
        self.assertEqual(len(listens), 2)
        self.assertEqual(listens[0].ts_since_epoch, 1400000200)
        self.assertEqual(listens[1].ts_since_epoch, 1400000150)

    def test_fetch_listens_3(self):
        self._create_test_data(self.testuser_name, self.testuser_id)
        listens, min_ts, max_ts = self.logstore.fetch_listens(user_id=self.testuser_id, to_ts=1400000300)
        self.assertEqual(len(listens), 5)
        self.assertEqual(listens[0].ts_since_epoch, 1400000200)
        self.assertEqual(listens[1].ts_since_epoch, 1400000150)
        self.assertEqual(listens[2].ts_since_epoch, 1400000100)
        self.assertEqual(listens[3].ts_since_epoch, 1400000050)
        self.assertEqual(listens[4].ts_since_epoch, 1400000000)

    def test_fetch_listens_4(self):
        self._create_test_data(self.testuser_name, self.testuser_id)
        listens, min_ts, max_ts = self.logstore.fetch_listens(user_id=self.testuser_id, from_ts=1400000049, to_ts=1400000101)
        self.assertEqual(len(listens), 2)
        self.assertEqual(listens[0].ts_since_epoch, 1400000100)
        self.assertEqual(listens[1].ts_since_epoch, 1400000050)

    def test_fetch_listens_5(self):
        self._create_test_data(self.testuser_name, self.testuser_id)
        with self.assertRaises(ValueError):
            self.logstore.fetch_listens(user_id=self.testuser_id, from_ts=1400000101, to_ts=1400000001)

    def test_fetch_listens_with_gaps(self):
        self._create_test_data(self.testuser_name, self.testuser_id,
                               test_data_file_name='timescale_listenstore_test_listens_over_greater_time_range.json')

        # test from_ts with gaps
        listens, min_ts, max_ts = self.logstore.fetch_listens(user_id=self.testuser_id, from_ts=1399999999)
        self.assertEqual(len(listens), 4)
        self.assertEqual(listens[0].ts_since_epoch, 1420000050)
        self.assertEqual(listens[1].ts_since_epoch, 1420000000)
        self.assertEqual(listens[2].ts_since_epoch, 1400000050)
        self.assertEqual(listens[3].ts_since_epoch, 1400000000)

        # test from_ts and to_ts with gaps
        listens, min_ts, max_ts = self.logstore.fetch_listens(user_id=self.testuser_id, from_ts=1400000049, to_ts=1420000001)
        self.assertEqual(len(listens), 2)
        self.assertEqual(listens[0].ts_since_epoch, 1420000000)
        self.assertEqual(listens[1].ts_since_epoch, 1400000050)

        # test to_ts with gaps
        listens, min_ts, max_ts = self.logstore.fetch_listens(user_id=self.testuser_id, to_ts=1420000051)
        self.assertEqual(len(listens), 4)
        self.assertEqual(listens[0].ts_since_epoch, 1420000050)
        self.assertEqual(listens[1].ts_since_epoch, 1420000000)
        self.assertEqual(listens[2].ts_since_epoch, 1400000050)
        self.assertEqual(listens[3].ts_since_epoch, 1400000000)

    def test_fetch_listens_with_mapping(self):
        self._create_test_data(self.testuser_name, self.testuser_id)
        self._insert_mapping_metadata("c7a41965-9f1e-456c-8b1d-27c0f0dde280")
        listens, min_ts, max_ts = self.logstore.fetch_listens(user_id=self.testuser_id, from_ts=1400000000, limit=1)
        self.assertEqual(len(listens), 1)
        self.assertEqual(listens[0].data["mbid_mapping"]["artist_mbids"], ['6a221fda-2200-11ec-ac7d-dfa16a57158f'])
        self.assertEqual(listens[0].data["mbid_mapping"]["release_mbid"], '1fd178b4-1575-11ec-b98a-d72392cd8c97')
        self.assertEqual(listens[0].data["mbid_mapping"]["recording_mbid"], '076255b4-1575-11ec-ac84-135bf6a670e3')

    def test_get_listen_count_for_user(self):
        uid = random.randint(2000, 1 << 31)
        testuser = db_user.get_or_create(uid, "user_%d" % uid)
        testuser_name = testuser['musicbrainz_id']

        count = self._create_test_data(testuser_name, testuser["id"])
        listen_count = self.logstore.get_listen_count_for_user(testuser["id"])
        self.assertEqual(count, listen_count)

    def test_fetch_recent_listens(self):
        user = db_user.get_or_create(2, 'someuser')
        user_name = user['musicbrainz_id']
        self._create_test_data(user_name, user["id"])

        user2 = db_user.get_or_create(3, 'otheruser')
        user_name2 = user2['musicbrainz_id']
        self._create_test_data(user_name2, user2["id"])

        recent = self.logstore.fetch_recent_listens_for_users([user["id"], user2["id"]], limit=1, max_age=10000000000)
        self.assertEqual(len(recent), 2)

        recent = self.logstore.fetch_recent_listens_for_users([user["id"], user2["id"]], max_age=10000000000)
        self.assertEqual(len(recent), 4)

        recent = self.logstore.fetch_recent_listens_for_users([user["id"]], max_age=int(time()) -
                                                              recent[0].ts_since_epoch + 1)
        self.assertEqual(len(recent), 1)
        self.assertEqual(recent[0].ts_since_epoch, 1400000200)

    def test_dump_listens(self):
        self._create_test_data(self.testuser_name, self.testuser_id)
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
        listens = generate_data(1, self.testuser_name, base-4, 5, base+1)  # generate 5 listens with inserted_ts 1-5
        self._insert_with_created(listens)
        listens = generate_data(1, self.testuser_name, base+1, 5, base+6)  # generate 5 listens with inserted_ts 6-10
        self._insert_with_created(listens)
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
        listens, min_ts, max_ts = self.logstore.fetch_listens(user_id=self.testuser_id, to_ts=base + 11)
        self.assertEqual(len(listens), 4)
        self.assertEqual(listens[0].ts_since_epoch, base + 5)
        self.assertEqual(listens[1].ts_since_epoch, base + 4)
        self.assertEqual(listens[2].ts_since_epoch, base + 3)
        self.assertEqual(listens[3].ts_since_epoch, base + 2)

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
        listens, min_ts, max_ts = self.logstore.fetch_listens(user_id=self.testuser_id, to_ts=base + 11)
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
        self._create_test_data(self.testuser_name, self.testuser_id)
        temp_dir = tempfile.mkdtemp()
        dump_location = self.logstore.dump_listens(
            location=temp_dir,
            dump_id=1,
            end_time=datetime.now(),
        )
        self.assertTrue(os.path.isfile(dump_location))
        self.reset_timescale_db()
        self.logstore.import_listens_dump(dump_location)
        listens, min_ts, max_ts = self.logstore.fetch_listens(user_id=self.testuser_id, to_ts=1400000300)
        self.assertEqual(len(listens), 5)
        self.assertEqual(listens[0].ts_since_epoch, 1400000200)
        self.assertEqual(listens[1].ts_since_epoch, 1400000150)
        self.assertEqual(listens[2].ts_since_epoch, 1400000100)
        self.assertEqual(listens[3].ts_since_epoch, 1400000050)
        self.assertEqual(listens[4].ts_since_epoch, 1400000000)
        shutil.rmtree(temp_dir)

    def test_dump_and_import_listens_escaped(self):
        user = db_user.get_or_create(3, 'i have a\\weird\\user, na/me"\n')
        self._create_test_data(user['musicbrainz_id'], user['id'])

        self._create_test_data(self.testuser_name, self.testuser_id)

        temp_dir = tempfile.mkdtemp()
        dump_location = self.logstore.dump_listens(
            location=temp_dir,
            dump_id=1,
            end_time=datetime.now(),
        )
        self.assertTrue(os.path.isfile(dump_location))
        self.reset_timescale_db()

        self.logstore.import_listens_dump(dump_location)

        listens, min_ts, max_ts = self.logstore.fetch_listens(user_id=user['id'], to_ts=1400000300)
        self.assertEqual(len(listens), 5)
        self.assertEqual(listens[0].ts_since_epoch, 1400000200)
        self.assertEqual(listens[1].ts_since_epoch, 1400000150)
        self.assertEqual(listens[2].ts_since_epoch, 1400000100)
        self.assertEqual(listens[3].ts_since_epoch, 1400000050)
        self.assertEqual(listens[4].ts_since_epoch, 1400000000)

        listens, min_ts, max_ts = self.logstore.fetch_listens(user_id=self.testuser_id, to_ts=1400000300)
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

        # create a temp archive with incorrect SCHEMA_VERSION_CORE
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
        uid = random.randint(2000, 1 << 31)
        testuser = db_user.get_or_create(uid, "user_%d" % uid)
        testuser_name = testuser['musicbrainz_id']
        count = self._create_test_data(testuser_name, testuser["id"])
        user_key = REDIS_USER_LISTEN_COUNT + str(testuser["id"])
        self.assertEqual(count, self.logstore.get_listen_count_for_user(testuser["id"]))
        self.assertEqual(count, int(cache.get(user_key, decode=False) or 0))

        batch = generate_data(uid, testuser_name, int(time()), 1)
        self.logstore.insert(batch)
        self.assertEqual(count + 1, int(cache.get(user_key, decode=False) or 0))

    def test_delete_listens(self):
        uid = random.randint(2000, 1 << 31)
        testuser = db_user.get_or_create(uid, "user_%d" % uid)
        testuser_name = testuser['musicbrainz_id']
        self._create_test_data(testuser_name, testuser["id"])
        listens, min_ts, max_ts = self.logstore.fetch_listens(user_id=testuser["id"], to_ts=1400000300)
        self.assertEqual(len(listens), 5)
        self.assertEqual(listens[0].ts_since_epoch, 1400000200)
        self.assertEqual(listens[1].ts_since_epoch, 1400000150)
        self.assertEqual(listens[2].ts_since_epoch, 1400000100)
        self.assertEqual(listens[3].ts_since_epoch, 1400000050)
        self.assertEqual(listens[4].ts_since_epoch, 1400000000)

        self.logstore.delete(testuser["id"])
        listens, min_ts, max_ts = self.logstore.fetch_listens(user_id=testuser["id"], to_ts=1400000300)
        self.assertEqual(len(listens), 0)

    def test_delete_single_listen(self):
        uid = random.randint(2000, 1 << 31)
        testuser = db_user.get_or_create(uid, "user_%d" % uid)
        testuser_name = testuser['musicbrainz_id']
        self._create_test_data(testuser_name, testuser["id"])
        listens, min_ts, max_ts = self.logstore.fetch_listens(user_id=testuser["id"], to_ts=1400000300)
        self.assertEqual(len(listens), 5)
        self.assertEqual(listens[0].ts_since_epoch, 1400000200)
        self.assertEqual(listens[1].ts_since_epoch, 1400000150)
        self.assertEqual(listens[2].ts_since_epoch, 1400000100)
        self.assertEqual(listens[3].ts_since_epoch, 1400000050)
        self.assertEqual(listens[4].ts_since_epoch, 1400000000)

        self.logstore.delete_listen(1400000050, testuser["id"], "c7a41965-9f1e-456c-8b1d-27c0f0dde280")
        listens, min_ts, max_ts = self.logstore.fetch_listens(user_id=testuser["id"], to_ts=1400000300)
        self.assertEqual(len(listens), 4)
        self.assertEqual(listens[0].ts_since_epoch, 1400000200)
        self.assertEqual(listens[1].ts_since_epoch, 1400000150)
        self.assertEqual(listens[2].ts_since_epoch, 1400000100)
        self.assertEqual(listens[3].ts_since_epoch, 1400000000)

        self.assertEqual(self.logstore.get_listen_count_for_user(testuser["id"]), 4)
        min_ts, max_ts = self.logstore.get_timestamps_for_user(testuser["id"])
        self.assertEqual(min_ts, 1400000000)
        self.assertEqual(max_ts, 1400000200)

    def test_for_empty_timestamps(self):
        """
            Even if a user has no listens they should have the sentinel timestamps of 0,0 stored in the
            cache to avoid continually recomputing them
        """
        uid = random.randint(2000, 1 << 31)
        testuser = db_user.get_or_create(uid, "user_%d" % uid)
        min_ts, max_ts = self.logstore.get_timestamps_for_user(testuser["id"])
        self.assertEqual(min_ts, 0)
        self.assertEqual(max_ts, 0)
        self.assertEqual(cache.get(REDIS_USER_TIMESTAMPS + str(testuser["id"])), "0,0")
