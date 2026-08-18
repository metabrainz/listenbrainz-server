import unittest
from datetime import datetime, timezone
from unittest import mock

from clickhouse.stats import deleted_listens as dl


class FakeResult:
    def __init__(self, rows):
        self.result_rows = rows
        self.first_row = rows[0] if rows else None


class FakeClient:
    """Records commands/inserts; answers queries from a small script."""

    def __init__(self, listens_matching=0, import_state=None):
        self.commands = []
        self.inserts = []
        self.queries = []
        self.listens_matching = listens_matching
        self.import_state = import_state or {}

    def query(self, sql, parameters=None):
        self.queries.append((sql, parameters))
        if "FROM import_state" in sql:
            name = parameters["name"]
            return FakeResult([(self.import_state[name],)] if name in self.import_state else [])
        if sql.startswith("SELECT count() FROM listens"):
            return FakeResult([(self.listens_matching,)])
        raise AssertionError(f"unexpected query {sql}")

    def command(self, sql, parameters=None, settings=None):
        self.commands.append((" ".join(sql.split()), parameters))

    def insert(self, table, rows, column_names=None):
        self.inserts.append((table, rows, column_names))


class ImportStateTestCase(unittest.TestCase):

    def test_get_import_state_defaults_to_zero(self):
        client = FakeClient()
        self.assertEqual(dl.get_import_state(client, "listen_delete_metadata"), 0)

    def test_get_import_state_returns_stored_value(self):
        client = FakeClient(import_state={"listen_delete_metadata": 42})
        self.assertEqual(dl.get_import_state(client, "listen_delete_metadata"), 42)

    def test_set_import_state(self):
        client = FakeClient()
        dl.set_import_state(client, "listen_delete_metadata", 42)
        self.assertEqual(client.commands[0][1], {"name": "listen_delete_metadata", "last_id": 42})


class ImportRecordsTestCase(unittest.TestCase):

    @mock.patch.object(dl, "_fetch_new_rows")
    def test_import_deleted_listens_records_converts_to_utc_and_tracks_max_id(self, mock_fetch):
        listened_at = datetime(2026, 5, 1, 12, 0, tzinfo=timezone.utc)
        created = datetime(2026, 5, 1, 12, 5, tzinfo=timezone.utc)
        mock_fetch.return_value = [
            [(11, 1, listened_at, "msid-1", created)],
            [(12, 2, listened_at, "msid-2", created)],
        ]
        client = FakeClient(import_state={"listen_delete_metadata": 10})

        imported, prev_id, new_id = dl.import_deleted_listens_records("dsn", client, 1)

        self.assertEqual((imported, prev_id, new_id), (2, 10, 12))
        mock_fetch.assert_called_once_with("dsn", dl.DELETED_LISTENS_PG_QUERY, 10, 1)
        self.assertEqual(len(client.inserts), 2)
        table, rows, columns = client.inserts[0]
        self.assertEqual(table, "deleted_listens")
        self.assertEqual(columns, ["id", "user_id", "listened_at", "recording_msid", "created"])
        # naive UTC datetimes for clickhouse
        self.assertEqual(rows[0], (11, 1, listened_at.replace(tzinfo=None), "msid-1", created.replace(tzinfo=None)))

    @mock.patch.object(dl, "_fetch_new_rows", return_value=[])
    def test_import_deleted_listens_records_nothing_new(self, _mock_fetch):
        client = FakeClient(import_state={"listen_delete_metadata": 10})
        self.assertEqual(dl.import_deleted_listens_records("dsn", client, 100), (0, 10, 10))
        self.assertEqual(client.inserts, [])

    @mock.patch.object(dl, "_fetch_new_rows")
    def test_import_deleted_user_history_records(self, mock_fetch):
        max_created = datetime(2026, 5, 1, 12, 5, tzinfo=timezone.utc)
        mock_fetch.return_value = [[(3, 7, max_created)]]
        client = FakeClient()

        imported, prev_id, new_id = dl.import_deleted_user_history_records("dsn", client, 100)

        self.assertEqual((imported, prev_id, new_id), (1, 0, 3))
        mock_fetch.assert_called_once_with("dsn", dl.DELETED_USER_HISTORY_PG_QUERY, 0, 100)
        self.assertEqual(client.inserts[0][0], "deleted_user_listen_history")
        self.assertEqual(client.inserts[0][1], [(3, 7, max_created.replace(tzinfo=None))])


