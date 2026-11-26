from unittest.mock import patch

from listenbrainz.clickhouse.query_worker.listens import aggregates
from listenbrainz.clickhouse.query_worker.listens.aggregate_tables import HOURLY_COUNTS
from listenbrainz.clickhouse.query_worker.listens.deletions import delete_matching_listens
from listenbrainz.clickhouse.query_worker.listens.load_dump import merge_staged_listens
from listenbrainz.clickhouse.query_worker.listens.schema import ensure_schema
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
        self.client.command("DROP VIEW user_artist_stats_daily_mv")
        self.client.command("DROP TABLE user_artist_stats_daily")

        def check_both_tables():
            self.assert_hourly_counts_match_listens()
            expected = self.client.query("""
                SELECT user_id, toDate(listened_at, 'UTC') AS day, lowerUTF8(artist_name) AS name,
                       arrayJoin(emptyArrayToSingle(arrayMap(id -> toString(id), artist_credit_mbids))) AS mbid, count()
                  FROM listens GROUP BY user_id, day, name, mbid ORDER BY user_id, day, name, mbid
            """).result_rows
            actual = self.client.query("""
                SELECT user_id, day, lowerUTF8(display_name) AS name, mbid, sum(listen_count) AS total
                  FROM user_artist_stats_daily
                  JOIN (SELECT artist_id, min(display_name) AS display_name, min(artist_mbid) AS mbid
                          FROM artist_metadata GROUP BY artist_id) AS labels USING (artist_id)
                 GROUP BY user_id, day, name, mbid
                HAVING total != 0 ORDER BY user_id, day, name, mbid
            """).result_rows
            self.assertEqual(actual, expected)

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

    def test_full_import_publishes_artist_lookup_for_later_changes(self):
        self.load_fixture("full-dump-1")
        mbid = self.client.command("SELECT toString(arrayJoin(artist_credit_mbids)) FROM listens LIMIT 1")
        self.set_artist_cache([(42, mbid, "Canonical")])
        self.load_fixture("full-dump-1")
        self.set_artist_cache([(43, mbid, "Updated")])
        expected = self.client.command(
            "SELECT count() FROM (SELECT arrayJoin(artist_credit_mbids) AS id FROM listens) WHERE id = {id:UUID}",
            parameters={"id": mbid},
        )
        count_sql = "SELECT sum(listen_count) FROM user_artist_stats_daily WHERE artist_id = 42"
        self.assertEqual(self.client.command(count_sql), expected)
        self.client.command("INSERT INTO listens (user_id, artist_credit_mbids) VALUES (119999, [{id:UUID}])",
                            parameters={"id": mbid})
        self.assertEqual(self.client.command(count_sql), expected + 1)
        delete_matching_listens(self.client, "listens", "has(artist_credit_mbids, {id:UUID})",
                                aggregates.LIVE_STREAM, {"id": mbid})
        self.assertEqual(self.client.command(count_sql), 0)
        self.load_fixture("full-dump-1")
        self.assertEqual(self.client.command(count_sql), 0)
        self.assertEqual(self.client.query("""
            SELECT display_name, sum(listen_count) FROM user_artist_stats_daily
            JOIN (SELECT artist_id, min(display_name) AS display_name FROM artist_metadata GROUP BY artist_id) AS labels
            USING (artist_id) WHERE artist_id = 43 GROUP BY display_name
        """).result_rows, [("Updated", expected)])

    def test_schema_and_full_import_without_artist_cache(self):
        with patch("brainzutils.musicbrainz_db.engine", None):
            self.client.command("DROP VIEW artist_metadata_mv")
            ensure_schema(self.client)
            self.load_fixture("full-dump-1")
        self.assertEqual(self.client.command("EXISTS TABLE artist_metadata_cache"), 0)
        self.assertGreater(self.client.command("SELECT sum(listen_count) FROM user_artist_stats_daily"), 0)

    def test_full_replacement_skips_live_backfill_without_musicbrainz(self):
        self.load_fixture("full-dump-1")
        self.client.command("DROP VIEW user_artist_stats_daily_mv")
        self.client.command("DROP TABLE user_artist_stats_daily")
        with patch("brainzutils.musicbrainz_db.engine", None), patch.object(
                aggregates, "send_changes", wraps=aggregates.send_changes) as changes:
            self.load_fixture("full-dump-1")
        self.assertFalse(any(call.args[2:4] == ("listens", 1) for call in changes.call_args_list))
        self.assertGreater(self.client.command("SELECT sum(listen_count) FROM user_artist_stats_daily"), 0)

    def test_partial_metadata_publication_repairs_live_counts_and_labels(self):
        self.load_fixture("full-dump-1")
        mbid = self.client.command("SELECT toString(arrayJoin(artist_credit_mbids)) FROM listens LIMIT 1")
        original = type(self.client).command

        for artist_id, failure in [(42, RuntimeError), (43, SystemExit)]:
            with self.subTest(failure=failure):
                self.set_artist_cache([(artist_id, mbid, "Canonical")])

                def fail_metadata_exchange(client, sql, *args, **kwargs):
                    if sql.startswith("EXCHANGE TABLES") and sql.endswith(" AND artist_metadata"):
                        raise failure("metadata exchange failed")
                    return original(client, sql, *args, **kwargs)

                before = self.listens()
                with patch.object(type(self.client), "command", fail_metadata_exchange):
                    with self.assertRaisesRegex(failure, "metadata exchange failed"):
                        self.load_fixture("full-dump-1")
                self.assertEqual(self.listens(), before)
                self.assertEqual(self.client.command("EXISTS TABLE listens_to_changes"), int(failure is RuntimeError))
                with patch.object(type(self.connection), "from_config", return_value=self.connection):
                    with aggregates.aggregate_snapshot(aggregates.DAILY_ARTIST_COUNTS) as snapshot:
                        self.assertEqual(snapshot.command("""
                            SELECT count() FROM stats_snapshot
                             WHERE artist_id NOT IN (SELECT artist_id FROM artist_metadata)
                        """), 0)
                        expected = self.client.command("""
                            SELECT count() FROM (SELECT arrayJoin(artist_credit_mbids) AS id FROM listens)
                             WHERE id = {mbid:UUID}
                        """, parameters={"mbid": mbid})
                        self.assertEqual(snapshot.command("""
                            SELECT sum(listen_count) FROM stats_snapshot WHERE artist_id = {id:UInt128}
                        """, parameters={"id": artist_id}), expected)
                self.assert_hourly_counts_match_listens()
