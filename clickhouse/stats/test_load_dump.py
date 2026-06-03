import unittest
from datetime import datetime, timezone
from unittest import mock

import pyarrow as pa

from clickhouse.stats.load_dump import (
    PROCESS_RAW_LISTENS,
    PROCESS_RAW_LISTENS_CHUNKS,
    PROCESS_RAW_LISTENS_SETTINGS,
    build_raw_listens_arrow_table,
    create_client,
    process_raw_listens,
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

        result = build_raw_listens_arrow_table(table)

        self.assertEqual(result.column_names, [
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

    def command(self, sql, settings=None):
        self.commands.append((sql, settings))

    def insert_arrow(self, table, arrow_table, settings=None):
        self.inserts.append((table, arrow_table, settings))


class RawListenProcessingTestCase(unittest.TestCase):

    def test_process_raw_listens_single_chunk_runs_unmodified_sql(self):
        client = FakeClient()

        process_raw_listens(client, chunks=1)

        self.assertEqual(len(client.commands), 1)
        sql, settings = client.commands[0]
        self.assertIs(sql, PROCESS_RAW_LISTENS)
        self.assertEqual(settings, PROCESS_RAW_LISTENS_SETTINGS)

    def test_process_raw_listens_default_chunks_runs_one_query_per_bucket(self):
        client = FakeClient()

        process_raw_listens(client)

        self.assertEqual(len(client.commands), PROCESS_RAW_LISTENS_CHUNKS)
        for i, (sql, settings) in enumerate(client.commands):
            self.assertIn(
                f"WHERE user_id % {PROCESS_RAW_LISTENS_CHUNKS} = {i}",
                sql,
                f"chunk {i} missing user_id bucket filter",
            )
            self.assertEqual(settings, PROCESS_RAW_LISTENS_SETTINGS)

    def test_process_raw_listens_chunks_keep_metadata_joins_intact(self):
        client = FakeClient()

        process_raw_listens(client, chunks=4)

        for sql, _ in client.commands:
            # The empty-mbid filters from the bug fix must survive the chunking rewrite.
            self.assertIn("WHERE artist_mbid != ''", sql)
            self.assertIn("WHERE recording_mbid != ''", sql)
            self.assertIn("WHERE release_mbid != ''", sql)

    def test_process_raw_listens_sql_reads_from_raw_listens(self):
        self.assertIn("FROM raw_listens AS r", PROCESS_RAW_LISTENS)
        self.assertNotIn("raw_listens_batch", PROCESS_RAW_LISTENS)

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


if __name__ == "__main__":
    unittest.main()
