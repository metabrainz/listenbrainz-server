from listenbrainz.clickhouse.query_worker.listens.aggregates import LIVE_STREAM
from listenbrainz.clickhouse.query_worker.listens.deletions import delete_matching_listens
from listenbrainz.clickhouse.query_worker.tests import ActivityTestCase
from listenbrainz.db import couchdb


MAPPED = "abcdef12-1111-2222-3333-000000000000"
UNKNOWN = "00000000-0000-0000-0000-000000000000"
EMPTY_NAME = "12345678-1111-2222-3333-000000000001"


class ArtistsTestCase(ActivityTestCase):
    query_name = "clickhouse.artists"

    mb_artists = [(17, MAPPED, "Björk"), (23, EMPTY_NAME, "")]

    def test_artist_identity_and_range_boundaries(self):
        self.client.command("""
            INSERT INTO listens (user_id, listened_at, artist_name, artist_credit_mbids) VALUES
            (1, '2024-01-01', 'credit', ['%s','%s']),
            (1, '2024-01-15', 'another credit', ['%s','%s']),
            (1, '2024-01-15', 'BJÖRK', []), (1, '2024-01-15', 'Björk', []),
            (1, '2024-01-15', 'credit', []),
            (1, '2024-01-15', 'fallback', ['%s']), (2, '2024-02-01', '', []),
            (3, '2024-02-01 00:00:00.001', 'later', [])
        """ % (MAPPED, UNKNOWN, MAPPED, MAPPED, EMPTY_NAME))
        messages = self.refresh(["month", "this_month", "all_time"])
        batches = [m for m in messages if m["type"] == "clk_artists"]
        self.assertEqual([batch["stats_range"] for batch in batches], ["month", "this_month", "all_time"])
        for batch in batches:
            db = batch["database"]
            doc = couchdb.fetch_exact_data(db, "1")
            self.assertEqual(doc["count"], 4)
            self.assertEqual(doc["data"], [
                {"artist_name": "Björk", "artist_mbid": MAPPED, "listen_count": 3},
                {"artist_name": "BJÖRK", "artist_mbid": None, "listen_count": 2},
                {"artist_name": "credit", "artist_mbid": UNKNOWN, "listen_count": 1},
                {"artist_name": "credit", "artist_mbid": None, "listen_count": 1},
            ])
            if batch["stats_range"] == "all_time":
                self.assertEqual(couchdb.fetch_exact_data(db, "2")["data"], [])
                self.assertEqual(batch["to_ts"], 1706832000)  # February 2 00:00 UTC
            else:
                self.assertIsNone(couchdb.fetch_exact_data(db, "2"))
                self.assertEqual(batch["to_ts"], 1706745600)  # February 1 00:00 UTC
            self.assertEqual(couchdb.fetch_exact_data(db, "3") is not None, batch["stats_range"] == "all_time")

    def test_adjacent_months_after_latest_day_is_deleted(self):
        self.client.command("""
            INSERT INTO listens (user_id, listened_at, artist_name) VALUES
            (1, '2024-01-31 23:59:59.999', 'January'), (1, '2024-02-01 00:00:00', 'February'),
            (1, '2024-02-02 12:00:00', 'February'), (2, '2024-03-02', 'deleted')
        """)
        delete_matching_listens(self.client, "listens", "user_id = 2", LIVE_STREAM)
        batches = [m for m in self.refresh(["month", "this_month"]) if m["type"] == "clk_artists"]
        january, february = batches
        self.assertEqual(january["to_ts"], february["from_ts"])
        for batch, artist, expected_count in [(january, "January", 1), (february, "February", 2)]:
            self.assertEqual(batch["data"][0]["data"], [
                {"artist_name": artist, "artist_mbid": None, "listen_count": expected_count}
            ])

    def test_invalid_ranked_artist_does_not_pull_in_next_artist(self):
        self.client.command("""
            INSERT INTO listens (user_id, listened_at, artist_name)
            SELECT 1, toDateTime('2024-01-01'), if(number < 3, '', toString(number)) FROM numbers(1004)
        """)
        database = self.refresh(["all_time"])[-1]["database"]
        doc = couchdb.fetch_exact_data(database, "1")
        self.assertEqual(doc["count"], 1001)
        ranked_names = sorted((str(i) for i in range(3, 1004)), reverse=True)
        self.assertEqual([row["artist_name"] for row in doc["data"]], ranked_names[:999])

    def test_mbid_lookup_and_grouping_use_uuid_value(self):
        self.client.command("""
            INSERT INTO listens (user_id, listened_at, artist_name, artist_credit_mbids) VALUES
            (1, '2024-01-01', 'credit', ['%s']), (1, '2024-01-02', 'credit', ['%s'])
        """ % (MAPPED, MAPPED.upper()))
        database = self.refresh(["all_time"])[-1]["database"]
        doc = couchdb.fetch_exact_data(database, "1")
        self.assertEqual(doc["count"], 1)
        self.assertEqual(doc["data"], [{"artist_name": "Björk", "artist_mbid": MAPPED, "listen_count": 2}])

    def test_materialized_ids_and_signed_counts(self):
        self.client.command("""
            INSERT INTO listens (user_id, listened_at, artist_name, artist_credit_mbids) VALUES
            (5, '2024-01-01', 'credit', ['%s', '%s']),
            (5, '2024-01-01 11:00:00', 'CREDIT', []),
            (5, '2024-01-01 12:00:00', 'credit', []),
            (5, '2024-01-01 12:00:00', 'credit', ['%s'])
        """ % (MAPPED, MAPPED, UNKNOWN))
        rows = self.client.query("""
            SELECT artist_id, artist_mbid, sum(listen_count)
              FROM user_artist_stats_daily
              JOIN (SELECT artist_id, min(artist_mbid) AS artist_mbid FROM artist_metadata GROUP BY artist_id) AS labels
             USING (artist_id)
             GROUP BY artist_id, artist_mbid ORDER BY artist_id
        """).result_rows
        self.assertEqual(rows[0], (17, MAPPED, 2))
        self.assertEqual(sorted((mbid, n) for _, mbid, n in rows[1:]),
                         [("", 2), (UNKNOWN, 1)])
        self.assertTrue(all(row[0] >= 2**127 for row in rows[1:]))
        self.assertNotEqual(rows[1][0], rows[2][0])

    def test_unmapped_spelling_is_shared_across_users(self):
        for user_id, name in [(1, 'Björk'), (2, 'BJÖRK')]:
            self.client.command("""
                INSERT INTO listens (user_id, listened_at, artist_name)
                VALUES ({user_id:UInt32}, '2024-02-01', {name:String})
            """, parameters={"user_id": user_id, "name": name})
        self.assertEqual(tuple(self.client.query("SELECT * FROM user_artist_stats_daily LIMIT 0").column_names),
                         ("user_id", "day", "artist_id", "listen_count"))
        database = self.refresh(["all_time"])[-1]["database"]
        for user_id in ("1", "2"):
            self.assertEqual(couchdb.fetch_exact_data(database, user_id)["data"],
                             [{"artist_name": "BJÖRK", "artist_mbid": None, "listen_count": 1}])

    def test_unmapped_greek_final_sigma(self):
        self.client.command("""
            INSERT INTO listens (user_id, listened_at, artist_name) VALUES
            (1, '2024-02-01', 'ΝΙΚΟΣ'), (1, '2024-02-02', 'νικος'), (1, '2024-02-02', 'νικοσ')
        """)
        database = self.refresh(["all_time"])[-1]["database"]
        doc = couchdb.fetch_exact_data(database, "1")
        self.assertEqual(doc["count"], 2)
        self.assertEqual(doc["data"], [
            {"artist_name": "ΝΙΚΟΣ", "artist_mbid": None, "listen_count": 2},
            {"artist_name": "νικοσ", "artist_mbid": None, "listen_count": 1},
        ])

    def test_missing_label_aborts_refresh(self):
        self.client.command("""
            INSERT INTO listens (user_id, listened_at, artist_name) VALUES (1, '2024-02-01', 'Artist')
        """)
        self.client.command("TRUNCATE TABLE artist_metadata")
        with self.assertRaisesRegex(RuntimeError, "Missing artist metadata"):
            self.refresh(["all_time"])
