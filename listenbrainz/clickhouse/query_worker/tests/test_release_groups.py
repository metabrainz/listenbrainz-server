import json
from unittest.mock import patch
from uuid import UUID

import pyarrow.parquet as pq

from listenbrainz.clickhouse.query_worker.listens.aggregates import LIVE_STREAM
from listenbrainz.clickhouse.query_worker.listens.deletions import delete_matching_listens
from listenbrainz.clickhouse.query_worker.listens.load_dump import merge_staged_listens
from listenbrainz.clickhouse.query_worker.listens.schema import ensure_schema
from listenbrainz.clickhouse.query_worker.metadata_tables import MUSICBRAINZ_TABLES
from listenbrainz.clickhouse.query_worker.release_groups import release_groups
from listenbrainz.clickhouse.query_worker.tests import ActivityTestCase, DumpImportTestCase, TEST_DATA_PATH
from listenbrainz.db import couchdb


EDITION, REISSUE, GROUP, FIRST, SECOND, UNKNOWN, UNTITLED = (str(UUID(int=i)) for i in range(7))
CREDITS = [
    {"artist_credit_name": "First", "artist_mbid": FIRST, "join_phrase": " & "},
    {"artist_credit_name": "Second", "artist_mbid": SECOND, "join_phrase": ""},
]


def create_release_caches(client):
    for table in MUSICBRAINZ_TABLES:
        if table.name in ("release_metadata_cache", "release_group_metadata_cache"):
            client.command(f"CREATE TABLE {table.name} ({table.columns}) ENGINE = MergeTree ORDER BY {table.order_by}")


class ReleaseGroupDumpTestCase(DumpImportTestCase):
    def test_full_and_incremental_imports_match_spark_results(self):
        create_release_caches(self.client)
        for name in ("release_metadata_cache", "release_group_metadata_cache"):
            rows = pq.read_table(TEST_DATA_PATH / f"{name}.parquet")
            self.client.insert_arrow(name, rows)
        self.load_spark_listens()
        with patch.object(type(self.connection), "from_config", return_value=self.connection):
            batch, = (m for m in release_groups(["all_time"]) if m["type"] == "clk_release_groups")
        expected = json.loads((TEST_DATA_PATH / "user_top_release_groups_output.json").read_text())
        self.assertEqual(batch["data"], expected[0]["data"])


