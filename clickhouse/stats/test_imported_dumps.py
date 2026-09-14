import unittest
from datetime import datetime, timedelta, timezone
from clickhouse.tests import ClickHouseTestCase

from clickhouse.stats.ftp import DumpType
from clickhouse.stats.imported_dumps import (
    get_incremental_dumps_since_latest_full,
    get_latest_full_dump,
    record_imported_dump,
    select_missing_incremental_dumps,
)


class ImportedDumpsTestCase(ClickHouseTestCase):

    def test_empty_history(self):
        self.assertIsNone(get_latest_full_dump(self.client))
        self.assertEqual(get_incremental_dumps_since_latest_full(self.client), set())

    def test_records_default_timestamp_and_type(self):
        record_imported_dump(self.client, 10, DumpType.INCREMENTAL)
        self.assertEqual(get_incremental_dumps_since_latest_full(self.client), {10})
        self.assertIsNone(get_latest_full_dump(self.client))

    def test_latest_full_and_incrementals_preserve_millisecond_cutoff(self):
        base = datetime(2026, 6, 10, 0, 21, 48, 531000, tzinfo=timezone.utc)
        record_imported_dump(self.client, 2500, DumpType.FULL, base)
        record_imported_dump(self.client, 2501, DumpType.INCREMENTAL, base - timedelta(milliseconds=1))
        record_imported_dump(self.client, 2502, DumpType.INCREMENTAL, base)
        record_imported_dump(self.client, 2503, DumpType.INCREMENTAL, base + timedelta(milliseconds=1))
        self.assertEqual(get_latest_full_dump(self.client), {"dump_id": 2500, "imported_at": base.replace(tzinfo=None)})
        self.assertEqual(get_incremental_dumps_since_latest_full(self.client), {2502, 2503})
        # A newer full import supersedes the incrementals, even with a lower dump id.
        record_imported_dump(self.client, 2499, DumpType.FULL, base + timedelta(milliseconds=2))
        self.assertEqual(get_latest_full_dump(self.client)["dump_id"], 2499)
        self.assertEqual(get_incremental_dumps_since_latest_full(self.client), set())
        # Re-importing a dump replaces its timestamp in FINAL reads.
        record_imported_dump(self.client, 2501, DumpType.INCREMENTAL, base + timedelta(milliseconds=3))
        self.assertEqual(get_incremental_dumps_since_latest_full(self.client), {2501})

    def test_aware_timestamp_is_stored_in_utc(self):
        aware = datetime(2026, 6, 10, 2, 21, 48, 531000, tzinfo=timezone(timedelta(hours=2)))
        record_imported_dump(self.client, 1, DumpType.FULL, aware)
        self.assertEqual(get_latest_full_dump(self.client)["imported_at"], aware.astimezone(timezone.utc).replace(tzinfo=None))


class SelectMissingIncrementalDumpsTestCase(unittest.TestCase):

    AVAILABLE = [
        (2499, "listenbrainz-dump-2499-20260608-000003-incremental"),
        (2501, "listenbrainz-dump-2501-20260610-000003-incremental"),
        (2502, "listenbrainz-dump-2502-20260611-000003-incremental"),
        (2503, "listenbrainz-dump-2503-20260612-000003-incremental"),
    ]

    def test_skips_dumps_covered_by_the_full_dump(self):
        missing = select_missing_incremental_dumps(self.AVAILABLE, set(), after_dump_id=2500)

        self.assertEqual([dump_id for dump_id, _ in missing], [2501, 2502, 2503])

    def test_skips_already_imported_dumps(self):
        missing = select_missing_incremental_dumps(self.AVAILABLE, {2502}, after_dump_id=2500)

        self.assertEqual([dump_id for dump_id, _ in missing], [2501, 2503])

    def test_returns_oldest_first(self):
        shuffled = list(reversed(self.AVAILABLE))

        missing = select_missing_incremental_dumps(shuffled, set(), after_dump_id=2500)

        self.assertEqual([dump_id for dump_id, _ in missing], [2501, 2502, 2503])

    def test_without_a_full_dump_id_keeps_every_unimported_dump(self):
        missing = select_missing_incremental_dumps(self.AVAILABLE, {2499}, after_dump_id=None)

        self.assertEqual([dump_id for dump_id, _ in missing], [2501, 2502, 2503])


if __name__ == "__main__":
    unittest.main()
