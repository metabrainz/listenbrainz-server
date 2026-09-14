import unittest
from datetime import datetime, timedelta, timezone
from unittest import mock

from clickhouse.stats.ftp import DumpType
from clickhouse.stats.imported_dumps import (
    get_incremental_dumps_since_latest_full,
    get_latest_full_dump,
    record_imported_dump,
    select_missing_incremental_dumps,
)


class ImportedDumpsTestCase(unittest.TestCase):

    def test_record_imported_dump_inserts_dump_type_value(self):
        ch_client = mock.Mock()

        record_imported_dump(ch_client, 2534, DumpType.INCREMENTAL)

        self.assertEqual(
            ch_client.command.call_args.kwargs["parameters"],
            {"dump_id": 2534, "dump_type": "incremental"},
        )

    def test_record_imported_dump_keeps_milliseconds_of_an_explicit_time(self):
        ch_client = mock.Mock()

        record_imported_dump(ch_client, 2534, DumpType.FULL, datetime(2026, 6, 10, 0, 21, 48, 531000))

        self.assertIn("parseDateTime64BestEffort", ch_client.command.call_args.args[0])
        self.assertEqual(
            ch_client.command.call_args.kwargs["parameters"],
            {"dump_id": 2534, "dump_type": "full", "imported_at": "2026-06-10 00:21:48.531"},
        )

    def test_record_imported_dump_normalises_an_aware_time_to_utc(self):
        ch_client = mock.Mock()
        aware = datetime(2026, 6, 10, 2, 21, 48, tzinfo=timezone(timedelta(hours=2)))

        record_imported_dump(ch_client, 2534, DumpType.FULL, aware)

        self.assertEqual(
            ch_client.command.call_args.kwargs["parameters"]["imported_at"],
            "2026-06-10 00:21:48.000",
        )

    def test_get_latest_full_dump_returns_none_when_never_imported(self):
        ch_client = mock.Mock()
        ch_client.query.return_value = mock.Mock(result_rows=[])

        self.assertIsNone(get_latest_full_dump(ch_client))

    def test_get_latest_full_dump_returns_id_and_time(self):
        imported_at = datetime(2026, 6, 9, 22, 0)
        ch_client = mock.Mock()
        ch_client.query.return_value = mock.Mock(
            result_rows=[(2500, imported_at)], first_row=(2500, imported_at)
        )

        self.assertEqual(
            get_latest_full_dump(ch_client),
            {"dump_id": 2500, "imported_at": imported_at},
        )

    def test_incremental_dumps_since_latest_full_compares_in_clickhouse(self):
        ch_client = mock.Mock()
        ch_client.query.return_value = mock.Mock(result_rows=[(2501,), (2502,)])

        self.assertEqual(get_incremental_dumps_since_latest_full(ch_client), {2501, 2502})

        query = ch_client.query.call_args.args[0]
        # the cutoff must stay a subquery: a DateTime64(3) bound passed back in as a
        # parameter loses its milliseconds
        self.assertIn("SELECT max(imported_at)", query)
        self.assertEqual(
            ch_client.query.call_args.kwargs["parameters"],
            {"dump_type": "incremental", "full_dump_type": "full"},
        )


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
