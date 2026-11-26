import json
from unittest.mock import patch
from uuid import UUID

import pyarrow.parquet as pq

from listenbrainz.clickhouse.query_worker.listens.aggregates import LIVE_STREAM
from listenbrainz.clickhouse.query_worker.listens.deletions import delete_matching_listens
from listenbrainz.clickhouse.query_worker.listens.load_dump import merge_staged_listens
from listenbrainz.clickhouse.query_worker.listens.schema import ensure_schema
from listenbrainz.clickhouse.query_worker.metadata_tables import RECORDING_ARTIST_CACHE, RELEASE_METADATA_CACHE
from listenbrainz.clickhouse.query_worker.recordings import recordings
from listenbrainz.clickhouse.query_worker.tests import ActivityTestCase, DumpImportTestCase, TEST_DATA_PATH
from listenbrainz.clickhouse.query_worker.tests.test_release_groups import create_release_caches
from listenbrainz.db import couchdb


class RecordingDumpTestCase(DumpImportTestCase):
    def test_full_and_incremental_imports_match_spark_results(self):
        self.load_spark_listens()
        for table, fixture in ((RECORDING_ARTIST_CACHE, "recording_artist"),
                               (RELEASE_METADATA_CACHE, "release_metadata_cache")):
            self.client.command(f"CREATE TABLE {table.name} ({table.columns}) "
                                f"ENGINE = MergeTree ORDER BY {table.order_by}")
            self.client.insert_arrow(table.name, pq.read_table(TEST_DATA_PATH / f"{fixture}.parquet"))
        with patch.object(type(self.connection), "from_config", return_value=self.connection):
            batch, = (msg for msg in recordings(["all_time"]) if msg["type"] == "clk_recordings")
        expected = json.loads((TEST_DATA_PATH / "user_top_recordings_output.json").read_text())
        self.assertEqual(batch["data"], expected[0]["data"])


