import logging
import random
from datetime import datetime, timedelta, timezone
from time import time
from unittest.mock import patch

import sqlalchemy
from brainzutils import cache
from sqlalchemy import text

import listenbrainz.db.user as db_user
from listenbrainz.db import listens as listens_db, timescale as ts, timescale
from listenbrainz.db.testing import DatabaseTestCase, TimescaleTestCase
from listenbrainz.listen import Listen
from listenbrainz.listenstore.tests.util import create_test_data_for_timescalelistenstore
from listenbrainz.listenstore.timescale_listenstore import REDIS_USER_LISTEN_COUNT, \
    TimescaleListenStore, REDIS_TOTAL_LISTEN_COUNT, EPOCH
from listenbrainz.listenstore.timescale_utils import add_missing_to_listen_users_metadata, delete_listens
from listenbrainz.webserver import create_app


class TestTimescaleListenStore(DatabaseTestCase, TimescaleTestCase):

    def setUp(self):
        DatabaseTestCase.setUp(self)
        TimescaleTestCase.setUp(self)
        self.app = create_app()
        self.log = logging.getLogger(__name__)
        self.logstore = TimescaleListenStore(self.log)

        self.ctx = self.app.app_context()
        self.ctx.push()

        self.testuser = db_user.get_or_create(self.db_conn, 1, "test")
        self.testuser_id = self.testuser["id"]
        self.testuser_name = self.testuser["musicbrainz_id"]

    def tearDown(self):
        self.ctx.pop()
        self.logstore = None
        DatabaseTestCase.tearDown(self)
        TimescaleTestCase.tearDown(self)
        cache._r.flushdb()

    def _create_test_data(self, user_name, user_id, test_data_file_name=None):
        """ Insert test listens, without a recalculation: counts and timestamps must be maintained at ingest """
        test_data = create_test_data_for_timescalelistenstore(user_name, user_id, test_data_file_name)
        self.logstore.insert(test_data)
        return len(test_data)

    def _insert_mapping_metadata(self, msid):
        """ Insert mapping test data into the mapping tables """

        query = """
            INSERT INTO mapping.mb_metadata_cache
               (recording_mbid, recording_id, artist_mbids, artist_ids, release_mbid, release_id, recording_data, artist_data, tag_data, release_data, dirty)
                VALUES ('2f3d422f-8890-41a1-9762-fbe16f107c31'
                      , 1
                      , '{8f6bd1e4-fbe1-4f50-aa9b-94c450ec0f11}'::UUID[]
                      , '{1}'::INTEGER[]
                      , '76df3287-6cda-33eb-8e9a-044b5e15ffdd'
                      , 1
                      , '{"name": "Strangers", "rels": [], "length": 291160}'
                      , '{"name": "Portishead", "artist_credit_id": 204, "artists": [{"area": "United Kingdom", "rels": {"lyrics": "https://muzikum.eu/en/122-6105/portishead/lyrics.html", "youtube": "https://www.youtube.com/user/portishead1002", "wikidata": "https://www.wikidata.org/wiki/Q191352", "streaming": "https://tidal.com/artist/27441", "free streaming": "https://www.deezer.com/artist/1069", "social network": "https://www.facebook.com/portishead", "official homepage": "http://www.portishead.co.uk/", "purchase for download": "https://www.junodownload.com/artists/Portishead/releases/"}, "type": "Group", "begin_year": 1991}]}'
                      , '{"artist": [], "recording": [], "release_group": []}'
                      , '{"mbid": "76df3287-6cda-33eb-8e9a-044b5e15ffdd", "name": "Dummy"}'
                      , 'f'
                       ),
                       ('2cfad207-3f55-4aec-8120-86cf66e34d59'
                      , 2
                      , '{678d88b2-87b0-403b-b63d-5da7465aecc3}'::UUID[]
                      , '{2}'::INTEGER[]
                      , '93ac1812-d38d-4125-88e8-8440e3e89072'
                      , 2
                      , '{"name": "Immigrant Song", "rels": [], "length": 145426}'
                      , '{"name": "Led Zeppelin", "artists": [{"area": "United Kingdom", "name": "Led Zeppelin", "rels": {"lyrics": "https://genius.com/artists/Led-zeppelin", "youtube": "https://www.youtube.com/@ledzeppelin", "wikidata": "https://www.wikidata.org/wiki/Q2331", "streaming": "https://tidal.com/artist/67522", "free streaming": "https://www.deezer.com/artist/848", "social network": "https://www.facebook.com/ledzeppelin", "official homepage": "http://www.ledzeppelin.com/", "purchase for download": "https://www.7digital.com/artist/led-zeppelin"}, "type": "Group", "end_year": 1980, "begin_year": 1968, "join_phrase": ""}], "artist_credit_id": 388}'
                      , '{"artist": [], "recording": [], "release_group": []}'
                      , '{"mbid": "93ac1812-d38d-4125-88e8-8440e3e89072", "name": "Led Zeppelin III", "year": 1987, "caa_id": 1287533205, "caa_release_mbid": "7aadcfa2-df82-480e-8d2d-7ec4d0b41172", "album_artist_name": "Led Zeppelin", "release_group_mbid": "53f80f76-f8af-3558-bfd5-e7221e055c75"}'
                      , 'f' )
        """

        join_query = """INSERT INTO mbid_mapping
                               (recording_msid, recording_mbid, match_type)
                        VALUES ('%s', '%s', 'exact_match')""" % (msid, '2f3d422f-8890-41a1-9762-fbe16f107c31')

        with ts.engine.begin() as connection:
            connection.execute(sqlalchemy.text(query))
            connection.execute(sqlalchemy.text(join_query))

    def test_insert_timescale(self):
        count = self._create_test_data(self.testuser_name, self.testuser_id)
        from_ts = datetime.fromtimestamp(1399999999, timezone.utc)
        listens = self.logstore.fetch_listens(user=self.testuser, from_ts=from_ts)
        self.assertEqual(len(listens), count)

    def test_fetch_listens_0(self):
        self._create_test_data(self.testuser_name, self.testuser_id)
        from_ts = datetime.fromtimestamp(1400000000, timezone.utc)
        listens = self.logstore.fetch_listens(user=self.testuser, from_ts=from_ts, limit=1)
        self.assertEqual(len(listens), 1)
        self.assertEqual(listens[0].ts_since_epoch, 1400000050)

    def test_fetch_listens_1(self):
        self._create_test_data(self.testuser_name, self.testuser_id)
        from_ts = datetime.fromtimestamp(1400000000, timezone.utc)
        listens = self.logstore.fetch_listens(user=self.testuser, from_ts=from_ts)
        self.assertEqual(len(listens), 4)
        self.assertEqual(listens[0].ts_since_epoch, 1400000200)
        self.assertEqual(listens[1].ts_since_epoch, 1400000150)
        self.assertEqual(listens[2].ts_since_epoch, 1400000100)
        self.assertEqual(listens[3].ts_since_epoch, 1400000050)

    def test_fetch_listens_2(self):
        self._create_test_data(self.testuser_name, self.testuser_id)
        from_ts = datetime.fromtimestamp(1400000100, timezone.utc)
        listens = self.logstore.fetch_listens(user=self.testuser, from_ts=from_ts)
        self.assertEqual(len(listens), 2)
        self.assertEqual(listens[0].ts_since_epoch, 1400000200)
        self.assertEqual(listens[1].ts_since_epoch, 1400000150)

    def test_fetch_listens_3(self):
        self._create_test_data(self.testuser_name, self.testuser_id)
        to_ts = datetime.fromtimestamp(1400000300, timezone.utc)
        listens = self.logstore.fetch_listens(user=self.testuser, to_ts=to_ts)
        self.assertEqual(len(listens), 5)
        self.assertEqual(listens[0].ts_since_epoch, 1400000200)
        self.assertEqual(listens[1].ts_since_epoch, 1400000150)
        self.assertEqual(listens[2].ts_since_epoch, 1400000100)
        self.assertEqual(listens[3].ts_since_epoch, 1400000050)
        self.assertEqual(listens[4].ts_since_epoch, 1400000000)

    def test_fetch_listens_4(self):
        self._create_test_data(self.testuser_name, self.testuser_id)
        from_ts = datetime.fromtimestamp(1400000049, timezone.utc)
        to_ts = datetime.fromtimestamp(1400000101, timezone.utc)
        listens = self.logstore.fetch_listens(user=self.testuser, from_ts=from_ts, to_ts=to_ts)
        self.assertEqual(len(listens), 2)
        self.assertEqual(listens[0].ts_since_epoch, 1400000100)
        self.assertEqual(listens[1].ts_since_epoch, 1400000050)

    def test_fetch_listens_5(self):
        self._create_test_data(self.testuser_name, self.testuser_id)
        from_ts = datetime.fromtimestamp(1400000101, timezone.utc)
        with self.assertRaises(ValueError):
            self.logstore.fetch_listens(user=self.testuser, from_ts=from_ts, to_ts=from_ts)

    def test_fetch_listens_with_gaps(self):
        self._create_test_data(self.testuser_name, self.testuser_id,
                               test_data_file_name='timescale_listenstore_test_listens_over_greater_time_range.json')

        # test from_ts with gaps
        from_ts = datetime.fromtimestamp(1399999999, timezone.utc)
        listens = self.logstore.fetch_listens(user=self.testuser, from_ts=from_ts)
        self.assertEqual(len(listens), 4)
        self.assertEqual(listens[0].ts_since_epoch, 1420000050)
        self.assertEqual(listens[1].ts_since_epoch, 1420000000)
        self.assertEqual(listens[2].ts_since_epoch, 1400000050)
        self.assertEqual(listens[3].ts_since_epoch, 1400000000)

        # test from_ts and to_ts with gaps
        from_ts = datetime.fromtimestamp(1400000049, timezone.utc)
        to_ts = datetime.fromtimestamp(1420000001, timezone.utc)
        listens = self.logstore.fetch_listens(user=self.testuser, from_ts=from_ts, to_ts=to_ts)
        self.assertEqual(len(listens), 2)
        self.assertEqual(listens[0].ts_since_epoch, 1420000000)
        self.assertEqual(listens[1].ts_since_epoch, 1400000050)

        # test to_ts with gaps
        to_ts = datetime.fromtimestamp(1420000051, timezone.utc)
        listens = self.logstore.fetch_listens(user=self.testuser, to_ts=to_ts)
        self.assertEqual(len(listens), 4)
        self.assertEqual(listens[0].ts_since_epoch, 1420000050)
        self.assertEqual(listens[1].ts_since_epoch, 1420000000)
        self.assertEqual(listens[2].ts_since_epoch, 1400000050)
        self.assertEqual(listens[3].ts_since_epoch, 1400000000)

    def test_fetch_listens_with_mapping(self):
        """ Test that the recording mbid submitted by the user is preferred over the mapping created by LB """
        self._create_test_data(self.testuser_name, self.testuser_id)
        self._insert_mapping_metadata("c7a41965-9f1e-456c-8b1d-27c0f0dde280")
        from_ts = datetime.fromtimestamp(1400000000, timezone.utc)
        listens = self.logstore.fetch_listens(user=self.testuser, from_ts=from_ts, limit=1)
        self.assertEqual(len(listens), 1)
        self.assertEqual(listens[0].data["mbid_mapping"]["artist_mbids"], ['678d88b2-87b0-403b-b63d-5da7465aecc3'])
        self.assertEqual(listens[0].data["mbid_mapping"]["release_mbid"], '93ac1812-d38d-4125-88e8-8440e3e89072')
        self.assertEqual(listens[0].data["mbid_mapping"]["release_group_mbid"], '53f80f76-f8af-3558-bfd5-e7221e055c75')
        self.assertEqual(listens[0].data["mbid_mapping"]["recording_mbid"], '2cfad207-3f55-4aec-8120-86cf66e34d59')

    def test_fetch_listens_reads_listens_db(self):
        """ Test that listens are served from the listens DB and not from timescale """
        self._create_test_data(self.testuser_name, self.testuser_id)
        with ts.engine.begin() as connection:
            connection.execute(text("""
                INSERT INTO listen (listened_at, created, user_id, recording_msid, data)
                     VALUES (:listened_at, NOW(), :user_id, :recording_msid, '{}'::jsonb)
            """), {
                "listened_at": datetime.fromtimestamp(1400000300, timezone.utc),
                "user_id": self.testuser_id,
                "recording_msid": "84b7d3b2-6ca2-4bd6-b7e1-b1d8a6a0a4fd",
            })

        listens = self.logstore.fetch_listens(user=self.testuser)
        self.assertEqual(len(listens), 5)
        self.assertEqual(listens[0].ts_since_epoch, 1400000200)
        self.assertEqual(
            self.logstore.get_timestamps_for_user(self.testuser_id)[1],
            datetime.fromtimestamp(1400000200, timezone.utc)
        )

        recent = self.logstore.fetch_all_recent_listens_for_users(
            [self.testuser],
            min_ts=datetime.fromtimestamp(1399999999, timezone.utc),
            max_ts=datetime.fromtimestamp(1400000400, timezone.utc),
        )
        self.assertEqual(len(recent), 5)
        self.assertEqual(recent[0].ts_since_epoch, 1400000200)

    def test_fetch_recent_listens_with_mapping(self):
        self._create_test_data(self.testuser_name, self.testuser_id)
        self._insert_mapping_metadata("c7a41965-9f1e-456c-8b1d-27c0f0dde280")
        # same msid as the 1400000050 listen but without a submitted mbid, so the mbid mapping applies
        self.logstore.insert([Listen.from_json({
            "user_id": self.testuser_id,
            "user_name": self.testuser_name,
            "listened_at": 1400000300,
            "recording_msid": "c7a41965-9f1e-456c-8b1d-27c0f0dde280",
            "track_metadata": {"track_name": "Strangers", "artist_name": "Portishead", "additional_info": {}},
        })])

        recent = self.logstore.fetch_recent_listens_for_users([self.testuser], per_user_limit=10, limit=10)
        self.assertEqual(len(recent), 6)
        mapped = {listen.ts_since_epoch: listen.data.get("mbid_mapping") for listen in recent}

        self.assertEqual(mapped[1400000300]["recording_mbid"], "2f3d422f-8890-41a1-9762-fbe16f107c31")
        self.assertEqual(mapped[1400000300]["recording_name"], "Strangers")
        self.assertEqual(mapped[1400000300]["artist_mbids"], ["8f6bd1e4-fbe1-4f50-aa9b-94c450ec0f11"])

        # the submitted mbid is preferred over the mapping for the same msid
        self.assertEqual(mapped[1400000050]["recording_mbid"], "2cfad207-3f55-4aec-8120-86cf66e34d59")
        self.assertEqual(mapped[1400000050]["artist_mbids"], ["678d88b2-87b0-403b-b63d-5da7465aecc3"])
        self.assertEqual(mapped[1400000050]["artists"][0]["artist_credit_name"], "Led Zeppelin")
        self.assertEqual(mapped[1400000050]["caa_id"], 1287533205)

        # submitted mbid without cached metadata
        self.assertEqual(mapped[1400000200], {"recording_mbid": "afd5316a-e9f4-42c0-8933-8892678f4e07"})

    def test_get_listen_count_for_user(self):
        uid = random.randint(2000, 1 << 31)
        testuser = db_user.get_or_create(self.db_conn, uid, "user_%d" % uid)
        testuser_name = testuser['musicbrainz_id']

        count = self._create_test_data(testuser_name, testuser["id"])
        listen_count = self.logstore.get_listen_count_for_user(testuser["id"])
        self.assertEqual(count, listen_count)

    def test_fetch_recent_listens(self):
        user = db_user.get_or_create(self.db_conn, 2, 'someuser')
        user_name = user['musicbrainz_id']
        self._create_test_data(user_name, user["id"])

        user2 = db_user.get_or_create(self.db_conn, 3, 'otheruser')
        user_name2 = user2['musicbrainz_id']
        self._create_test_data(user_name2, user2["id"])

        min_ts = datetime(1960, 1, 1)
        recent = self.logstore.fetch_recent_listens_for_users([user, user2], per_user_limit=1, min_ts=min_ts)
        self.assertEqual(len(recent), 2)

        recent = self.logstore.fetch_recent_listens_for_users([user, user2], min_ts=min_ts)
        self.assertEqual(len(recent), 4)

        recent = self.logstore.fetch_recent_listens_for_users([user], min_ts=recent[0].timestamp - timedelta(seconds=1))
        self.assertEqual(len(recent), 1)
        self.assertEqual(recent[0].ts_since_epoch, 1400000200)

    def test_listen_counts_in_cache(self):
        uid = random.randint(2000, 1 << 31)
        testuser = db_user.get_or_create(self.db_conn, uid, "user_%d" % uid)
        testuser_name = testuser['musicbrainz_id']
        count = self._create_test_data(testuser_name, testuser["id"])
        user_key = REDIS_USER_LISTEN_COUNT + str(testuser["id"])
        self.assertEqual(count, self.logstore.get_listen_count_for_user(testuser["id"]))
        self.assertEqual(count, cache.get(user_key))

    def test_delete_listens(self):
        self._create_test_data(self.testuser_name, self.testuser_id)
        self.assertEqual(self._get_listen_count(self.testuser_id), 5)
        with patch.object(timescale.engine, "connect", side_effect=AssertionError("Timescale delete")):
            self.logstore.delete(self.testuser_id)

        with listens_db.engine.connect() as connection:
            self.assertEqual(connection.execute(text("SELECT count(*) FROM listen")).scalar(), 0)
            self.assertEqual(connection.execute(text(
                "SELECT count(*) FROM deleted_user_listen_history WHERE user_id = :user_id"
            ), {"user_id": self.testuser_id}).scalar(), 1)
        self.assertEqual(self._get_listen_count(self.testuser_id), 0)
        with timescale.engine.connect() as connection:
            # Deletion affects only the listens DB; Timescale retains all five listens.
            self.assertEqual(connection.execute(text("SELECT count(*) FROM listen")).scalar(), 5)

        # reads come from the listens DB, so the deleted history is no longer served
        listens = self.logstore.fetch_listens(user=self.testuser)
        self.assertEqual(listens, [])
        self.assertEqual(self.logstore.get_timestamps_for_user(self.testuser_id), (EPOCH, EPOCH))

    def test_delete_single_listen(self):
        self._create_test_data(self.testuser_name, self.testuser_id)
        listened_at = datetime.fromtimestamp(1400000050, timezone.utc)
        recording_msid = "c7a41965-9f1e-456c-8b1d-27c0f0dde280"
        with listens_db.engine.connect() as connection:
            # Ingestion populated both stores before deletion.
            self.assertEqual(connection.execute(text("SELECT count(*) FROM listen")).scalar(), 5)
            created = connection.execute(text(
                "SELECT created FROM listen WHERE user_id = :user_id AND listened_at = :listened_at"
            ), {"user_id": self.testuser_id, "listened_at": listened_at}).scalar()
        with patch.object(timescale.engine, "begin", side_effect=AssertionError("Timescale delete")):
            self.logstore.delete_listen(listened_at, self.testuser_id, recording_msid)
            delete_listens()
            delete_listens()
        with listens_db.engine.connect() as connection:
            self.assertEqual(connection.execute(text("SELECT count(*) FROM listen")).scalar(), 4)
            row = connection.execute(text("SELECT * FROM listen_delete_metadata")).one()
            self.assertEqual(row.status, "complete")
            self.assertEqual(row.listen_created, created)
            self.assertEqual(row.listened_at, listened_at)
            self.assertEqual(row.user_id, self.testuser_id)
            self.assertEqual(str(row.recording_msid), recording_msid)
        # the second delete_listens run finds nothing pending, so the listen is counted once
        self.assertEqual(self._get_listen_count(self.testuser_id), 4)
        with timescale.engine.connect() as connection:
            self.assertEqual(connection.execute(text("SELECT count(*) FROM listen")).scalar(), 5)

        listens = self.logstore.fetch_listens(user=self.testuser)
        self.assertEqual(
            [listen.ts_since_epoch for listen in listens],
            [1400000200, 1400000150, 1400000100, 1400000000]
        )

    def test_delete_missing_listen_is_invalid(self):
        self.logstore.delete_listen(
            datetime.fromtimestamp(1400000050, timezone.utc), self.testuser_id,
            "c7a41965-9f1e-456c-8b1d-27c0f0dde280",
        )
        delete_listens()
        delete_listens()
        with listens_db.engine.connect() as connection:
            row = connection.execute(text("SELECT status, listen_created FROM listen_delete_metadata")).one()
            self.assertEqual(row.status, "invalid")
            self.assertIsNone(row.listen_created)

    def test_deletion_histories_survive_repeated_processing_and_history_delete(self):
        self._create_test_data(self.testuser_name, self.testuser_id)
        for _ in range(2):
            self.logstore.delete_listen(
                datetime.fromtimestamp(1400000050, timezone.utc), self.testuser_id,
                "c7a41965-9f1e-456c-8b1d-27c0f0dde280",
            )
        delete_listens()
        self.logstore.delete(self.testuser_id)
        with listens_db.engine.connect() as connection:
            records = connection.execute(text("SELECT * FROM listen_delete_metadata ORDER BY id")).all()
            history = connection.execute(text("SELECT * FROM deleted_user_listen_history ORDER BY id")).all()
        self.assertEqual(len(records), 2)
        self.assertTrue(all(row.status == "complete" for row in records))
        self.assertEqual(len(history), 1)
        delete_listens()
        with listens_db.engine.connect() as connection:
            self.assertEqual(connection.execute(text("SELECT * FROM listen_delete_metadata ORDER BY id")).all(), records)
            self.assertEqual(connection.execute(text("SELECT * FROM deleted_user_listen_history ORDER BY id")).all(), history)

    def test_delete_failure_rolls_back_listens_and_history(self):
        self._create_test_data(self.testuser_name, self.testuser_id)
        self.logstore.delete_listen(
            datetime.fromtimestamp(1400000050, timezone.utc), self.testuser_id,
            "c7a41965-9f1e-456c-8b1d-27c0f0dde280",
        )

        def fail_commit(connection):
            raise RuntimeError("Commit failed")

        sqlalchemy.event.listen(listens_db.engine, "commit", fail_commit)
        try:
            with self.assertRaisesRegex(RuntimeError, "Commit failed"):
                delete_listens()
        finally:
            sqlalchemy.event.remove(listens_db.engine, "commit", fail_commit)
        with listens_db.engine.connect() as connection:
            self.assertEqual(connection.execute(text("SELECT count(*) FROM listen")).scalar(), 5)
            self.assertEqual(connection.execute(text("SELECT status FROM listen_delete_metadata")).scalar(), "pending")
        delete_listens()
        with listens_db.engine.connect() as connection:
            self.assertEqual(connection.execute(text("SELECT count(*) FROM listen")).scalar(), 4)
            self.assertEqual(connection.execute(text("SELECT status FROM listen_delete_metadata")).scalar(), "complete")

    def _get_listen_count(self, user_id):
        with listens_db.engine.connect() as connection:
            return connection.execute(
                text("SELECT count FROM listen_user_metadata WHERE user_id = :user_id"),
                {"user_id": user_id}
            ).scalar()

    def test_for_empty_timestamps(self):
        """Test newly created user has an empty count stored in the database."""
        uid = random.randint(2000, 1 << 31)
        testuser = db_user.get_or_create(self.db_conn, uid, "user_%d" % uid)
        self.logstore.set_empty_values_for_user(testuser["id"])
        self.logstore.set_empty_values_for_user(testuser["id"])
        self.assertEqual(self._get_listen_count(testuser["id"]), 0)
        self.assertEqual(self.logstore.get_timestamps_for_user(testuser["id"]), (EPOCH, EPOCH))

        # the count of an existing user is left unchanged
        self._create_test_data(testuser["musicbrainz_id"], testuser["id"])
        self.logstore.set_empty_values_for_user(testuser["id"])
        self.assertEqual(self._get_listen_count(testuser["id"]), 5)

    def test_get_total_listen_count(self):
        total_count = self.logstore.get_total_listen_count()
        self.assertEqual(total_count, 0)

        count_user_1 = self._create_test_data(self.testuser["musicbrainz_id"], self.testuser["id"])
        uid = random.randint(2000, 1 << 31)
        testuser2 = db_user.get_or_create(self.db_conn, uid, f"user_{uid}")
        count_user_2 = self._create_test_data(testuser2["musicbrainz_id"], testuser2["id"])

        cache.delete(REDIS_TOTAL_LISTEN_COUNT)
        add_missing_to_listen_users_metadata()

        total_count = self.logstore.get_total_listen_count()
        self.assertEqual(total_count, count_user_1 + count_user_2)

    def test_get_timestamps_for_user(self):
        self._create_test_data(self.testuser["musicbrainz_id"], self.testuser["id"])
        min_ts, max_ts = self.logstore.get_timestamps_for_user(self.testuser["id"])
        self.assertEqual(datetime.fromtimestamp(1400000200, timezone.utc), max_ts)
        self.assertEqual(datetime.fromtimestamp(1400000000, timezone.utc), min_ts)

        # timestamps widen as more listens are inserted
        self._create_test_data(
            self.testuser["musicbrainz_id"],
            self.testuser["id"],
            "timescale_listenstore_test_listens_2.json",
        )
        min_ts, max_ts = self.logstore.get_timestamps_for_user(self.testuser["id"])
        self.assertEqual(datetime.fromtimestamp(1400000500, timezone.utc), max_ts)
        self.assertEqual(datetime.fromtimestamp(1400000000, timezone.utc), min_ts)

    def test_fetch_listens_after_later_insert(self):
        """ Test listens from a later insert are returned """
        self._create_test_data(self.testuser["musicbrainz_id"], self.testuser["id"])

        self._create_test_data(
            self.testuser["musicbrainz_id"],
            self.testuser["id"],
            "timescale_listenstore_test_listens_2.json",
        )
        from_ts = datetime.fromtimestamp(1400000300, timezone.utc)
        listens = self.logstore.fetch_listens(user=self.testuser, from_ts=from_ts, limit=1)
        self.assertEqual(len(listens), 1)
        self.assertEqual(listens[0].ts_since_epoch, 1400000500)
