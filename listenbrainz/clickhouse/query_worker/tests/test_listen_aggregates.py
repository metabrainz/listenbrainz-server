from unittest.mock import patch

from listenbrainz.clickhouse.query_worker.listens import aggregates
from listenbrainz.clickhouse.query_worker.listens.aggregate_tables import HOURLY_COUNTS, ListenAggregate
from listenbrainz.clickhouse.query_worker.listens.deletions import delete_matching_listens
from listenbrainz.clickhouse.query_worker.listens.load_dump import merge_staged_listens
from listenbrainz.clickhouse.query_worker.tests import DumpImportTestCase


class ListenAggregateTestCase(DumpImportTestCase):
    def test_remove_midnight_count_from_existing_aggregate(self):
        self.load_fixture("full-dump-1")
        self.client.command("ALTER TABLE hourly_listen_counts ADD COLUMN midnight_listen_count Int64")
        aggregates.ensure_aggregates(self.client)
        columns = self.client.query("SELECT * FROM hourly_listen_counts LIMIT 0").column_names
        self.assertNotIn("midnight_listen_count", columns)
        self.client.command("INSERT INTO listens (user_id, listened_at) VALUES (7, '2024-01-01 00:00:00')")
        self.assert_hourly_counts_match_listens()

    def test_upgrade_to_direct_view_target(self):
        self.load_fixture("full-dump-1")
        legacy = "listen_changes_hourly_listen_counts"
        self.client.command("DROP VIEW hourly_listen_counts_mv")
        self.client.command(f"CREATE TABLE {legacy} CLONE AS hourly_listen_counts")
        self.client.command(f"CREATE MATERIALIZED VIEW {legacy}_mv TO {legacy} AS "
                            + HOURLY_COUNTS.select.format(source=aggregates.LIVE_STREAM))
        aggregates.ensure_aggregates(self.client)
        self.assertEqual(self.client.command(f"EXISTS TABLE {legacy}"), 0)
        self.assertEqual(self.client.command(f"EXISTS TABLE {legacy}_mv"), 0)
        self.assert_hourly_counts_match_listens()
        self.client.command("INSERT INTO listens (user_id, listened_at) VALUES (7, '2024-01-01 00:00:00')")
        self.assert_hourly_counts_match_listens()

    def test_register_aggregate_on_existing_listens(self):
        self.load_fixture("full-dump-1")
        hourly_uuid = self.client.command(
            "SELECT uuid FROM system.tables WHERE database = currentDatabase() AND name = 'hourly_listen_counts'"
        )
        by_artist = ListenAggregate(
            name="test_artist_counts",
            source_columns=("user_id", "artist_name"),
            columns="user_id UInt32, artist_name String, listens Int64",
            engine="SummingMergeTree ORDER BY (user_id, artist_name)",
            select="SELECT user_id, artist_name, sum(delta) AS listens FROM {source} GROUP BY user_id, artist_name",
        )

        def check_both_tables():
            self.assert_hourly_counts_match_listens()
            expected = self.client.query("""
                SELECT user_id, artist_name, count() FROM listens
                GROUP BY user_id, artist_name ORDER BY user_id, artist_name
            """).result_rows
            actual = self.client.query("""
                SELECT user_id, artist_name, sum(listens) AS total FROM test_artist_counts
                GROUP BY user_id, artist_name HAVING total != 0 ORDER BY user_id, artist_name
            """).result_rows
            self.assertEqual(actual, expected)

        with patch.object(aggregates, "LISTEN_AGGREGATES", (HOURLY_COUNTS, by_artist)):
            aggregates.ensure_aggregates(self.client)
            self.assertEqual(hourly_uuid, self.client.command(
                "SELECT uuid FROM system.tables WHERE database = currentDatabase() AND name = 'hourly_listen_counts'"
            ))
            check_both_tables()
            for fixture in ("incremental-dump-2", "incremental-dump-2", "full-dump-1"):
                self.load_fixture(fixture)
                check_both_tables()

            # A resubmission moves the count to a different artist while keeping the same listen key.
            self.client.command("CREATE TABLE replacement AS listens")
            self.client.command("""
                INSERT INTO replacement SELECT * REPLACE (created + INTERVAL 1 DAY AS created,
                    'corrected artist' AS artist_name) FROM listens LIMIT 1
            """)
            merge_staged_listens(self.client, "replacement")
            check_both_tables()
            delete_matching_listens(self.client, "listens", "artist_name = 'corrected artist'", aggregates.LIVE_STREAM)
            check_both_tables()