class RecordingsTestCase(ActivityTestCase):
    query_name = "clickhouse.recordings"

    def test_recordings_share_the_release_group_key_and_preserve_editions(self):
        recording, edition, reissue, group = (str(UUID(int=i)) for i in range(4))
        create_release_caches(self.client)
        self.client.insert("release_metadata_cache", [(edition, group), (reissue, group)],
                           column_names=["release_mbid", "release_group_mbid"])
        self.client.insert("release_group_metadata_cache", [(group, "Album")],
                           column_names=["release_group_mbid", "title"])
        self.client.command(f"""
            INSERT INTO listens (user_id, listened_at, recording_mbid, recording_name, artist_name,
                                 release_mbid, release_name) VALUES
            (1, '2024-01-01', '{recording}', 'Song', 'Band', '{edition}', 'Album'),
            (1, '2024-01-01 01:00:00', '{recording}', 'Song', 'Band', '{reissue}', 'Album'),
            (1, '2024-01-01 02:00:00', NULL, 'Unmapped', 'Band', NULL, 'Demo')
        """)
        self.client.command("DROP VIEW user_release_group_stats_daily_mv")
        ensure_schema(self.client)
        self.client.command("OPTIMIZE TABLE user_recording_stats_daily FINAL")

        def check_group_counts():
            query = """SELECT release_group_id, sum(listen_count) AS n FROM {}
                        GROUP BY release_group_id HAVING n > 0 ORDER BY release_group_id"""
            actual = self.client.query(query.format("user_recording_stats_daily")).result_rows
            self.assertEqual(actual, self.client.query(query.format("user_release_group_stats_daily")).result_rows)
            return actual

        groups = check_group_counts()
        self.assertEqual(groups[-1], ((True, UUID(group)), 2))
        self.assertEqual(len(groups), 2)
        doc = couchdb.fetch_exact_data(self.refresh(["all_time"])[-1]["database"], "1")
        self.assertEqual(doc["count"], 3)
        self.assertEqual({row["release_mbid"] for row in doc["data"]}, {edition, reissue, None})
        self.client.command("TRUNCATE TABLE release_metadata_cache")
        delete_matching_listens(self.client, "listens", f"release_mbid = '{edition}'", LIVE_STREAM)
        self.assertEqual(check_group_counts()[-1], ((True, UUID(group)), 1))
        doc = couchdb.fetch_exact_data(self.refresh(["all_time"])[-1]["database"], "1")
        self.assertEqual({row["release_mbid"] for row in doc["data"]}, {reissue, None})

    def test_refresh_pins_cover_art_and_distinguishes_missing_mbids(self):
        release = str(UUID(int=0))
        table = RELEASE_METADATA_CACHE
        self.client.command(f"CREATE TABLE {table.name} ({table.columns}) ENGINE = MergeTree ORDER BY {table.order_by}")
        self.client.insert(table.name, [(release, 8201679314, release)],
                           column_names=["release_mbid", "caa_id", "caa_release_mbid"])
        self.client.command(f"""
            INSERT INTO listens (user_id, listened_at, recording_name, artist_name, release_mbid) VALUES
            (1, '2024-01-15', 'Song', 'Artist', '{release}'), (1, '2024-01-15', 'Song', 'Artist', NULL),
            (2, '2024-02-01', 'Newer', 'Artist', NULL)
        """)
        with patch.object(type(self.connection), "from_config", return_value=self.connection):
            messages = recordings(["month", "all_time"])
            self.assertEqual(next(messages)["type"], "clk_recordings_start")
            self.client.command(f"TRUNCATE TABLE {table.name}")
            for batch in (m for m in messages if m["type"] == "clk_recordings"):
                doc = batch["data"][0]
                self.assertEqual(doc["count"], 2)
                self.assertEqual([(r["release_mbid"], r["caa_id"], r["caa_release_mbid"]) for r in doc["data"]],
                                 [(release, 8201679314, release), (None, None, None)])
        doc = couchdb.fetch_exact_data(self.refresh(["all_time"])[-1]["database"], "1")
        self.assertEqual([r["caa_id"] for r in doc["data"]], [None, None])

    def test_backfill_corrections_deletions_and_case_insensitive_identity(self):
        # Start with listens collected before recording stats were initialized.
        for table in ("user_recording_stats_daily", "recording_metadata"):
            self.client.command(f"DROP VIEW {table}_mv")
            self.client.command(f"DROP TABLE {table}")
        recording, release, other_release, first, second = (str(UUID(int=i)) for i in range(5))
        self.client.command(f"""
            INSERT INTO listens (user_id, listened_at, recording_name, recording_mbid, artist_name,
                                 artist_credit_mbids, release_name, release_mbid) VALUES
            (1, '2024-01-01', 'SONG', '{recording}', 'band', ['{first}', '{second}'], 'album', '{release}'),
            (1, '2024-01-02', 'Song', '{recording}', 'Band', ['{first}', '{second}'], 'Album', '{release}'),
            (1, '2024-01-02 01:00:00', 'Song', '{recording}', 'Band', ['{first}', '{second}'], 'Album', '{other_release}'),
            (1, '2024-01-04', 'Song', '{recording}', 'Band', ['{second}', '{first}'], 'Album', '{release}'),
            (1, '2024-01-05', 'Song', NULL, 'Band', ['{first}', '{second}'], 'Album', '{release}'),
            (2, '2024-02-01', 'No release', NULL, 'Solo', [], NULL, NULL)
        """)
        ensure_schema(self.client)
        ensure_schema(self.client)
        self.client.command("OPTIMIZE TABLE user_recording_stats_daily FINAL")
        columns = self.client.query("SELECT * FROM user_recording_stats_daily LIMIT 0").column_names
        self.assertEqual(tuple(columns), ("user_id", "day", "recording_id", "release_group_id", "listen_count"))
        self.assert_hourly_counts_match_listens()
        january, all_time = (m for m in self.refresh(["month", "all_time"]) if m["type"] == "clk_recordings")
        doc = couchdb.fetch_exact_data(january["database"], "1")
        self.assertEqual(doc["count"], 4)
        self.assertEqual([row["listen_count"] for row in doc["data"]], [2, 1, 1, 1])
        self.assertEqual(doc["data"][0], {
            "track_name": "SONG", "recording_mbid": recording, "artist_name": "band", "artist_mbids": [first, second],
            "release_name": "album", "release_mbid": release, "artists": None,
            "caa_id": None, "caa_release_mbid": None, "listen_count": 2,
        })
        self.assertIsNone(couchdb.fetch_exact_data(january["database"], "2"))
        self.assertIsNone(couchdb.fetch_exact_data(all_time["database"], "2")["data"][0]["release_name"])

        self.client.command("CREATE TABLE correction AS listens")
        self.client.command("""
            INSERT INTO correction SELECT * REPLACE (created + INTERVAL 1 DAY AS created, 'Fixed' AS recording_name)
              FROM listens WHERE recording_name = 'SONG'
        """)
        merge_staged_listens(self.client, "correction")
        merge_staged_listens(self.client, "correction")
        delete_matching_listens(self.client, "listens", "recording_name = 'Fixed'", LIVE_STREAM)
        database = self.refresh(["all_time"])[-1]["database"]
        doc = couchdb.fetch_exact_data(database, "1")
        self.assertEqual(doc["count"], 4)
        self.assertEqual([(row["track_name"], row["listen_count"]) for row in doc["data"]], [("Song", 1)] * 4)

    def test_ties_across_cutoff_and_invalid_artist_credit(self):
        self.client.command("""
            INSERT INTO listens (user_id, listened_at, recording_name, artist_name)
            SELECT 1, toDateTime('2024-01-01'), toString(number), 'Artist' FROM numbers(1003)
        """)
        self.client.command("""
            INSERT INTO listens (user_id, listened_at, recording_name) VALUES (2, '2024-01-01', 'Unknown')
        """)
        database = self.refresh(["all_time"])[-1]["database"]
        doc = couchdb.fetch_exact_data(database, "1")
        self.assertEqual(doc["count"], 1003)
        self.assertEqual([row["track_name"] for row in doc["data"]], sorted(map(str, range(1003)), reverse=True)[:1000])
        empty = couchdb.fetch_exact_data(database, "2")
        self.assertEqual((empty["count"], empty["data"]), (0, []))
