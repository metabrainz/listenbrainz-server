import unittest
from datetime import datetime, timezone
from unittest import mock

import pyarrow as pa

from clickhouse.stats.load_dump import (
    PROCESS_RAW_LISTENS,
    PROCESS_RAW_LISTENS_CHUNKS,
    PROCESS_RAW_LISTENS_SETTINGS,
    REPLACE_TRUNCATE_TABLES,
    build_process_raw_listens_query,
    build_raw_listens_arrow_table,
    create_client,
    drop_raw_listens_partition,
    process_raw_listens,
    truncate_derived_tables,
)


class LoadDumpClientTestCase(unittest.TestCase):

    @mock.patch("clickhouse.stats.load_dump.clickhouse_connect.get_client")
    def test_create_client_waits_for_async_insert(self, mock_get_client):
        create_client("localhost", 8123, "default", "", "default")

        mock_get_client.assert_called_once()
        kwargs = mock_get_client.call_args.kwargs
        self.assertIs(kwargs["form_encode_query_params"], True)
        self.assertTrue(kwargs["session_id"].startswith("listenbrainz_load_dump_"))
        self.assertEqual(kwargs["settings"], {"async_insert": 1, "wait_for_async_insert": 1})


class RawListenArrowTestCase(unittest.TestCase):

    def test_build_raw_listens_arrow_table_normalizes_dump_rows(self):
        listened_at = datetime(2026, 5, 24, 10, 0, tzinfo=timezone.utc)
        created = datetime(2026, 5, 24, 10, 1, tzinfo=timezone.utc)
        table = pa.table({
            "listened_at": [listened_at],
            "created": [created],
            "user_id": [10],
            "recording_msid": ["recording-msid"],
            "artist_name": ["Artist"],
            "release_name": [None],
            "release_mbid": [None],
            "recording_name": ["Track"],
            "recording_mbid": [None],
            "artist_credit_mbids": [["artist-mbid", None]],
        })

        result = build_raw_listens_arrow_table(table, "load-1")

        self.assertEqual(result.column_names, [
            "load_id",
            "listened_at",
            "created",
            "user_id",
            "recording_msid",
            "artist_name",
            "release_name",
            "release_mbid",
            "recording_name",
            "recording_mbid",
            "artist_credit_mbids",
        ])
        self.assertEqual(result.to_pylist(), [{
            "load_id": "load-1",
            "listened_at": listened_at,
            "created": created,
            "user_id": 10,
            "recording_msid": "recording-msid",
            "artist_name": "Artist",
            "release_name": "",
            "release_mbid": "",
            "recording_name": "Track",
            "recording_mbid": "",
            "artist_credit_mbids": ["artist-mbid"],
        }])


class FakeClient:
    def __init__(self):
        self.commands = []
        self.inserts = []

    def command(self, sql, parameters=None, settings=None):
        self.commands.append((sql, settings))
        self.parameters = parameters

    def insert_arrow(self, table, arrow_table, settings=None):
        self.inserts.append((table, arrow_table, settings))


