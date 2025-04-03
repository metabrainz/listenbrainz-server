import os
import shutil
import subprocess
import tarfile
import tempfile
from datetime import datetime, timezone, timedelta
from tempfile import TemporaryDirectory

from psycopg2.extras import execute_values

import listenbrainz.db.user as db_user
from listenbrainz.db import timescale
from listenbrainz.db.dump import SchemaMismatchException
from listenbrainz.listenstore import LISTENS_DUMP_SCHEMA_VERSION, LISTEN_MINIMUM_DATE
from listenbrainz.listenstore.dump_listenstore import DumpListenStore
from listenbrainz.listenstore.tests.util import create_test_data_for_timescalelistenstore, generate_data
from listenbrainz.listenstore.timescale_utils import recalculate_all_user_data
from listenbrainz.tests.integration import NonAPIIntegrationTestCase
from listenbrainz.webserver import timescale_connection, redis_connection


class TestDumpListenStore(NonAPIIntegrationTestCase):

    def setUp(self):
        super(TestDumpListenStore, self).setUp()
        self.ls = timescale_connection._ts
        self.rs = redis_connection._redis
        self.dumpstore = DumpListenStore(self.app)
        self.testuser = db_user.get_or_create(self.db_conn, 1, "test")
        self.testuser_name = self.testuser["musicbrainz_id"]
        self.testuser_id = self.testuser["id"]

    def _create_test_data(self, user_name, user_id, test_data_file_name=None):
        test_data = create_test_data_for_timescalelistenstore(user_name, user_id, test_data_file_name)
        self.ls.insert(test_data)
        return len(test_data)

    def _insert_with_created(self, listens):
        """ Insert a batch of listens with 'created' field.
        """
        submit = []
        for listen in listens:
            submit.append((*listen.to_timescale(), listen.inserted_timestamp))

        query = """INSERT INTO listen (listened_at, user_id, recording_msid, data, created)
                        VALUES %s
                   ON CONFLICT (listened_at, user_id, recording_msid)
                    DO NOTHING
                """

        conn = timescale.engine.raw_connection()
        with conn.cursor() as curs:
            execute_values(curs, query, submit, template=None)

        conn.commit()

    def test_dump_listens(self):
        self._create_test_data(self.testuser_name, self.testuser_id)
        temp_dir = tempfile.mkdtemp()
        dump = self.dumpstore.dump_listens(
            location=temp_dir,
            dump_id=1,
            start_time=LISTEN_MINIMUM_DATE,
            end_time=datetime.now(timezone.utc),
            dump_type="full"
        )
        self.assertTrue(os.path.isfile(dump))
        shutil.rmtree(temp_dir)

    def test_incremental_dump(self):
        base = 1500000000
        # generate 5 listens with inserted_ts 1-5
        listens = generate_data(self.testuser_id, self.testuser_name, base-4, 5, base+1)
        self._insert_with_created(listens)
        # generate 5 listens with inserted_ts 6-10
        listens = generate_data(self.testuser_id, self.testuser_name, base+1, 5, base+6)
        self._insert_with_created(listens)
        temp_dir = tempfile.mkdtemp()
        dump_location = self.dumpstore.dump_listens(
            location=temp_dir,
            dump_id=1,
            start_time=datetime.fromtimestamp(base + 6, timezone.utc),
            end_time=datetime.fromtimestamp(base + 10, timezone.utc),
            dump_type="incremental"
        )
        self.assertTrue(os.path.isfile(dump_location))

        self.reset_timescale_db()
        self.ls.import_listens_dump(dump_location)
        recalculate_all_user_data()

        to_ts = datetime.fromtimestamp(base + 11, timezone.utc)
        listens, min_ts, max_ts = self.ls.fetch_listens(user=self.testuser, to_ts=to_ts)
        self.assertEqual(len(listens), 4)
        self.assertEqual(listens[0].ts_since_epoch, base + 5)
        self.assertEqual(listens[1].ts_since_epoch, base + 4)
        self.assertEqual(listens[2].ts_since_epoch, base + 3)
        self.assertEqual(listens[3].ts_since_epoch, base + 2)

        shutil.rmtree(temp_dir)

    def test_time_range_full_dumps(self):
        base = 1500000000
        listens = generate_data(self.testuser_id, self.testuser_name, base + 1, 5, base + 1)  # generate 5 listens with ts 1-5
        self._insert_with_created(listens)
        listens = generate_data(self.testuser_id, self.testuser_name, base + 6, 5, base + 6)  # generate 5 listens with ts 6-10
        self._insert_with_created(listens)
        temp_dir = tempfile.mkdtemp()
        dump_location = self.dumpstore.dump_listens(
            location=temp_dir,
            dump_id=1,
            start_time=LISTEN_MINIMUM_DATE,
            end_time=datetime.fromtimestamp(base + 5, timezone.utc),
            dump_type="full"
        )
        self.assertTrue(os.path.isfile(dump_location))

        self.reset_timescale_db()
        self.ls.import_listens_dump(dump_location)
        recalculate_all_user_data()

        listens, min_ts, max_ts = self.ls.fetch_listens(user=self.testuser, to_ts=datetime.fromtimestamp(base + 11, timezone.utc))
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
        dump_location = self.dumpstore.dump_listens(
            location=temp_dir,
            dump_id=1,
            start_time=LISTEN_MINIMUM_DATE,
            end_time=datetime.now(timezone.utc) + timedelta(seconds=60),
            dump_type="full"
        )
        self.assertTrue(os.path.isfile(dump_location))

        self.reset_timescale_db()
        self.ls.import_listens_dump(dump_location)
        recalculate_all_user_data()

        to_ts = datetime.fromtimestamp(1400000300, timezone.utc)
        listens, min_ts, max_ts = self.ls.fetch_listens(user=self.testuser, to_ts=to_ts)
        self.assertEqual(len(listens), 5)
        self.assertEqual(listens[0].ts_since_epoch, 1400000200)
        self.assertEqual(listens[1].ts_since_epoch, 1400000150)
        self.assertEqual(listens[2].ts_since_epoch, 1400000100)
        self.assertEqual(listens[3].ts_since_epoch, 1400000050)
        self.assertEqual(listens[4].ts_since_epoch, 1400000000)
        shutil.rmtree(temp_dir)

    def test_dump_and_import_listens_escaped(self):
        user = db_user.get_or_create(self.db_conn, 3, 'i have a\\weird\\user, na/me"\n')
        self._create_test_data(user['musicbrainz_id'], user['id'])

        self._create_test_data(self.testuser_name, self.testuser_id)

        temp_dir = tempfile.mkdtemp()
        dump_location = self.dumpstore.dump_listens(
            location=temp_dir,
            dump_id=1,
            start_time=LISTEN_MINIMUM_DATE,
            end_time=datetime.now(tz=timezone.utc) + timedelta(seconds=60),
            dump_type="full"
        )
        self.assertTrue(os.path.isfile(dump_location))

        self.reset_timescale_db()
        self.ls.import_listens_dump(dump_location)
        recalculate_all_user_data()

        listens, min_ts, max_ts = self.ls.fetch_listens(user=user, to_ts=datetime.fromtimestamp(1400000300, timezone.utc))
        self.assertEqual(len(listens), 5)
        self.assertEqual(listens[0].ts_since_epoch, 1400000200)
        self.assertEqual(listens[1].ts_since_epoch, 1400000150)
        self.assertEqual(listens[2].ts_since_epoch, 1400000100)
        self.assertEqual(listens[3].ts_since_epoch, 1400000050)
        self.assertEqual(listens[4].ts_since_epoch, 1400000000)

        listens, min_ts, max_ts = self.ls.fetch_listens(user=self.testuser, to_ts=datetime.fromtimestamp(1400000300, timezone.utc))
        self.assertEqual(len(listens), 5)
        self.assertEqual(listens[0].ts_since_epoch, 1400000200)
        self.assertEqual(listens[1].ts_since_epoch, 1400000150)
        self.assertEqual(listens[2].ts_since_epoch, 1400000100)
        self.assertEqual(listens[3].ts_since_epoch, 1400000050)
        self.assertEqual(listens[4].ts_since_epoch, 1400000000)
        shutil.rmtree(temp_dir)

    # test test_import_dump_many_users is gone -- why are we testing user dump/restore here??

    def create_test_dump(self, temp_dir, archive_name, archive_path, schema_version=None):
        """ Creates a test dump to test the import listens functionality.
        Args:
            archive_name (str): the name of the archive
            archive_path (str): the full path to the archive
            schema_version (int): the version of the schema to be written into SCHEMA_SEQUENCE
                                  if not provided, the SCHEMA_SEQUENCE file is not added to the archive
        Returns:
            the full path to the archive created
        """
        with open(archive_path, 'w') as archive:
            zstd_command = ['zstd', '--compress', '-T4']
            zstd = subprocess.Popen(zstd_command, stdin=subprocess.PIPE, stdout=archive)
            with tarfile.open(fileobj=zstd.stdin, mode='w|') as tar:
                schema_version_path = os.path.join(temp_dir, 'SCHEMA_SEQUENCE')
                with open(schema_version_path, 'w') as f:
                    f.write(str(schema_version or ' '))
                tar.add(schema_version_path,
                        arcname=os.path.join(archive_name, 'SCHEMA_SEQUENCE'))
            zstd.stdin.close()
            zstd.wait()
        return archive_path

    def test_schema_mismatch_exception_for_dump_incorrect_schema(self):
        """ Tests that SchemaMismatchException is raised when the schema of the dump is old """
        with TemporaryDirectory() as temp_dir:
            # create a temp archive with incorrect SCHEMA_VERSION_CORE
            archive_name = 'temp_dump'
            archive_path = os.path.join(temp_dir, archive_name + '.tar.zst')
            archive_path = self.create_test_dump(
                temp_dir=temp_dir,
                archive_name=archive_name,
                archive_path=archive_path,
                schema_version=LISTENS_DUMP_SCHEMA_VERSION - 1
            )
            with self.assertRaises(SchemaMismatchException):
                self.ls.import_listens_dump(archive_path)

    def test_schema_mismatch_exception_for_dump_no_schema(self):
        """ Tests that SchemaMismatchException is raised when there is no schema version in the archive """
        with TemporaryDirectory() as temp_dir:
            archive_name = 'temp_dump'
            archive_path = os.path.join(temp_dir, archive_name + '.tar.zst')
            archive_path = self.create_test_dump(
                temp_dir=temp_dir,
                archive_name=archive_name,
                archive_path=archive_path
            )
            with self.assertRaises(SchemaMismatchException):
                self.ls.import_listens_dump(archive_path)
