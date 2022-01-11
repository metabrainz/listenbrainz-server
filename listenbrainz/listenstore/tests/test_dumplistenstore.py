import logging
import os
import shutil
import tarfile
import tempfile
from datetime import datetime

from psycopg2.extras import execute_values

import listenbrainz.db.user as db_user
from listenbrainz.db import timescale
from listenbrainz.db.dump import SchemaMismatchException
from listenbrainz.db.testing import TimescaleTestCase, DatabaseTestCase
from listenbrainz.listenstore import TimescaleListenStore, LISTENS_DUMP_SCHEMA_VERSION
from listenbrainz.listenstore.dump_listenstore import DumpListenStore
from listenbrainz.listenstore.tests.util import create_test_data_for_timescalelistenstore, generate_data


class TestDumpListenStore(DatabaseTestCase, TimescaleTestCase):

    def setUp(self):
        DatabaseTestCase.setUp(self)
        TimescaleTestCase.setUp(self)
        self.log = logging.getLogger(__name__)
        self.logstore = TimescaleListenStore(self.log)
        self.dumpstore = DumpListenStore(self.log)
        self.testuser_name = db_user.get_or_create(1, "test")["musicbrainz_id"]

    def tearDown(self):
        self.logstore = None
        self.dumpstore = None
        DatabaseTestCase.tearDown(self)
        TimescaleTestCase.tearDown(self)

    def _create_test_data(self, user_name, test_data_file_name=None):
        test_data = create_test_data_for_timescalelistenstore(user_name, test_data_file_name)
        self.logstore.insert(test_data)
        return len(test_data)

    def _insert_with_created(self, listens):
        """ Insert a batch of listens with 'created' field.
        """
        submit = []
        for listen in listens:
            submit.append((*listen.to_timescale(), listen.inserted_timestamp))

        query = """INSERT INTO listen (listened_at, track_name, user_name, data, created)
                        VALUES %s
                   ON CONFLICT (listened_at, track_name, user_name)
                    DO NOTHING
                """

        conn = timescale.engine.raw_connection()
        with conn.cursor() as curs:
            execute_values(curs, query, submit, template=None)

        conn.commit()

    def test_dump_listens(self):
        self._create_test_data(self.testuser_name)
        temp_dir = tempfile.mkdtemp()
        dump = self.dumpstore.dump_listens(
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
        dump_location = self.dumpstore.dump_listens(
            location=temp_dir,
            dump_id=1,
            start_time=datetime.utcfromtimestamp(base + 6),
            end_time=datetime.utcfromtimestamp(base + 10)
        )
        self.assertTrue(os.path.isfile(dump_location))
        self.reset_timescale_db()
        self.logstore.import_listens_dump(dump_location)
        listens, min_ts, max_ts = self.logstore.fetch_listens(user_name=self.testuser_name, to_ts=base + 11)
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
        dump_location = self.dumpstore.dump_listens(
            location=temp_dir,
            dump_id=1,
            end_time=datetime.utcfromtimestamp(base + 5)
        )
        self.assertTrue(os.path.isfile(dump_location))
        self.reset_timescale_db()
        self.logstore.import_listens_dump(dump_location)
        listens, min_ts, max_ts = self.logstore.fetch_listens(user_name=self.testuser_name, to_ts=base + 11)
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
        dump_location = self.dumpstore.dump_listens(
            location=temp_dir,
            dump_id=1,
            end_time=datetime.now(),
        )
        self.assertTrue(os.path.isfile(dump_location))
        self.reset_timescale_db()
        self.logstore.import_listens_dump(dump_location)
        listens, min_ts, max_ts = self.logstore.fetch_listens(user_name=self.testuser_name, to_ts=1400000300)
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

        listens, min_ts, max_ts = self.logstore.fetch_listens(user_name=user['musicbrainz_id'], to_ts=1400000300)
        self.assertEqual(len(listens), 5)
        self.assertEqual(listens[0].ts_since_epoch, 1400000200)
        self.assertEqual(listens[1].ts_since_epoch, 1400000150)
        self.assertEqual(listens[2].ts_since_epoch, 1400000100)
        self.assertEqual(listens[3].ts_since_epoch, 1400000050)
        self.assertEqual(listens[4].ts_since_epoch, 1400000000)

        listens, min_ts, max_ts = self.logstore.fetch_listens(user_name=self.testuser_name, to_ts=1400000300)
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
            archive_path=archive_path
        )

        with self.assertRaises(SchemaMismatchException):
            self.logstore.import_listens_dump(archive_path)
