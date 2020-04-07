# coding=utf-8

import listenbrainz.db.user as db_user
import os
import time
import ujson
import logging
import psycopg2
from psycopg2.extras import execute_values
import sqlalchemy
import shutil
import subprocess
import tarfile
import tempfile

from time import sleep
from datetime import datetime
from listenbrainz.db.testing import DatabaseTestCase
from listenbrainz.db import timescale as ts
from listenbrainz import config
from listenbrainz.listenstore.tests.util import create_test_data_for_timescalelistenstore, generate_data
from listenbrainz.webserver.timescale_connection import init_ts_connection
from listenbrainz.utils import quote
from listenbrainz.db.dump import SchemaMismatchException
from listenbrainz.listenstore import TimescaleListenStore, LISTENS_DUMP_SCHEMA_VERSION
from listenbrainz.listenstore.timescale_listenstore import REDIS_TIMESCALE_USER_LISTEN_COUNT


TIMESCALE_SQL_DIR = os.path.join(os.path.dirname(os.path.realpath(__file__)), '..', '..', '..', 'admin', 'timescale')

class TestTimescaleListenStore(DatabaseTestCase):


    def reset_timescale_db(self):

        ts.init_db_connection(config.TIMESCALE_ADMIN_URI)
        ts.run_sql_script_without_transaction(os.path.join(TIMESCALE_SQL_DIR, 'drop_db.sql'))
        ts.run_sql_script_without_transaction(os.path.join(TIMESCALE_SQL_DIR, 'create_db.sql'))

        ts.init_db_connection(config.TIMESCALE_ADMIN_LB_URI)
        ts.run_sql_script_without_transaction(os.path.join(TIMESCALE_SQL_DIR, 'create_extensions.sql'))
        ts.run_sql_script(os.path.join(TIMESCALE_SQL_DIR, 'create_tables.sql'))
        ts.run_sql_script(os.path.join(TIMESCALE_SQL_DIR, 'create_functions.sql'))
        ts.run_sql_script(os.path.join(TIMESCALE_SQL_DIR, 'create_views.sql'))
        ts.run_sql_script(os.path.join(TIMESCALE_SQL_DIR, 'create_indexes.sql'))


    def setUp(self):
        super(TestTimescaleListenStore, self).setUp()
        self.log = logging.getLogger(__name__)
        self.reset_timescale_db()
        
        self.logstore = init_ts_connection(self.log, {
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

    def _create_test_data(self, user_name):
        test_data = create_test_data_for_timescalelistenstore(user_name)
        self.logstore.insert(test_data)
        return len(test_data)

    def test_check_listen_count_view_exists(self):
        try:
            with ts.engine.connect() as connection:
                result = connection.execute(sqlalchemy.text("SELECT column_name FROM information_schema.columns WHERE table_name = 'listen_count'"))
                cols = result.fetchall()
        except psycopg2.OperationalError as e:
            self.log.error("Cannot query timescale listen_count: %s" % str(e), exc_info=True)
            raise
        self.assertEqual(cols[0][0], "bucket")
        self.assertEqual(cols[1][0], "user_name")
        self.assertEqual(cols[2][0], "count")

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

#    def test_get_listen_count_for_user(self):
#        count = self._create_test_data(self.testuser_name)
#
#        # The listen_counts in the database will always be lagging behind and will not be fully
#        # accurate, but they will give a good indication for the number of listens of a user.
#        # This means that we can't insert data data and expect it to be in the DB right away
#        # so we can fetch them for running tests
#        listen_count = self.logstore.get_listen_count_for_user(user_name=self.testuser_name)
#        self.assertEqual(count, listen_count)

    def test_fetch_listens_escaped(self):
        user = db_user.get_or_create(2, 'i have a\\weird\\user, name"\n')
        user_name = user['musicbrainz_id']
        self._create_test_data(user_name)
        listens = self.logstore.fetch_listens(user_name=user_name, from_ts=1400000100)
        self.assertEqual(len(listens), 2)
        self.assertEqual(listens[0].ts_since_epoch, 1400000200)
        self.assertEqual(listens[1].ts_since_epoch, 1400000150)

    def test_fetch_recent_listens(self): #fails
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

        recent = self.logstore.fetch_recent_listens_for_users([user_name], max_age = int(time.time()) - recent[0].ts_since_epoch + 1)
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

    def test_dump_listens_spark_format(self):
        expected_count = self._create_test_data(self.testuser_name)
        time.sleep(1)
        temp_dir = tempfile.mkdtemp()
        dump = self.logstore.dump_listens(
            location=temp_dir,
            dump_id=1,
            spark_format=True,
            end_time=datetime.now(),
        )
        self.assertTrue(os.path.isfile(dump))
        self.assert_spark_dump_contains_listens(dump, expected_count)
        shutil.rmtree(temp_dir)

    def assert_spark_dump_contains_listens(self, dump, expected_listen_count):
        """ This method checks that the spark dump specified contains the
        expected number of listens. We also do some schema checks for the
        listens here too
        """
        pxz_command = ['pxz', '--decompress', '--stdout', dump]
        pxz = subprocess.Popen(pxz_command, stdout=subprocess.PIPE)

        listen_count = 0
        with tarfile.open(fileobj=pxz.stdout, mode='r|') as tar:
            for member in tar:
                file_name = member.name.split('/')[-1]
                if file_name.endswith('.json'):
                    for line in tar.extractfile(member).readlines():
                        listen = ujson.loads(line)
                        self.assertIn('inserted_timestamp', listen)
                        listen_count += 1
        self.assertEqual(listen_count, expected_listen_count)

    def test_incremental_dump(self):
        listens = generate_data(1, self.testuser_name, 1, 5) # generate 5 listens with ts 1-5
        self.logstore.insert(listens)
        sleep(1)
        start_time = datetime.now()
        sleep(1)
        listens = generate_data(1, self.testuser_name, 6, 5) # generate 5 listens with ts 6-10
        self.logstore.insert(listens)
        sleep(1)
        temp_dir = tempfile.mkdtemp()
        dump_location = self.logstore.dump_listens(
            location=temp_dir,
            dump_id=1,
            start_time=start_time,
            end_time=datetime.now(),
        )
        spark_dump_location = self.logstore.dump_listens(
            location=temp_dir,
            dump_id=1,
            start_time=start_time,
            end_time=datetime.now(),
            spark_format=True,
        )
        sleep(1)
        self.assertTrue(os.path.isfile(dump_location))
        self.assertTrue(os.path.isfile(spark_dump_location))
        self.reset_timescale_db()
        sleep(1)
        self.logstore.import_listens_dump(dump_location)
        sleep(1)
        listens = self.logstore.fetch_listens(user_name=self.testuser_name, to_ts=11)
        self.assertEqual(len(listens), 5)
        self.assertEqual(listens[0].ts_since_epoch, 10)
        self.assertEqual(listens[1].ts_since_epoch, 9)
        self.assertEqual(listens[2].ts_since_epoch, 8)
        self.assertEqual(listens[3].ts_since_epoch, 7)
        self.assertEqual(listens[4].ts_since_epoch, 6)

        self.assert_spark_dump_contains_listens(spark_dump_location, 5)
        shutil.rmtree(temp_dir)

    def test_time_range_full_dumps(self): # fails because 1-11 < between_time always
        listens = generate_data(1, self.testuser_name, 1, 5) # generate 5 listens with ts 1-5
        self.logstore.insert(listens)
        sleep(1)
        between_time = datetime.now()
        sleep(1)
        listens = generate_data(1, self.testuser_name, 6, 5) # generate 5 listens with ts 6-10
        self.logstore.insert(listens)
        sleep(1)
        temp_dir = tempfile.mkdtemp()
        dump_location = self.logstore.dump_listens(
            location=temp_dir,
            dump_id=1,
            end_time=between_time,
        )
        spark_dump_location = self.logstore.dump_listens(
            location=temp_dir,
            dump_id=1,
            end_time=between_time,
            spark_format=True,
        )
        sleep(1)
        self.assertTrue(os.path.isfile(dump_location))
        self.reset_timescale_db()
        sleep(1)
        self.logstore.import_listens_dump(dump_location)
        sleep(1)
        listens = self.logstore.fetch_listens(user_name=self.testuser_name, to_ts=11)
        self.assertEqual(len(listens), 5)
        self.assertEqual(listens[0].ts_since_epoch, 5)
        self.assertEqual(listens[1].ts_since_epoch, 4)
        self.assertEqual(listens[2].ts_since_epoch, 3)
        self.assertEqual(listens[3].ts_since_epoch, 2)
        self.assertEqual(listens[4].ts_since_epoch, 1)

        # This test fails. We insert listened_at from 1-10 using generate_data() (*see line 238 and 243 in this file*).
        # Now we pass between_time as end_time. This end_time value is converted to int (*see line 415 in timescale_listenstore.py*) which will be 15xxxxxxxx.
        # This 15xxxxxxxx is used as listened_at (*see line 287 and 294 in timescale_listenstore.py*). All 1-10 are less than 15xxxxxxxx so all get into the dump.
        # So we get 10 entries instread of 5. We cannot pass 5 as between_time because db_user.get_all_users(columns=['id', 'musicbrainz_id'], created_before=end_time) needs end_time which should be datetime value (*see line 626 in timescale_listenstore.py*).

    def test_full_dump_listen_with_no_insert_timestamp(self):
        """ We have listens with no `inserted_timestamps` inside the production
        database. This means that full dumps should always be able to dump these
        listens as well. This is a test to test that.
        """
        listens = generate_data(1, self.testuser_name, 1, 5)

        # insert these listens into influx without an insert_timestamp
        influx_rows = [listen.to_influx(quote(self.testuser_name)) for listen in listens]
        for row in influx_rows[1:]:
            row['fields'].pop('inserted_timestamp')

        t = datetime.now()
        self.logstore.write_points_to_db(influx_rows)
        sleep(1)
        listens_from_influx = self.logstore.fetch_listens(user_name=self.testuser_name, to_ts=11)
        self.assertEqual(len(listens_from_influx), 5)

        # full dump (with no start time) should contain these listens
        temp_dir = tempfile.mkdtemp()
        dump_location = self.logstore.dump_listens(
            location=temp_dir,
            dump_id=1,
            end_time=datetime.now(),
        )
        spark_dump_location = self.logstore.dump_listens(
            location=temp_dir,
            dump_id=1,
            end_time=datetime.now(),
            spark_format=True,
        )
        self.assertTrue(os.path.isfile(dump_location))
        self.reset_influx_db()
        sleep(1)
        self.logstore.import_listens_dump(dump_location)
        sleep(1)
        listens_from_influx = self.logstore.fetch_listens(user_name=self.testuser_name, to_ts=11)
        self.assertEqual(len(listens_from_influx), 5)
        self.assert_spark_dump_contains_listens(spark_dump_location, 5)
        shutil.rmtree(temp_dir)

    def test_incremental_dumps_listen_with_no_insert_timestamp(self):
        """ Incremental dumps should only consider listens that have
        inserted_timestamps.
        """
        t = datetime.now()
        sleep(1)
        listens = generate_data(1, self.testuser_name, 1, 5)

        # insert these listens into influx without an insert_timestamp
        influx_rows = [listen.to_influx(quote(self.testuser_name)) for listen in listens]
        for row in influx_rows[1:]:
            row['fields'].pop('inserted_timestamp')

        self.logstore.write_points_to_db(influx_rows)
        sleep(1)
        listens_from_influx = self.logstore.fetch_listens(user_name=self.testuser_name, to_ts=11)
        self.assertEqual(len(listens_from_influx), 5)

        # incremental dump (with a start time) should not contain these listens
        temp_dir = tempfile.mkdtemp()
        dump_location = self.logstore.dump_listens(
            location=temp_dir,
            dump_id=1,
            start_time=t,
            end_time=datetime.now(),
        )
        spark_dump_location = self.logstore.dump_listens(
            location=temp_dir,
            dump_id=1,
            start_time=t,
            end_time=datetime.now(),
            spark_format=True,
        )
        self.assertTrue(os.path.isfile(dump_location))
        self.reset_influx_db()
        sleep(1)
        self.logstore.import_listens_dump(dump_location)
        sleep(1)
        listens_from_influx = self.logstore.fetch_listens(user_name=self.testuser_name, to_ts=11)
        self.assertEqual(len(listens_from_influx), 1)
        self.assert_spark_dump_contains_listens(spark_dump_location, 1)
        shutil.rmtree(temp_dir)

    def test_import_listens(self):
        count = self._create_test_data(self.testuser_name)
        sleep(1)
        temp_dir = tempfile.mkdtemp()
        dump_location = self.logstore.dump_listens(
            location=temp_dir,
            dump_id=1,
            end_time=datetime.now(),
        )
        sleep(1)
        self.assertTrue(os.path.isfile(dump_location))
        self.reset_timescale_db()
        sleep(1)
        self.logstore.import_listens_dump(dump_location)
        sleep(1)
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
        count = self._create_test_data(user['musicbrainz_id'])
        sleep(1)

        count = self._create_test_data(self.testuser_name)
        sleep(1)

        temp_dir = tempfile.mkdtemp()
        dump_location = self.logstore.dump_listens(
            location=temp_dir,
            dump_id=1,
            end_time=datetime.now(),
        )
        sleep(1)
        self.assertTrue(os.path.isfile(dump_location))
        self.reset_timescale_db()

        self.logstore.import_listens_dump(dump_location)
        sleep(1)

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

    def test_import_dump_many_users(self):
        for i in range(2, 52):
            db_user.create(i, 'user%d' % i)

        temp_dir = tempfile.mkdtemp()
        dump_location = self.logstore.dump_listens(
            location=temp_dir,
            dump_id=1,
            end_time=datetime.now(),
        )
        sleep(1)
        self.assertTrue(os.path.isfile(dump_location))
        self.reset_timescale_db()

        done = self.logstore.import_listens_dump(dump_location)
        sleep(1)
        self.assertEqual(done, len(db_user.get_all_users()))
        shutil.rmtree(temp_dir)


    def create_test_dump(self, archive_name, archive_path, schema_version=None, index=None):
        """ Creates a test dump to test the import listens functionality.

        Args:
            archive_name (str): the name of the archive
            archive_path (str): the full path to the archive
            schema_version (int): the version of the schema to be written into SCHEMA_SEQUENCE
                                  if not provided, the SCHEMA_SEQUENCE file is not added to the archive
            index (dict): the index dict to be written into index.json
                          if not provided, index.json is not added to the archive

        Returns:
            the full path to the archive created
        """

        temp_dir = tempfile.mkdtemp()
        with open(archive_path, 'w') as archive:
            pxz_command = ['pxz', '--compress']
            pxz = subprocess.Popen(pxz_command, stdin=subprocess.PIPE, stdout=archive)

            with tarfile.open(fileobj=pxz.stdin, mode='w|') as tar:
                if schema_version is not None:
                    schema_version_path = os.path.join(temp_dir, 'SCHEMA_SEQUENCE')
                    with open(schema_version_path, 'w') as f:
                        f.write(str(schema_version))
                    tar.add(schema_version_path,
                            arcname=os.path.join(archive_name, 'SCHEMA_SEQUENCE'))

                if index is not None:
                    index_json_path = os.path.join(temp_dir, 'index.json')
                    with open(index_json_path, 'w') as f:
                        f.write(ujson.dumps({}))
                    tar.add(index_json_path,
                            arcname=os.path.join(archive_name, 'index.json'))

            pxz.stdin.close()

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
            schema_version=LISTENS_DUMP_SCHEMA_VERSION - 1,
            index={},
        )
        sleep(1)
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
            schema_version=None,
            index={},
        )

        sleep(1)
        with self.assertRaises(SchemaMismatchException):
            self.logstore.import_listens_dump(archive_path)


    def test_schema_mismatch_exception_for_dump_no_index(self):
        """ Tests that SchemaMismatchException is raised when there is no index.json in the archive """

        temp_dir = tempfile.mkdtemp()
        archive_name = 'temp_dump'
        archive_path = os.path.join(temp_dir, archive_name + '.tar.xz')

        archive_path = self.create_test_dump(
            archive_name=archive_name,
            archive_path=archive_path,
            schema_version=LISTENS_DUMP_SCHEMA_VERSION,
            index=None,
        )

        sleep(1)
        with self.assertRaises(SchemaMismatchException):
            self.logstore.import_listens_dump(archive_path)


    def test_delete_listens(self):
        count = self._create_test_data(self.testuser_name)
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
        count = self._create_test_data(user['musicbrainz_id'])
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
