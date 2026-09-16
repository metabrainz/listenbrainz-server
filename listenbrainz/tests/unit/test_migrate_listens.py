import unittest
from datetime import datetime, timezone
from unittest.mock import MagicMock, call, patch

import click
from flask import Flask

from listenbrainz.listenstore import migrate_listens


class MigrateListensTestCase(unittest.TestCase):

    def setUp(self):
        self.app = Flask(__name__)

    def test_insert_sql_uses_conflict_handler_when_unique_index_exists(self):
        with patch.object(migrate_listens, "_fetch_one", return_value=(1,)):
            query = migrate_listens._insert_sql(MagicMock(), require_unique=True)

        self.assertEqual(query, migrate_listens.INSERT_ON_CONFLICT_SQL)

    def test_insert_sql_allows_plain_insert_for_initial_full_copy(self):
        with self.app.app_context(), patch.object(migrate_listens, "_fetch_one", return_value=None):
            query = migrate_listens._insert_sql(MagicMock())

        self.assertEqual(query, migrate_listens.INSERT_SQL)

    def test_insert_sql_requires_unique_index_for_incremental_copy(self):
        with patch.object(migrate_listens, "_fetch_one", return_value=None):
            with self.assertRaisesRegex(click.ClickException, "run create-indexes successfully"):
                migrate_listens._insert_sql(MagicMock(), require_unique=True)

    def test_incremental_copy_requires_unique_index(self):
        source_conn = MagicMock()
        target_conn = MagicMock()
        checkpoint = datetime(2026, 8, 20, tzinfo=timezone.utc)
        missing_index = click.ClickException("missing unique index")

        with patch.object(migrate_listens, "connect_source", return_value=source_conn), \
                patch.object(migrate_listens, "connect_target", return_value=target_conn), \
                patch.object(migrate_listens, "_log_checkpoint", return_value=checkpoint), \
                patch.object(migrate_listens, "_insert_sql", side_effect=missing_index) as insert_sql:
            with self.assertRaisesRegex(click.ClickException, "missing unique index"):
                migrate_listens.migrate_incremental(checkpoint, None, 100)

        insert_sql.assert_called_once_with(target_conn, require_unique=True)
        source_conn.close.assert_called_once_with()
        target_conn.close.assert_called_once_with()

    def test_check_integrity_passes_for_complete_target_without_duplicates(self):
        target_conn = MagicMock()
        cursor = target_conn.cursor.return_value.__enter__.return_value
        cursor.fetchone.side_effect = [("listen",), (123, 0, 0)]

        with self.app.app_context(), \
                patch.object(migrate_listens, "connect_target", return_value=target_conn), \
                patch.object(migrate_listens, "_existing_partitions", return_value=(256, 256)):
            migrate_listens.check_integrity()

        self.assertEqual(cursor.execute.call_args_list, [
            call("SELECT to_regclass('listen')"),
            call(migrate_listens.TARGET_INTEGRITY_SQL),
        ])
        target_conn.rollback.assert_called_once_with()
        target_conn.close.assert_called_once_with()

    def test_check_integrity_fails_for_incomplete_partition_set(self):
        target_conn = MagicMock()
        cursor = target_conn.cursor.return_value.__enter__.return_value
        cursor.fetchone.return_value = ("listen",)

        with self.app.app_context(), \
                patch.object(migrate_listens, "connect_target", return_value=target_conn), \
                patch.object(migrate_listens, "_existing_partitions", return_value=(256, 255)):
            with self.assertRaisesRegex(click.ClickException, "255 of 256 required hash partitions"):
                migrate_listens.check_integrity()

        target_conn.close.assert_called_once_with()

    def test_check_integrity_fails_for_duplicate_listens(self):
        target_conn = MagicMock()
        cursor = target_conn.cursor.return_value.__enter__.return_value
        cursor.fetchone.side_effect = [("listen",), (125, 2, 1)]

        with self.app.app_context(), \
                patch.object(migrate_listens, "connect_target", return_value=target_conn), \
                patch.object(migrate_listens, "_existing_partitions", return_value=(256, 256)):
            with self.assertRaisesRegex(click.ClickException, "2 duplicate listens across 1 logical listen keys"):
                migrate_listens.check_integrity()

        target_conn.rollback.assert_called_once_with()
        target_conn.close.assert_called_once_with()


if __name__ == "__main__":
    unittest.main()
