from clickhouse.stats.ftp import DumpType
from clickhouse.stats.import_state import INCREMENTAL_DUMP_STATE, get_import_state, record_imported_dump
from clickhouse.tests import ClickHouseTestCase


class ImportStateTestCase(ClickHouseTestCase):

    def mark(self):
        return get_import_state(self.client, INCREMENTAL_DUMP_STATE)

    def test_incremental_dumps_advance_the_mark(self):
        self.assertEqual(self.mark(), 0)
        record_imported_dump(self.client, 2501, DumpType.INCREMENTAL)
        self.assertEqual(self.mark(), 2501)
        # a manual load of an older dump does not move it back
        record_imported_dump(self.client, 2490, DumpType.INCREMENTAL)
        self.assertEqual(self.mark(), 2501)

    def test_full_dump_restarts_the_mark(self):
        record_imported_dump(self.client, 2501, DumpType.INCREMENTAL)
        record_imported_dump(self.client, 2490, DumpType.FULL)
        self.assertEqual(self.mark(), 2490)

