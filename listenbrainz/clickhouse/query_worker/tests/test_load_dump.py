import shutil
from datetime import datetime, timedelta
from pathlib import Path
from tempfile import TemporaryDirectory
from uuid import uuid4

import pandas as pd
import pyarrow as pa
import pyarrow.compute as pc
import pyarrow.parquet as pq

from listenbrainz.clickhouse.query_worker.listens.ftp import DumpType
from listenbrainz.clickhouse.query_worker.listens.load_dump import (
    create_staging_table,
    merge_staged_listens,
)
from listenbrainz.clickhouse.query_worker.tests import (
    ClickHouseTestCase, TEST_DATA_PATH, _normalized, archive_parquet_files, fixture_listens,
)
from listenbrainz.listenstore.dump_listenstore import SPARK_LISTENS_SCHEMA

ALL_FIXTURES = ("full-dump-1", "incremental-dump-2", "incremental-dump-3")


class DumpDataTestCase(ClickHouseTestCase):

    def test_fixture_import_and_replay_are_idempotent(self):
        self.load_spark_listens()
        rows = self.listens()
        # every column of every listen, each listen once
        self.assertEqual(set(rows), fixture_listens(*ALL_FIXTURES))
        self.assertEqual(len(rows), len(fixture_listens(*ALL_FIXTURES)))
        # replaying incremental dumps adds nothing
        self.load_fixture("incremental-dump-2")
        self.load_fixture("incremental-dump-3")
        self.assertEqual(self.listens(), rows)
        # a full dump followed by its incrementals gives the same listens again
        self.load_spark_listens()
        self.assertEqual(self.listens(), rows)
        self.assertEqual(self.staging_tables(), [])

    def test_dump_columns_are_loaded_as_written(self):
        # written as the dump writer does, with nulls in every nullable column and a
        # user_id beyond Int32, which ClickHouse converts on insert
        listens = pd.DataFrame({
            "listened_at": [datetime(2024, 1, 1, 0, 0, 0, 123000), datetime(2024, 1, 2)],
            "created": [datetime(2024, 1, 3), datetime(2024, 1, 4, 0, 0, 0, 456000)],
            "user_id": [1, 4_000_000_000],
            "recording_msid": [str(uuid4()), str(uuid4())],
            "artist_name": ["artist", ""],
            "artist_credit_id": [5, None],
            "release_name": ["release", None],
            "release_mbid": [str(uuid4()), None],
            "recording_name": ["recording", "other recording"],
            "recording_mbid": [None, str(uuid4())],
            "artist_credit_mbids": [[str(uuid4()), str(uuid4())], None],
        })
        table = pa.Table.from_pandas(listens, schema=SPARK_LISTENS_SCHEMA, preserve_index=False)
        expected = {_normalized(row) for row in table.to_pylist()}
        with TemporaryDirectory() as tmp:
            pq.write_table(table, Path(tmp) / "0.parquet", flavor="spark", compression="zstd")
            archive = archive_parquet_files(Path(tmp), Path(tmp) / "dump.tar")
            # an incremental load is merged into listens, a full one swapped in
            for dump_type in (DumpType.INCREMENTAL, DumpType.FULL):
                with self.subTest(dump_type=dump_type):
                    self.client.command("TRUNCATE TABLE listens")
                    result = self.load_archive(archive, dump_type)
                    self.assertEqual((result["errors"], result["added"]), ([], 2))
                    self.assertEqual(set(self.listens()), expected)

    def test_resubmitted_listen_is_not_duplicated(self):
        # a listen deleted and submitted again comes back with a new `created`
        self.load_fixture("full-dump-1")
        before = self.listens()
        listens = pq.read_table(TEST_DATA_PATH / "full-dump-1" / "0.parquet")
        created = listens.schema.get_field_index("created")
        resubmitted = listens.set_column(created, "created", pc.add(listens["created"], pa.scalar(timedelta(days=30))))
        with TemporaryDirectory() as tmp:
            pq.write_table(resubmitted, Path(tmp) / "0.parquet")
            archive = archive_parquet_files(Path(tmp), Path(tmp) / "dump.tar")
            result = self.load_archive(archive, DumpType.INCREMENTAL)
        self.assertEqual((result["errors"], result["added"]), ([], 0))
        self.assertEqual(self.listens(), before)

    def test_merge_skips_loaded_listens_and_isolates_loads(self):
        source = pq.read_table(TEST_DATA_PATH / "incremental-dump-2" / "0.parquet")
        one = create_staging_table(self.client)
        self.client.insert_arrow(one, source)
        other = source.slice(0, 1).set_column(source.schema.get_field_index("user_id"), "user_id", pa.array([999], type=pa.int64()))
        two = create_staging_table(self.client)
        self.client.insert_arrow(two, other)
        # the same listen twice in one load
        self.client.insert_arrow(one, source.slice(0, 1))
        merge_staged_listens(self.client, one)
        self.assertEqual(len(self.listens()), source.num_rows)
        self.assertNotIn(999, {row[2] for row in self.listens()})
        # merging the same load again adds nothing
        merge_staged_listens(self.client, one)
        self.assertEqual(len(self.listens()), source.num_rows)
        merge_staged_listens(self.client, two)
        self.assertIn(999, {row[2] for row in self.listens()})

    def test_failed_replace_keeps_existing_listens(self):
        self.load_spark_listens()
        before = self.listens()
        with TemporaryDirectory() as tmp:
            shutil.copy(TEST_DATA_PATH / "incremental-dump-2" / "0.parquet", Path(tmp) / "good.parquet")
            (Path(tmp) / "bad.parquet").write_bytes(b"not parquet")
            archive = archive_parquet_files(Path(tmp), Path(tmp) / "dump.tar")
            failed = self.load_archive(archive, DumpType.FULL)
        self.assertEqual(len(failed["errors"]), 1)
        self.assertEqual(self.listens(), before)
        self.assertEqual(self.staging_tables(), [])

    def test_failed_incremental_keeps_existing_listens(self):
        self.load_fixture("full-dump-1")
        before = self.listens()
        with TemporaryDirectory() as tmp:
            (Path(tmp) / "broken.parquet").write_bytes(b"broken")
            archive = archive_parquet_files(Path(tmp), Path(tmp) / "dump.tar")
            failed = self.load_archive(archive, DumpType.INCREMENTAL)
        self.assertEqual(len(failed["errors"]), 1)
        self.assertEqual(self.listens(), before)
        self.assertEqual(self.staging_tables(), [])

    def test_import_drops_the_leftovers_of_killed_imports(self):
        # an import killed mid-load leaves its staging table behind
        killed = create_staging_table(self.client)
        self.client.insert_arrow(killed, pq.read_table(TEST_DATA_PATH / "incremental-dump-2" / "0.parquet"))
        self.load_fixture("full-dump-1")
        self.assertEqual(self.staging_tables(), [])
        self.assertEqual(set(self.listens()), fixture_listens("full-dump-1"))

    def test_full_dump_swaps_in_only_the_dump(self):
        self.load_spark_listens()
        result = self.load_fixture("full-dump-1")
        self.assertEqual(set(self.listens()), fixture_listens("full-dump-1"))
        self.assertEqual(result["added"], len(fixture_listens("full-dump-1")))
        self.assertEqual(self.staging_tables(), [])

    def test_full_dump_replaces_a_listens_table_with_an_older_schema(self):
        self.client.command("DROP TABLE listens SYNC")
        self.client.command(
            "CREATE TABLE listens (listened_at DateTime64(3), created DateTime64(3), user_id UInt32,"
            " recording_msid String) ENGINE = MergeTree ORDER BY (user_id, listened_at, recording_msid)"
        )
        self.load_fixture("full-dump-1")
        self.assertEqual(set(self.listens()), fixture_listens("full-dump-1"))

