from dataclasses import replace
from pathlib import Path
from unittest.mock import patch
from uuid import UUID, uuid4

from sqlalchemy import create_engine
from sqlalchemy.exc import DataError

from listenbrainz import db
from listenbrainz.clickhouse.query_worker import metadata_cache
from listenbrainz.clickhouse.query_worker.listens.schema import ensure_schema
from listenbrainz.clickhouse.query_worker.query_map import functions
from listenbrainz.clickhouse.query_worker.tests import ClickHouseTestCase


class MetadataCacheTestCase(ClickHouseTestCase):
    def setUp(self):
        super().setUp()
        urls = db.create_test_database_connect_strings()
        self.feedback = create_engine(urls["DB_CONNECT"])
        self.addCleanup(self.feedback.dispose)
        with self.feedback.begin() as conn:
            conn.exec_driver_sql("CREATE TEMP TABLE recording_feedback (user_id int, recording_mbid uuid, score int)")
            conn.exec_driver_sql("INSERT INTO recording_feedback VALUES (81, NULL, -1)")

    def musicbrainz_fixture(self):
        url = db.create_test_database_connect_strings()["DB_CONNECT_ADMIN"]
        admin = create_engine(url, isolation_level="AUTOCOMMIT")
        self.addCleanup(admin.dispose)
        database = "test_metadata_" + uuid4().hex
        with admin.connect() as conn:
            conn.exec_driver_sql(f"CREATE DATABASE {database}")

        def drop_database():
            with admin.connect() as conn:
                conn.exec_driver_sql(f"DROP DATABASE {database}")

        self.addCleanup(drop_database)
        engine = create_engine(admin.url.set(database=database))
        self.addCleanup(engine.dispose)
        with engine.begin() as conn:
            conn.exec_driver_sql(Path(__file__).with_name("metadata_cache.sql").read_text())
        return engine

    def refresh(self, musicbrainz=None):
        with patch.object(type(self.connection), "from_config", return_value=self.connection), \
                patch("brainzutils.musicbrainz_db.engine", musicbrainz), patch.object(db, "engine", self.feedback):
            functions["clickhouse.update_metadata_cache"]()

    def rows(self, query):
        return self.client.query(query).result_rows

    def test_refresh_spark_caches_and_artist_lookup(self):
        self.refresh(self.musicbrainz_fixture())
        first, second, third, recording, redirect = (UUID(int=i) for i in range(1, 6))
        self.assertEqual(self.rows("SELECT * FROM artist_metadata_cache ORDER BY artist_id"),
                         [(1, first, "First"), (2, second, "Second"), (3, third, "")])
        self.assertEqual(self.rows("SELECT * FROM artist_country_cache ORDER BY artist_mbid"),
                         [(first, "First", "GRC"), (second, "Second", None)])
        self.assertEqual(self.rows("SELECT * FROM artist_credit_cache ORDER BY position"),
                         [(1, first, 0, " & "), (1, second, 1, "")])
        self.assertEqual(self.rows("SELECT * FROM recording_length_cache ORDER BY is_redirect"),
                         [(recording, None, 4, False), (redirect, None, 4, True)])
        artists = [
            {"artist_credit_name": "First!", "join_phrase": " & ", "artist_mbid": first},
            {"artist_credit_name": "Second", "join_phrase": "", "artist_mbid": second},
        ]
        self.assertEqual(self.rows("SELECT artist_mbids, artists FROM recording_artist_cache"),
                         [([first, second], artists)])
        self.assertEqual(self.rows("SELECT * FROM release_metadata_cache"),
                         [(UUID(int=7), UUID(int=6), None, "Release", "Both", None, None, [first, second], artists)])
        self.assertEqual(self.rows("SELECT * FROM release_group_metadata_cache"),
                         [(UUID(int=6), "Group", "Both", None, None, [first, second], artists, None, None)])
        for entity, jazz_count in [("recording", 3), ("artist", 4), ("release_group", 5)]:
            with self.subTest(entity=entity):
                expected = [(recording, "jazz", jazz_count)]
                self.assertEqual(self.rows(f"SELECT * FROM {entity}_genre_cache"), expected)
                if entity == "recording":
                    expected.append((recording, "live", 1))
                self.assertEqual(self.rows(f"SELECT * FROM {entity}_tag_cache ORDER BY tag"), expected)
        self.assertEqual(self.rows("SELECT * FROM recording_feedback_cache"), [(81, None, -1)])

        with self.feedback.begin() as conn:
            conn.exec_driver_sql("TRUNCATE recording_feedback")
        self.refresh()  # Unconfigured MusicBrainz leaves its published caches available.
        self.assertEqual(self.rows("SELECT artist_name FROM artist_metadata_cache WHERE artist_id = 1"), [("First",)])
        self.assertEqual(self.rows("SELECT * FROM recording_feedback_cache"), [])

    def test_artist_backfill_uses_published_musicbrainz_ids_and_names(self):
        self.client.command("""
            INSERT INTO listens (user_id, listened_at, artist_name, artist_credit_mbids) VALUES
            (1, '2024-01-01', 'submitted', ['00000000-0000-0000-0000-000000000001',
                                            '00000000-0000-0000-0000-000000000003'])
        """)
        self.refresh(self.musicbrainz_fixture())
        self.client.command("DROP VIEW user_artist_stats_daily_mv")
        ensure_schema(self.client)
        self.assertEqual(self.rows("""
            SELECT artist_id, display_name, sum(listen_count) FROM user_artist_stats_daily
              JOIN artist_metadata USING (artist_id)
             GROUP BY artist_id, display_name ORDER BY artist_id
        """), [(1, "First", 1), (3, "", 1)])

    def test_failed_refresh_preserves_previous_cache_and_can_retry(self):
        self.refresh()
        with self.feedback.begin() as conn:
            conn.exec_driver_sql("ALTER TABLE recording_feedback RENAME TO previous_feedback")
            conn.exec_driver_sql("""
                CREATE TEMP VIEW recording_feedback AS
                SELECT i AS user_id, NULL::uuid AS recording_mbid, 1 / (2 - i) AS score
                  FROM generate_series(1, 2) i
            """)
        with patch("listenbrainz.clickhouse.query_worker.metadata_cache.BATCH_SIZE", 1), self.assertRaises(DataError):
            self.refresh()
        self.assertEqual(self.rows("SELECT * FROM recording_feedback_cache"), [(81, None, -1)])

        with self.feedback.begin() as conn:
            conn.exec_driver_sql("DROP VIEW recording_feedback")
            conn.exec_driver_sql("ALTER TABLE previous_feedback RENAME TO recording_feedback")
            conn.exec_driver_sql("UPDATE recording_feedback SET score = 1")
        self.refresh()
        self.assertEqual(self.rows("SELECT * FROM recording_feedback_cache"), [(81, None, 1)])

    def test_slow_source_with_idle_transaction_timeout(self):
        artist = metadata_cache.MUSICBRAINZ_TABLES[0]
        slow = replace(artist, query=artist.query + " CROSS JOIN pg_sleep(0.7)")
        with self.feedback.begin() as conn:
            conn.exec_driver_sql("SET idle_in_transaction_session_timeout = '200ms'")
        with patch.object(metadata_cache, "MUSICBRAINZ_TABLES", (slow,)):
            self.refresh(self.musicbrainz_fixture())
        self.assertEqual(self.client.command("SELECT count() FROM artist_metadata_cache"), 3)
        self.assertEqual(self.rows("SELECT * FROM recording_feedback_cache"), [(81, None, -1)])

    def test_batches_share_one_insert_context(self):
        with self.feedback.begin() as conn:
            conn.exec_driver_sql("INSERT INTO recording_feedback VALUES (82, NULL, 1), (83, NULL, -1)")
        client_class = type(self.client)
        with patch.object(metadata_cache, "BATCH_SIZE", 1), \
                patch.object(client_class, "create_insert_context", autospec=True,
                             side_effect=client_class.create_insert_context) as describe:
            self.refresh()
        describe.assert_called_once()
        self.assertEqual(self.rows("SELECT * FROM recording_feedback_cache ORDER BY user_id"),
                         [(81, None, -1), (82, None, 1), (83, None, -1)])

    def test_replace_cache_larger_than_partition_drop_limit(self):
        self.refresh()
        with self.feedback.begin() as conn:
            conn.exec_driver_sql("UPDATE recording_feedback SET score = 1")
        limits = {"max_partition_size_to_drop": 1, "max_table_size_to_drop": 1}
        with self.connection.connect(session_id=uuid4().hex, settings=limits) as client:
            metadata_cache._refresh_table(client, self.feedback, metadata_cache.RECORDING_FEEDBACK)
        self.assertEqual(self.rows("SELECT feedback FROM recording_feedback_cache"), [(1,)])

    def test_overlapping_refreshes_publish_their_own_snapshot(self):
        client_class = type(self.client)
        command = client_class.command
        nested_refresh_started = False

        def interleave(client, sql, *args, **kwargs):
            nonlocal nested_refresh_started
            if sql.startswith("ALTER TABLE recording_feedback_cache") and not nested_refresh_started:
                nested_refresh_started = True
                with self.feedback.begin() as conn:
                    conn.exec_driver_sql("UPDATE recording_feedback SET score = 1")
                self.refresh()
                self.assertEqual(self.rows("SELECT feedback FROM recording_feedback_cache"), [(1,)])
            return command(client, sql, *args, **kwargs)

        with patch.object(client_class, "command", interleave):
            self.refresh()
        self.assertTrue(nested_refresh_started)
        self.assertEqual(self.rows("SELECT feedback FROM recording_feedback_cache"), [(-1,)])
