from datetime import datetime

from listenbrainz.db.dump_entry import get_dump_entries, add_dump_entry
from listenbrainz.db.testing import DatabaseTestCase


class DumpEntryTestCase(DatabaseTestCase):

    def test_add_dump_entry(self):
        prev_dumps = get_dump_entries()
        add_dump_entry(datetime.today(), "incremental")
        now_dumps = get_dump_entries()
        self.assertEqual(len(now_dumps), len(prev_dumps) + 1)