class ApplyDeletionsTestCase(unittest.TestCase):

    def test_apply_deleted_listens_reverses_stats_then_deletes_then_clears_cache_state(self):
        client = FakeClient(listens_matching=5)

        removed = dl.apply_deleted_listens(client, 10)

        self.assertEqual(removed, 5)
        commands = [c for c, _ in client.commands]
        self.assertEqual(len(commands), 5)
        # -1 into each daily table, mirroring the MV filters
        self.assertIn("INSERT INTO user_artist_stats_daily", commands[0])
        self.assertIn("arrayJoin(artist_ids), toInt64(-1)", commands[0])
        self.assertIn("WHERE notEmpty(artist_ids) AND", commands[0])
        self.assertIn("INSERT INTO user_recording_stats_daily", commands[1])
        self.assertIn("WHERE recording_id != 0 AND", commands[1])
        self.assertIn("INSERT INTO user_release_group_stats_daily", commands[2])
        self.assertIn("WHERE release_group_id != 0 AND", commands[2])
        # then the listens are removed
        self.assertTrue(commands[3].startswith("DELETE FROM listens WHERE"))
        self.assertIn("FROM deleted_listens WHERE id > {last_id:UInt64}", commands[3])
        self.assertIn("(user_id, listened_at, recording_msid, created) IN", commands[3])
        # and the users are marked stale
        self.assertTrue(commands[4].startswith("ALTER TABLE user_stats_cache_state DELETE WHERE user_id IN"))
        for _, parameters in client.commands:
            self.assertEqual(parameters, {"last_id": 10})

    def test_apply_deleted_listens_noop_when_nothing_matches(self):
        client = FakeClient(listens_matching=0)
        self.assertEqual(dl.apply_deleted_listens(client, 10), 0)
        self.assertEqual(client.commands, [])

    def test_apply_deleted_user_history_uses_max_created_bound(self):
        client = FakeClient(listens_matching=2)

        removed = dl.apply_deleted_user_history(client, 3)

        self.assertEqual(removed, 2)
        delete_sql = client.commands[3][0]
        self.assertTrue(delete_sql.startswith("DELETE FROM listens WHERE"))
        self.assertIn("FROM deleted_user_listen_history WHERE id > {last_id:UInt64}", delete_sql)
        self.assertIn("l.created <= d.max_created", delete_sql)


class ImportDeletedListensTestCase(unittest.TestCase):

    @mock.patch.object(dl, "ensure_stats_schema")
    @mock.patch.object(dl, "set_import_state")
    @mock.patch.object(dl, "apply_deleted_user_history", return_value=4)
    @mock.patch.object(dl, "apply_deleted_listens", return_value=3)
    @mock.patch.object(dl, "import_deleted_user_history_records", return_value=(1, 0, 2))
    @mock.patch.object(dl, "import_deleted_listens_records", return_value=(2, 10, 12))
    def test_import_applies_new_records_and_advances_state(
        self, _mock_listens, _mock_users, mock_apply_listens, mock_apply_users, mock_set_state, _mock_schema
    ):
        client = FakeClient()

        summary = dl.import_deleted_listens("dsn", client, batch_size=50)

        mock_apply_listens.assert_called_once_with(client, 10)
        mock_apply_users.assert_called_once_with(client, 0)
        mock_set_state.assert_has_calls([
            mock.call(client, dl.DELETED_LISTENS_STATE, 12),
            mock.call(client, dl.DELETED_USER_HISTORY_STATE, 2),
        ])
        self.assertEqual(summary["deleted_listens_imported"], 2)
        self.assertEqual(summary["deleted_listens_removed"], 3)
        self.assertEqual(summary["deleted_user_histories_imported"], 1)
        self.assertEqual(summary["deleted_user_listens_removed"], 4)

    @mock.patch.object(dl, "ensure_stats_schema")
    @mock.patch.object(dl, "set_import_state")
    @mock.patch.object(dl, "apply_deleted_user_history")
    @mock.patch.object(dl, "apply_deleted_listens")
    @mock.patch.object(dl, "import_deleted_user_history_records", return_value=(0, 2, 2))
    @mock.patch.object(dl, "import_deleted_listens_records", return_value=(0, 12, 12))
    def test_import_is_a_noop_without_new_records(
        self, _mock_listens, _mock_users, mock_apply_listens, mock_apply_users, mock_set_state, _mock_schema
    ):
        summary = dl.import_deleted_listens("dsn", FakeClient())

        mock_apply_listens.assert_not_called()
        mock_apply_users.assert_not_called()
        mock_set_state.assert_not_called()
        self.assertEqual(summary["deleted_listens_removed"], 0)


if __name__ == "__main__":
    unittest.main()
