import os
import shutil
import subprocess
import tarfile
import tempfile
from datetime import datetime, timezone, timedelta
from tempfile import TemporaryDirectory
from unittest.mock import patch

import pyarrow.parquet as pq
from psycopg2.extras import execute_values
from sqlalchemy import text

import listenbrainz.db.user as db_user
from listenbrainz.db import timescale, listens as listens_db
from listenbrainz.dumps.exceptions import SchemaMismatchException
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

    @patch("listenbrainz.listenstore.dump_listenstore.SPARK_DUMP_MAPPING_BATCH_SIZE", 2)
    def test_spark_dump_with_mapping(self):
        """ Test that the spark dump uses the mapping from the listens db, preferring the user's manual mapping """
        base = 1500000000
        listens = generate_data(self.testuser_id, self.testuser_name, base, 3, base)
        self._insert_with_created(listens)

        mapped_mbid = "2f3d422f-8890-41a1-9762-fbe16f107c31"
        manual_mbid = "2cfad207-3f55-4aec-8120-86cf66e34d59"
        with listens_db.engine.begin() as connection:
            for recording_id, (mbid, name) in enumerate([(mapped_mbid, "Strangers"), (manual_mbid, "Immigrant Song")]):
                connection.execute(text("""
                    INSERT INTO mapping.mb_metadata_cache
                               (recording_mbid, recording_id, artist_mbids, artist_ids, release_mbid, release_id,
                                recording_data, artist_data, tag_data, release_data, dirty)
                        VALUES (:mbid, :id, '{8f6bd1e4-fbe1-4f50-aa9b-94c450ec0f11}'::UUID[], '{1}'::INTEGER[],
                                '76df3287-6cda-33eb-8e9a-044b5e15ffdd', 1, :recording_data,
                                '{"name": "Portishead", "artist_credit_id": 204, "artists": []}',
                                '{"artist": [], "recording": [], "release_group": []}',
                                '{"mbid": "76df3287-6cda-33eb-8e9a-044b5e15ffdd", "name": "Dummy"}', 'f')
                """), {"mbid": mbid, "id": recording_id, "recording_data": f'{{"name": "{name}"}}'})
            connection.execute(text("""
                INSERT INTO mapping.mbid_mapping (recording_msid, recording_mbid, match_type)
                     VALUES (:msid_0, :mapped_mbid, 'exact_match'), (:msid_1, :mapped_mbid, 'exact_match')
            """), {"msid_0": listens[0].recording_msid, "msid_1": listens[1].recording_msid, "mapped_mbid": mapped_mbid})
            connection.execute(text("""
                INSERT INTO mapping.mbid_manual_mapping (recording_msid, recording_mbid, user_id)
                     VALUES (:msid, :mbid, :user_id)
            """), {"msid": listens[1].recording_msid, "mbid": manual_mbid, "user_id": self.testuser_id})

        with TemporaryDirectory() as temp_dir:
            archive_path = self.dumpstore.dump_listens_for_spark(
                location=temp_dir,
                dump_id=1,
                dump_type="full",
                start_time=datetime.fromtimestamp(base - 1, timezone.utc),
                end_time=datetime.fromtimestamp(base + 10, timezone.utc),
            )
            with tarfile.open(archive_path) as tar:
                tar.extractall(temp_dir, filter="data")
            parquet_files = [
                os.path.join(root, name)
                for root, _, names in os.walk(temp_dir)
                for name in names if name.endswith(".parquet")
            ]
            rows = [row for file in sorted(parquet_files) for row in pq.read_table(file).to_pylist()]

        rows = {row["recording_msid"]: row for row in rows}
        self.assertEqual(len(rows), 3)

        mapped = rows[listens[0].recording_msid]
        self.assertEqual(mapped["recording_mbid"], mapped_mbid)
        self.assertEqual(mapped["recording_name"], "Strangers")
        self.assertEqual(mapped["artist_name"], "Portishead")
        self.assertEqual(mapped["artist_credit_id"], 204)
        self.assertEqual(mapped["release_name"], "Dummy")
        self.assertEqual(mapped["artist_credit_mbids"], ["8f6bd1e4-fbe1-4f50-aa9b-94c450ec0f11"])

        manual = rows[listens[1].recording_msid]
        self.assertEqual(manual["recording_mbid"], manual_mbid)
        self.assertEqual(manual["recording_name"], "Immigrant Song")

        unmapped = rows[listens[2].recording_msid]
        self.assertIsNone(unmapped["recording_mbid"])
        self.assertIsNone(unmapped["artist_credit_id"])
        self.assertEqual(unmapped["recording_name"], "Crack Rock")
        self.assertEqual(unmapped["artist_name"], "Frank Ocean")

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
        listens = self.ls.fetch_listens(user=self.testuser, to_ts=to_ts)
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

        listens = self.ls.fetch_listens(user=self.testuser, to_ts=datetime.fromtimestamp(base + 11, timezone.utc))
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
        listens = self.ls.fetch_listens(user=self.testuser, to_ts=to_ts)
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

        listens = self.ls.fetch_listens(user=user, to_ts=datetime.fromtimestamp(1400000300, timezone.utc))
        self.assertEqual(len(listens), 5)
        self.assertEqual(listens[0].ts_since_epoch, 1400000200)
        self.assertEqual(listens[1].ts_since_epoch, 1400000150)
        self.assertEqual(listens[2].ts_since_epoch, 1400000100)
        self.assertEqual(listens[3].ts_since_epoch, 1400000050)
        self.assertEqual(listens[4].ts_since_epoch, 1400000000)

        listens = self.ls.fetch_listens(user=self.testuser, to_ts=datetime.fromtimestamp(1400000300, timezone.utc))
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
