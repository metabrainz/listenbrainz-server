import unittest
from datetime import datetime, timezone
from unittest import mock

import pyarrow as pa

from clickhouse.stats.ftp import DumpType
from clickhouse.stats.load_dump import (
    PROCESS_RAW_LISTENS_ROWS_PER_CHUNK,
    RAW_LISTEN_COLUMNS,
    choose_process_chunks,
    PROCESS_RAW_LISTENS_SETTINGS,
    REPLACE_TRUNCATE_TABLES,
    build_process_raw_listens_query,
    build_raw_listens_arrow_table,
    create_client,
    drop_raw_listens_partition,
    import_missing_incremental_dumps,
    load_from_ftp,
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
            # metadata columns of the dump are not loaded
            "artist_name": ["Artist"],
            "recording_name": ["Track"],
            "artist_credit_mbids": [["artist-mbid", None]],
        })

        result = build_raw_listens_arrow_table(table, "load-1")

        self.assertEqual(result.column_names, RAW_LISTEN_COLUMNS)
        self.assertEqual(result.to_pylist(), [{
            "load_id": "load-1",
            "listened_at": listened_at,
            "created": created,
            "user_id": 10,
            "recording_msid": "recording-msid",
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

    def test_process_raw_listens_multiple_chunks_runs_one_query_per_bucket(self):
        client = FakeClient()
        chunks = 16

        process_raw_listens(client, "load-1", chunks=chunks)

        self.assertEqual(len(client.commands), chunks)
        for i, (sql, settings) in enumerate(client.commands):
            self.assertIn(
                f"WHERE r.load_id = {{load_id:String}} AND r.user_id % {chunks} = {i}",
                sql,
                f"chunk {i} missing user_id bucket filter",
            )
            # the IN-set subqueries must be scoped to the same bucket
            self.assertEqual(
                sql.count(f"WHERE load_id = {{load_id:String}} AND user_id % {chunks} = {i}"),
                4,
            )
            self.assertEqual(settings, PROCESS_RAW_LISTENS_SETTINGS)

    def test_choose_process_chunks_scales_with_load_size(self):
        self.assertEqual(choose_process_chunks(0), 1)
        self.assertEqual(choose_process_chunks(PROCESS_RAW_LISTENS_ROWS_PER_CHUNK), 1)
        self.assertEqual(choose_process_chunks(PROCESS_RAW_LISTENS_ROWS_PER_CHUNK + 1), 2)
        self.assertEqual(choose_process_chunks(PROCESS_RAW_LISTENS_ROWS_PER_CHUNK * 2), 2)
        self.assertEqual(choose_process_chunks(PROCESS_RAW_LISTENS_ROWS_PER_CHUNK * 2 + 1), 3)
        self.assertEqual(choose_process_chunks(1_500_000_000), 15)

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

    def test_process_raw_listens_sql_only_copies_listen_columns(self):
        sql = build_process_raw_listens_query()
        self.assertIn("INSERT INTO listens\n    (listened_at, created, user_id, recording_msid)", sql)
        self.assertNotIn("JOIN", sql.replace("LEFT JOIN (\n        SELECT user_id, max(max_created)", ""))
        for name in ("metadata", "artist", "recording_mbid", "release"):
            self.assertNotIn(name, sql)

    def test_process_raw_listens_settings_enable_external_spill(self):
        self.assertGreater(PROCESS_RAW_LISTENS_SETTINGS["max_bytes_before_external_group_by"], 0)
        self.assertGreater(PROCESS_RAW_LISTENS_SETTINGS["max_bytes_before_external_sort"], 0)
        self.assertEqual(PROCESS_RAW_LISTENS_SETTINGS["async_insert"], 0)

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
        self.assertEqual(truncated, ["listens", "user_stats_cache_state", "stats_cache_state"])
        self.assertNotIn("deleted_listens", truncated)
        self.assertNotIn("deleted_user_listen_history", truncated)
        self.assertNotIn("raw_listens", truncated)


class LoadDumpFlowTestCase(unittest.TestCase):

    def _run_load_dump(self, tmpdir, replace=False, fail_files=False, process_chunks=2):
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
            result = ld.load_dump(str(tmpdir), replace=replace, process_chunks=process_chunks)
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

    def test_load_dump_picks_chunks_from_load_size_by_default(self):
        import tempfile
        from pathlib import Path
        with tempfile.TemporaryDirectory() as tmp:
            result, mock_process, _, _ = self._run_load_dump(Path(tmp), process_chunks=None)

        # 3 raw rows -> well under the single-chunk threshold
        mock_process.assert_called_once_with(mock.ANY, result["load_id"], chunks=1)

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


CH_KWARGS = {
    "host": "localhost", "port": 8123, "username": "default", "password": "", "database": "default",
}


@mock.patch("clickhouse.stats.load_dump.shutil.rmtree")
@mock.patch("clickhouse.stats.load_dump._extract_archive", return_value="/tmp/parquet")
@mock.patch("clickhouse.stats.load_dump.FTPDumpDownloader")
class LoadFromFtpTestCase(unittest.TestCase):

    @staticmethod
    def _downloader(mock_downloader_class, dump_id=2534):
        downloader = mock_downloader_class.return_value
        downloader.download_dump_archive.return_value = ("/tmp/dump.tar", dump_id)
        return downloader

    @mock.patch("clickhouse.stats.load_dump._record_dump_import")
    @mock.patch("clickhouse.stats.load_dump.load_dump")
    def test_records_the_dump_it_loaded(self, mock_load_dump, mock_record, mock_downloader_class, *_):
        downloader = self._downloader(mock_downloader_class)
        mock_load_dump.return_value = {"errors": [], "total_inserted": 10, "files_completed": 1, "load_id": "abc"}

        result = load_from_ftp(dump_type=DumpType.INCREMENTAL, dump_id=2534, **CH_KWARGS)

        self.assertEqual(result["dump_id"], 2534)
        downloader.download_dump_archive.assert_called_once_with(DumpType.INCREMENTAL, mock.ANY, 2534)
        self.assertEqual(mock_record.call_args.args[:2], (2534, DumpType.INCREMENTAL))

    @mock.patch("clickhouse.stats.load_dump._record_dump_import")
    @mock.patch("clickhouse.stats.load_dump.load_dump")
    def test_does_not_record_a_dump_that_failed_to_load(self, mock_load_dump, mock_record, mock_downloader_class, *_):
        self._downloader(mock_downloader_class)
        mock_load_dump.return_value = {
            "errors": [("/tmp/0.parquet", "boom")], "total_inserted": 0, "files_completed": 0, "load_id": "abc",
        }

        load_from_ftp(dump_type=DumpType.INCREMENTAL, **CH_KWARGS)

        mock_record.assert_not_called()


class ImportMissingIncrementalDumpsTestCase(unittest.TestCase):

    AVAILABLE = [
        (2500, "listenbrainz-dump-2500-20260609-000003-incremental"),
        (2501, "listenbrainz-dump-2501-20260610-000003-incremental"),
        (2502, "listenbrainz-dump-2502-20260611-000003-incremental"),
    ]

    def setUp(self):
        self.mocks = {}
        for name in (
            "ensure_stats_schema", "create_client", "FTPDumpDownloader",
            "get_latest_full_dump", "get_incremental_dumps_since_latest_full", "load_from_ftp",
        ):
            patcher = mock.patch(f"clickhouse.stats.load_dump.{name}")
            self.mocks[name] = patcher.start()
            self.addCleanup(patcher.stop)

        self.mocks["FTPDumpDownloader"].return_value.list_dump_ids.return_value = self.AVAILABLE
        self.mocks["get_latest_full_dump"].return_value = {"dump_id": 2499, "imported_at": datetime(2026, 6, 9)}
        self.mocks["get_incremental_dumps_since_latest_full"].return_value = set()
        self.mocks["load_from_ftp"].side_effect = lambda **kwargs: self._loaded(kwargs["dump_id"])

    @staticmethod
    def _loaded(dump_id, errors=None):
        return {
            "dump_id": dump_id, "load_id": f"load-{dump_id}", "total_inserted": 10,
            "files_completed": 1, "errors": errors or [],
        }

    def _loaded_dump_ids(self):
        return [call.kwargs["dump_id"] for call in self.mocks["load_from_ftp"].call_args_list]

    def test_loads_every_missing_dump_oldest_first(self):
        self.mocks["get_incremental_dumps_since_latest_full"].return_value = {2501}

        result = import_missing_incremental_dumps(**CH_KWARGS)

        self.assertEqual(self._loaded_dump_ids(), [2500, 2502])
        self.assertEqual([dump["dump_id"] for dump in result["imported"]], [2500, 2502])
        self.assertEqual(result["pending"], 0)
        self.assertEqual(result["errors"], [])

    def test_skips_dumps_the_full_dump_already_covers(self):
        self.mocks["get_latest_full_dump"].return_value = {"dump_id": 2500, "imported_at": datetime(2026, 6, 9)}

        import_missing_incremental_dumps(**CH_KWARGS)

        self.assertEqual(self._loaded_dump_ids(), [2501, 2502])

    def test_max_dumps_leaves_the_rest_pending(self):
        result = import_missing_incremental_dumps(max_dumps=2, **CH_KWARGS)

        self.assertEqual(self._loaded_dump_ids(), [2500, 2501])
        self.assertEqual(result["pending"], 1)

    def test_stops_at_the_first_failure_so_it_is_retried(self):
        def load(**kwargs):
            if kwargs["dump_id"] == 2501:
                raise RuntimeError("ftp timed out")
            return self._loaded(kwargs["dump_id"])

        self.mocks["load_from_ftp"].side_effect = load

        result = import_missing_incremental_dumps(**CH_KWARGS)

        self.assertEqual(self._loaded_dump_ids(), [2500, 2501])
        self.assertEqual([dump["dump_id"] for dump in result["imported"]], [2500])
        self.assertEqual(result["errors"], [(2501, "ftp timed out")])
        self.assertEqual(result["pending"], 2)

    def test_stops_when_a_dump_left_parquet_files_behind(self):
        self.mocks["load_from_ftp"].side_effect = lambda **kwargs: self._loaded(
            kwargs["dump_id"],
            errors=[("/tmp/0.parquet", "HTTP request URI invalid or too long")] if kwargs["dump_id"] == 2500 else None,
        )

        result = import_missing_incremental_dumps(**CH_KWARGS)

        self.assertEqual(result["imported"], [])
        self.assertEqual(result["errors"][0][0], 2500)
        self.assertIn("parquet file(s) failed to load", result["errors"][0][1])

    def test_without_a_full_dump_only_the_latest_is_loaded(self):
        self.mocks["get_latest_full_dump"].return_value = None

        import_missing_incremental_dumps(**CH_KWARGS)

        self.assertEqual(self._loaded_dump_ids(), [2502])

    def test_without_a_full_dump_the_latest_is_not_loaded_twice(self):
        self.mocks["get_latest_full_dump"].return_value = None
        self.mocks["get_incremental_dumps_since_latest_full"].return_value = {2502}

        import_missing_incremental_dumps(**CH_KWARGS)

        self.assertEqual(self._loaded_dump_ids(), [])


if __name__ == "__main__":
    unittest.main()
