from listenbrainz.clickhouse.query_worker.listens.import_state import INCREMENTAL_DUMP_STATE, get_import_state, set_import_state
from listenbrainz.clickhouse.query_worker.tests import ClickHouseTestCase


class ImportStateTestCase(ClickHouseTestCase):

    def mark(self):
        return get_import_state(self.client, INCREMENTAL_DUMP_STATE)

    def test_last_write_wins(self):
        self.assertEqual(self.mark(), 0)
        set_import_state(self.client, INCREMENTAL_DUMP_STATE, 2600)
        self.assertEqual(self.mark(), 2600)
        # a full dump import moves the mark back
        set_import_state(self.client, INCREMENTAL_DUMP_STATE, 2590)
        self.assertEqual(self.mark(), 2590)

    def test_last_write_wins_over_a_row_with_a_later_version(self):
        # e.g. a row versioned by a clock that was ahead
        self.client.command(f"INSERT INTO import_state (name, last_id, version) VALUES ('{INCREMENTAL_DUMP_STATE}', 2600, 1000000000000000)")
        set_import_state(self.client, INCREMENTAL_DUMP_STATE, 2590)
        self.assertEqual(self.mark(), 2590)
        set_import_state(self.client, "other", 7)
        self.assertEqual(self.mark(), 2590)
        self.assertEqual(get_import_state(self.client, "other"), 7)
