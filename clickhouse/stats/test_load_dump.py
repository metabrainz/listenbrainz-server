import unittest
from datetime import datetime, timezone

import pyarrow as pa

from clickhouse.stats.load_dump import (
    PROCESS_RAW_LISTENS_ROWS_PER_CHUNK,
    RAW_LISTEN_COLUMNS,
    build_raw_listens_arrow_table,
    choose_process_chunks,
)


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


class ChunkSizingTestCase(unittest.TestCase):
    def test_choose_process_chunks_scales_with_load_size(self):
        self.assertEqual(choose_process_chunks(0), 1)
        self.assertEqual(choose_process_chunks(PROCESS_RAW_LISTENS_ROWS_PER_CHUNK), 1)
        self.assertEqual(choose_process_chunks(PROCESS_RAW_LISTENS_ROWS_PER_CHUNK + 1), 2)
        self.assertEqual(choose_process_chunks(1_500_000_000), 15)