class RawListenProcessingTestCase(unittest.TestCase):

    def test_process_raw_listens_single_chunk_scopes_to_load(self):
        client = FakeClient()

        process_raw_listens(client, "load-1", chunks=1)

        self.assertEqual(len(client.commands), 1)
        sql, settings = client.commands[0]
        self.assertEqual(sql, build_process_raw_listens_query())
        self.assertEqual(settings, PROCESS_RAW_LISTENS_SETTINGS)
        self.assertEqual(client.parameters, {"load_id": "load-1"})
        self.assertIn("WHERE r.load_id = {load_id:String}", sql)
        self.assertNotIn("user_id %", sql)

    def test_process_raw_listens_default_chunks_runs_one_query_per_bucket(self):
        client = FakeClient()

        process_raw_listens(client, "load-1")

        self.assertEqual(len(client.commands), PROCESS_RAW_LISTENS_CHUNKS)
        for i, (sql, settings) in enumerate(client.commands):
            self.assertIn(
                f"WHERE r.load_id = {{load_id:String}} AND r.user_id % {PROCESS_RAW_LISTENS_CHUNKS} = {i}",
                sql,
                f"chunk {i} missing user_id bucket filter",
            )
            # the IN-set subqueries must be scoped to the same bucket
            self.assertEqual(
                sql.count(f"WHERE load_id = {{load_id:String}} AND user_id % {PROCESS_RAW_LISTENS_CHUNKS} = {i}"),
                4,
            )
            self.assertEqual(settings, PROCESS_RAW_LISTENS_SETTINGS)

    def test_process_raw_listens_chunks_keep_metadata_joins_intact(self):
        client = FakeClient()

        process_raw_listens(client, "load-1", chunks=4)

        for sql, _ in client.commands:
            # The empty-mbid filters from the bug fix must survive the chunking rewrite.
            self.assertIn("WHERE artist_mbid != ''", sql)
            self.assertIn("WHERE recording_mbid != ''", sql)
            self.assertIn("WHERE release_mbid != ''", sql)

    def test_process_raw_listens_sql_skips_existing_and_deleted_listens(self):
        sql = build_process_raw_listens_query()
        # already in listens (re-delivered listen)
        self.assertIn("NOT IN (\n            SELECT user_id, listened_at, recording_msid\n            FROM listens", sql)
        # existing-listen set bounded to the load's created range
        self.assertIn("AND created >= (\n                SELECT min(created) FROM raw_listens", sql)
        self.assertIn("AND created <= (\n                SELECT max(created) FROM raw_listens", sql)
        # deleted in LB after the dump was created, matched on created as well
        self.assertIn("(r.user_id, r.listened_at, r.recording_msid, r.created) NOT IN", sql)
        self.assertIn("FROM deleted_listens", sql)
        # user's listen history deleted
        self.assertIn("FROM deleted_user_listen_history", sql)
        self.assertIn("r.created > duh.max_created", sql)
        # duplicates within the same load
        self.assertIn("LIMIT 1 BY r.user_id, r.listened_at, r.recording_msid", sql)

    def test_process_raw_listens_sql_drops_in_subqueries(self):
        self.assertNotIn("WHERE recording_mbid IN", PROCESS_RAW_LISTENS)
        self.assertNotIn("WHERE release_mbid IN", PROCESS_RAW_LISTENS)
        self.assertNotIn("WHERE artist_mbid IN", PROCESS_RAW_LISTENS)

    def test_process_raw_listens_groups_by_raw_listen_id(self):
        self.assertIn("GROUP BY expanded.raw_listen_id", PROCESS_RAW_LISTENS)

    def test_process_raw_listens_settings_enable_external_spill(self):
        self.assertGreater(PROCESS_RAW_LISTENS_SETTINGS["max_bytes_before_external_group_by"], 0)
        self.assertGreater(PROCESS_RAW_LISTENS_SETTINGS["max_bytes_before_external_sort"], 0)
        self.assertEqual(PROCESS_RAW_LISTENS_SETTINGS["async_insert"], 0)

    def test_process_raw_listens_excludes_empty_mbid_rows_from_metadata_joins(self):
        # Without these filters, LIMIT 1 BY '' picks an arbitrary metadata row and
        # every metadata-less listen gets attributed to it, surfacing as one
        # bogus high-count artist/recording/release in user stats.
        self.assertIn("WHERE artist_mbid != ''", PROCESS_RAW_LISTENS)
        self.assertIn("WHERE recording_mbid != ''", PROCESS_RAW_LISTENS)
        self.assertIn("WHERE release_mbid != ''", PROCESS_RAW_LISTENS)

    def test_drop_raw_listens_partition(self):
        client = FakeClient()
        drop_raw_listens_partition(client, "load-1")
        self.assertEqual(client.commands, [("ALTER TABLE raw_listens DROP PARTITION {load_id:String}", None)])
        self.assertEqual(client.parameters, {"load_id": "load-1"})

    def test_truncate_derived_tables_keeps_deleted_listen_records(self):
        client = FakeClient()
        truncate_derived_tables(client)
        truncated = [sql.split()[-1] for sql, _ in client.commands]
        self.assertEqual(truncated, REPLACE_TRUNCATE_TABLES)
        self.assertIn("listens", truncated)
        self.assertIn("user_artist_stats_daily", truncated)
        self.assertNotIn("deleted_listens", truncated)
        self.assertNotIn("deleted_user_listen_history", truncated)
        self.assertNotIn("raw_listens", truncated)


class LoadDumpFlowTestCase(unittest.TestCase):

    def _run_load_dump(self, tmpdir, replace=False, fail_files=False):
        from clickhouse.stats import load_dump as ld
        clients = []

        def fake_create_client(*args, **kwargs):
            client = mock.MagicMock()
            client.query.return_value.first_row = [0]
            clients.append(client)
            return client

        def fake_load_file(file_path, load_id, host, port, username, password, database, progress=None):
            if fail_files:
                raise RuntimeError("boom")
            progress.update(3)
            return 3

        with mock.patch.object(ld, "create_client", side_effect=fake_create_client), \
                mock.patch.object(ld, "ensure_stats_schema"), \
                mock.patch.object(ld, "find_parquet_files", return_value=[tmpdir / "a.parquet"]), \
                mock.patch.object(ld, "_load_parquet_file", side_effect=fake_load_file), \
                mock.patch.object(ld, "process_raw_listens") as mock_process, \
                mock.patch.object(ld, "drop_raw_listens_partition") as mock_drop, \
                mock.patch.object(ld, "truncate_derived_tables") as mock_truncate:
            result = ld.load_dump(str(tmpdir), replace=replace, process_chunks=2)
        return result, mock_process, mock_drop, mock_truncate

    def test_load_dump_processes_only_its_load_and_drops_partition(self):
        import tempfile
        from pathlib import Path
        with tempfile.TemporaryDirectory() as tmp:
            result, mock_process, mock_drop, mock_truncate = self._run_load_dump(Path(tmp))

        self.assertEqual(result["total_inserted"], 3)
        self.assertEqual(result["errors"], [])
        load_id = result["load_id"]
        mock_process.assert_called_once_with(mock.ANY, load_id, chunks=2)
        mock_drop.assert_called_once_with(mock.ANY, load_id)
        mock_truncate.assert_not_called()

    def test_load_dump_replace_truncates_before_loading(self):
        import tempfile
        from pathlib import Path
        with tempfile.TemporaryDirectory() as tmp:
            _, mock_process, _, mock_truncate = self._run_load_dump(Path(tmp), replace=True)
        mock_truncate.assert_called_once()
        mock_process.assert_called_once()

    def test_load_dump_does_not_process_partial_loads(self):
        import tempfile
        from pathlib import Path
        with tempfile.TemporaryDirectory() as tmp:
            result, mock_process, mock_drop, _ = self._run_load_dump(Path(tmp), fail_files=True)
        self.assertEqual(len(result["errors"]), 1)
        mock_process.assert_not_called()
        mock_drop.assert_not_called()


if __name__ == "__main__":
    unittest.main()
