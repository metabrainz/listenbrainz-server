# coding=utf-8

import listenbrainz.db.user as db_user
import logging
import os
import shutil
import subprocess
import tarfile
import tempfile
import time
import ujson

from brainzutils import cache
from datetime import datetime
from collections import OrderedDict
from influxdb import InfluxDBClient
from listenbrainz.db.dump import SchemaMismatchException
from listenbrainz.db.testing import DatabaseTestCase
from listenbrainz.listen import Listen
from listenbrainz.listenstore import InfluxListenStore, LISTENS_DUMP_SCHEMA_VERSION
from listenbrainz.listenstore.influx_listenstore import REDIS_INFLUX_USER_LISTEN_COUNT
from listenbrainz.listenstore.tests.util import create_test_data_for_influxlistenstore, generate_data
from listenbrainz.webserver.influx_connection import init_influx_connection
from sqlalchemy import text
from time import sleep

from listenbrainz import config

class TestInfluxListenStore(DatabaseTestCase):


    def reset_influx_db(self):
        """ Resets the entire influx db """
        influx = InfluxDBClient(
            host=config.INFLUX_HOST,
            port=config.INFLUX_PORT,
            database=config.INFLUX_DB_NAME
        )
        influx.query('DROP DATABASE %s' % config.INFLUX_DB_NAME)
        influx.query('CREATE DATABASE %s' % config.INFLUX_DB_NAME)


    def setUp(self):
        super(TestInfluxListenStore, self).setUp()
        self.log = logging.getLogger(__name__)

        # In order to do counting correctly, we need a clean DB to start with
        self.reset_influx_db()

        self.logstore = init_influx_connection(self.log, {
            'REDIS_HOST': config.REDIS_HOST,
            'REDIS_PORT': config.REDIS_PORT,
            'REDIS_NAMESPACE': config.REDIS_NAMESPACE,
            'INFLUX_HOST': config.INFLUX_HOST,
            'INFLUX_PORT': config.INFLUX_PORT,
            'INFLUX_DB_NAME': config.INFLUX_DB_NAME,
        })
        self.testuser_id = db_user.create(1, "test")
        self.testuser_name = db_user.get(self.testuser_id)['musicbrainz_id']

    def tearDown(self):
        self.logstore = None
        super(TestInfluxListenStore, self).tearDown()

    def _create_test_data(self, user_name):
        test_data = create_test_data_for_influxlistenstore(user_name)
        self.logstore.insert(test_data)
        return len(test_data)

    # this test should be done first, because the other tests keep inserting more rows
    def test_aaa_get_total_listen_count(self):
        listen_count = self.logstore.get_total_listen_count(False)
        self.assertEqual(0, listen_count)

        count = self._create_test_data(self.testuser_name)
        sleep(1)
        listen_count = self.logstore.get_total_listen_count(False)
        self.assertEqual(count, listen_count)

        self.logstore.update_listen_counts()
        listen_count = self.logstore.get_total_listen_count(False)
        self.assertEqual(count, listen_count)

        count = self._create_test_data(self.testuser_name)
        sleep(1)
        listen_count = self.logstore.get_total_listen_count(False)
        self.assertEqual(count * 2, listen_count)

        self.logstore.update_listen_counts()
        listen_count = self.logstore.get_total_listen_count(False)
        self.assertEqual(count * 2, listen_count)

    def test_insert_influx(self):
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

    def test_get_listen_count_for_user(self):
        count = self._create_test_data(self.testuser_name)
        self.logstore.update_listen_counts()
        listen_count = self.logstore.get_listen_count_for_user(user_name=self.testuser_name)
        self.assertEqual(count, listen_count)

    def test_fetch_listens_escaped(self):
        user = db_user.get_or_create(2, 'i have a\\weird\\user, name"\n')
        user_name = user['musicbrainz_id']
        self._create_test_data(user_name)
        listens = self.logstore.fetch_listens(user_name=user_name, from_ts=1400000100)
        self.assertEqual(len(listens), 2)
        self.assertEqual(listens[0].ts_since_epoch, 1400000200)
        self.assertEqual(listens[1].ts_since_epoch, 1400000150)

    def test_fetch_recent_listens(self):
        user = db_user.get_or_create(2, 'someuser')
        user_name = user['musicbrainz_id']
        self._create_test_data(user_name)

        user2 = db_user.get_or_create(3, 'otheruser')
        user_name2 = user['musicbrainz_id']
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
        )
        self.assertTrue(os.path.isfile(dump))
        shutil.rmtree(temp_dir)

    def test_dump_listens_spark_format(self):
        self._create_test_data(self.testuser_name)
        temp_dir = tempfile.mkdtemp()
        dump = self.logstore.dump_listens(
            location=temp_dir,
            dump_id=1,
            spark_format=True
        )
        self.assertTrue(os.path.isfile(dump))
        shutil.rmtree(temp_dir)


    def test_incremental_dump(self):
        """ Dump and import listens
        """
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
        sleep(1)
        self.assertTrue(os.path.isfile(dump_location))
        self.reset_influx_db()
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
        shutil.rmtree(temp_dir)


    def test_import_listens(self):
        count = self._create_test_data(self.testuser_name)
        sleep(1)
        temp_dir = tempfile.mkdtemp()
        dump_location = self.logstore.dump_listens(
            location=temp_dir,
            dump_id=1,
        )
        sleep(1)
        self.assertTrue(os.path.isfile(dump_location))
        self.reset_influx_db()
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
        )
        sleep(1)
        self.assertTrue(os.path.isfile(dump_location))
        self.reset_influx_db()

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
        )
        sleep(1)
        self.assertTrue(os.path.isfile(dump_location))
        self.reset_influx_db()

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


    def test_listen_counts_in_cache(self):
        count = self._create_test_data(self.testuser_name)
        self.assertEqual(count, self.logstore.get_listen_count_for_user(self.testuser_name, need_exact=True))
        user_key = '{}{}'.format(REDIS_INFLUX_USER_LISTEN_COUNT, self.testuser_name)
        self.assertEqual(count, int(cache.get(user_key, decode=False)))

        batch = generate_data(self.testuser_id, self.testuser_name, int(time.time()), 1)
        self.logstore.insert(batch)
        self.assertEqual(count + 1, int(cache.get(user_key, decode=False)))


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

    def test_delete_listens_no_measurement(self):
        user = db_user.get_or_create(12, 'user_with_no_measurement')
        self.logstore.delete(user['musicbrainz_id'])
        listens = self.logstore.fetch_listens(user_name=user['musicbrainz_id'], to_ts=1400000300)
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