class ReleaseGroupsTestCase(ActivityTestCase):
    query_name = "clickhouse.release_groups"

    def test_backfill_groups_editions_and_pins_metadata_for_changes(self):
        # An existing installation already has listens before its first group backfill.
        self.client.command(f"""
            INSERT INTO listens (user_id, listened_at, release_mbid, release_name, artist_name) VALUES
            (1, '2024-01-01', '{EDITION}', 'Submitted', 'Artist'),
            (1, '2024-01-02', '{REISSUE}', NULL, ''),
            (1, '2024-01-04', '{UNTITLED}', 'Ignored submitted title', 'Artist'),
            (2, '2024-02-01', NULL, NULL, 'No release')
        """)
        create_release_caches(self.client)
        self.client.insert("release_metadata_cache",
                           [(EDITION, GROUP), (REISSUE, GROUP), (UNKNOWN, UNKNOWN), (UNTITLED, UNTITLED)],
                           column_names=["release_mbid", "release_group_mbid"])
        self.client.insert("release_group_metadata_cache",
                           [(GROUP, "Title", "First & Second", [FIRST, SECOND], CREDITS, 8201679314, REISSUE)],
                           column_names=["release_group_mbid", "title", "artist_credit_name", "artist_credit_mbids",
                                         "artists", "caa_id", "caa_release_mbid"])
        self.client.insert("release_group_metadata_cache", [(UNTITLED, "")],
                           column_names=["release_group_mbid", "title"])
        self.client.command("DROP VIEW user_release_group_stats_daily_mv")
        ensure_schema(self.client)
        ensure_schema(self.client)
        self.assert_hourly_counts_match_listens()

        self.client.command("TRUNCATE TABLE release_metadata_cache")
        self.client.command("TRUNCATE TABLE release_group_metadata_cache")
        self.client.command(f"""
            INSERT INTO listens (user_id, listened_at, release_mbid) VALUES (1, '2024-01-03', '{EDITION}')
        """)
        mapped = {"release_group_name": "Title", "release_group_mbid": GROUP, "artist_name": "First & Second",
                  "artist_mbids": [FIRST, SECOND], "artists": CREDITS, "caa_id": 8201679314,
                  "caa_release_mbid": REISSUE, "listen_count": 3}
        batches = [m for m in self.refresh(["month", "all_time"]) if m["type"] == "clk_release_groups"]
        self.assertEqual([batch["stats_range"] for batch in batches], ["month", "all_time"])
        for batch in batches:
            self.assertEqual(batch["data"][0]["data"], [mapped])
            self.assertEqual(batch["data"][0]["count"], 1)
            self.assertEqual(batch["to_ts"], 1706745600 if batch["stats_range"] == "month" else 1706832000)
            self.assertIsNone(couchdb.fetch_exact_data(batch["database"], "2"))

        self.client.command("CREATE TABLE replacement AS listens")
        self.client.command(f"""
            INSERT INTO replacement SELECT * REPLACE (created + INTERVAL 1 DAY AS created,
                toUUID('{UNKNOWN}') AS release_mbid, 'Fallback' AS release_name)
            FROM listens WHERE release_mbid = '{REISSUE}'
        """)
        merge_staged_listens(self.client, "replacement")
        merge_staged_listens(self.client, "replacement")
        delete_matching_listens(self.client, "listens", f"release_mbid = '{EDITION}'", LIVE_STREAM)
        database = self.refresh(["all_time"])[-1]["database"]
        doc = couchdb.fetch_exact_data(database, "1")
        self.assertEqual(doc["count"], 1)
        self.assertEqual(doc["data"], [{"release_group_name": "Fallback", "release_group_mbid": None,
                                        "artist_name": "", "artist_mbids": [], "artists": None, "caa_id": None,
                                        "caa_release_mbid": None, "listen_count": 1}])

    def test_unmapped_identity_and_empty_titles(self):
        self.client.command(f"""
            INSERT INTO listens (user_id, listened_at, release_name, artist_name, artist_credit_mbids) VALUES
            (1, '2024-01-15', 'Album', 'Band', ['{FIRST}', '{SECOND}']),
            (1, '2024-01-31', 'ALBUM', 'BAND', ['{FIRST}', '{SECOND}']),
            (1, '2024-01-31', 'Album', 'Band', ['{SECOND}', '{FIRST}']),
            (1, '2024-01-31', 'Album', 'Other band', []),
            (1, '2024-02-01', 'February', 'Band', []),
            (1, '2024-02-01', NULL, 'Band', []), (1, '2024-02-02', '', 'Band', []),
            (2, '2024-03-01', NULL, 'Missing', [])
        """)
        delete_matching_listens(self.client, "listens", "user_id = 2", LIVE_STREAM)
        january, february = [m for m in self.refresh(["month", "this_month"]) if m["type"] == "clk_release_groups"]
        self.assertEqual(january["to_ts"], february["from_ts"])
        doc = couchdb.fetch_exact_data(january["database"], "1")
        self.assertEqual(doc["count"], 3)
        self.assertEqual([(row["release_group_name"], row["artist_name"], row["artist_mbids"], row["listen_count"])
                          for row in doc["data"]], [
            ("ALBUM", "BAND", [FIRST, SECOND], 2), ("Album", "Other band", [], 1),
            ("Album", "Band", [SECOND, FIRST], 1),
        ])
        self.assertEqual(february["data"][0]["count"], 1)
        self.assertEqual(february["data"][0]["data"][0]["release_group_name"], "February")

    def test_ranking_caps_rows_and_counts_all_named_groups(self):
        self.client.command("""
            INSERT INTO listens (user_id, listened_at, release_name)
            SELECT 1, toDateTime('2024-01-01'), toString(number) FROM numbers(1003)
        """)
        database = self.refresh(["all_time"])[-1]["database"]
        doc = couchdb.fetch_exact_data(database, "1")
        self.assertEqual(doc["count"], 1003)
        self.assertEqual([row["release_group_name"] for row in doc["data"]],
                         sorted(map(str, range(1003)), reverse=True)[:1000])
