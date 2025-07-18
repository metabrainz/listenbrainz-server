import logging
import random
from datetime import datetime, timedelta, timezone
from time import time

import sqlalchemy
from brainzutils import cache
from sqlalchemy import text

import listenbrainz.db.user as db_user
from listenbrainz.db import timescale as ts, timescale
from listenbrainz.db.testing import DatabaseTestCase, TimescaleTestCase
from listenbrainz.listenstore.tests.util import create_test_data_for_timescalelistenstore
from listenbrainz.listenstore.timescale_listenstore import REDIS_USER_LISTEN_COUNT, \
    TimescaleListenStore, REDIS_TOTAL_LISTEN_COUNT
from listenbrainz.listenstore.timescale_utils import delete_listens_and_update_user_listen_data,\
    recalculate_all_user_data, add_missing_to_listen_users_metadata, update_user_listen_data
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

    def _create_test_data(self, user_name, user_id, test_data_file_name=None, recalculate=True):
        test_data = create_test_data_for_timescalelistenstore(user_name, user_id, test_data_file_name)
        self.logstore.insert(test_data)
        if recalculate:
            recalculate_all_user_data()
        return len(test_data)

    def _insert_mapping_metadata(self, msid):
        """ Insert mapping test data into the mapping tables """

        query = """
            INSERT INTO mapping.mb_metadata_cache
               (recording_mbid, artist_mbids, release_mbid, recording_data, artist_data, tag_data, release_data, dirty)
                VALUES ('2f3d422f-8890-41a1-9762-fbe16f107c31'
                      , '{8f6bd1e4-fbe1-4f50-aa9b-94c450ec0f11}'::UUID[]
                      , '76df3287-6cda-33eb-8e9a-044b5e15ffdd'
                      , '{"name": "Strangers", "rels": [], "length": 291160}'
                      , '{"name": "Portishead", "artist_credit_id": 204, "artists": [{"area": "United Kingdom", "rels": {"lyrics": "https://muzikum.eu/en/122-6105/portishead/lyrics.html", "youtube": "https://www.youtube.com/user/portishead1002", "wikidata": "https://www.wikidata.org/wiki/Q191352", "streaming": "https://tidal.com/artist/27441", "free streaming": "https://www.deezer.com/artist/1069", "social network": "https://www.facebook.com/portishead", "official homepage": "http://www.portishead.co.uk/", "purchase for download": "https://www.junodownload.com/artists/Portishead/releases/"}, "type": "Group", "begin_year": 1991}]}'
                      , '{"artist": [], "recording": [], "release_group": []}'
                      , '{"mbid": "76df3287-6cda-33eb-8e9a-044b5e15ffdd", "name": "Dummy"}'
                      , 'f'
                       ),
                       ('2cfad207-3f55-4aec-8120-86cf66e34d59'
                      , '{678d88b2-87b0-403b-b63d-5da7465aecc3}'::UUID[]
                      , '93ac1812-d38d-4125-88e8-8440e3e89072'
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
        listens, min_ts, max_ts = self.logstore.fetch_listens(user=self.testuser, from_ts=from_ts)
        self.assertEqual(len(listens), count)

    def test_fetch_listens_0(self):
        self._create_test_data(self.testuser_name, self.testuser_id)
        from_ts = datetime.fromtimestamp(1400000000, timezone.utc)
        listens, min_ts, max_ts = self.logstore.fetch_listens(user=self.testuser, from_ts=from_ts, limit=1)
        self.assertEqual(len(listens), 1)
        self.assertEqual(listens[0].ts_since_epoch, 1400000050)
        self.assertEqual(min_ts, datetime.fromtimestamp(1400000000, timezone.utc))
        self.assertEqual(max_ts, datetime.fromtimestamp(1400000200, timezone.utc))

    def test_fetch_listens_1(self):
        self._create_test_data(self.testuser_name, self.testuser_id)
        from_ts = datetime.fromtimestamp(1400000000, timezone.utc)
        listens, min_ts, max_ts = self.logstore.fetch_listens(user=self.testuser, from_ts=from_ts)
        self.assertEqual(len(listens), 4)
        self.assertEqual(listens[0].ts_since_epoch, 1400000200)
        self.assertEqual(listens[1].ts_since_epoch, 1400000150)
        self.assertEqual(listens[2].ts_since_epoch, 1400000100)
        self.assertEqual(listens[3].ts_since_epoch, 1400000050)

    def test_fetch_listens_2(self):
        self._create_test_data(self.testuser_name, self.testuser_id)
        from_ts = datetime.fromtimestamp(1400000100, timezone.utc)
        listens, min_ts, max_ts = self.logstore.fetch_listens(user=self.testuser, from_ts=from_ts)
        self.assertEqual(len(listens), 2)
        self.assertEqual(listens[0].ts_since_epoch, 1400000200)
        self.assertEqual(listens[1].ts_since_epoch, 1400000150)

    def test_fetch_listens_3(self):
        self._create_test_data(self.testuser_name, self.testuser_id)
        to_ts = datetime.fromtimestamp(1400000300, timezone.utc)
        listens, min_ts, max_ts = self.logstore.fetch_listens(user=self.testuser, to_ts=to_ts)
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
        listens, min_ts, max_ts = self.logstore.fetch_listens(user=self.testuser, from_ts=from_ts, to_ts=to_ts)
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
        listens, min_ts, max_ts = self.logstore.fetch_listens(user=self.testuser, from_ts=from_ts)
        self.assertEqual(len(listens), 4)
        self.assertEqual(listens[0].ts_since_epoch, 1420000050)
        self.assertEqual(listens[1].ts_since_epoch, 1420000000)
        self.assertEqual(listens[2].ts_since_epoch, 1400000050)
        self.assertEqual(listens[3].ts_since_epoch, 1400000000)

        # test from_ts and to_ts with gaps
        from_ts = datetime.fromtimestamp(1400000049, timezone.utc)
        to_ts = datetime.fromtimestamp(1420000001, timezone.utc)
        listens, min_ts, max_ts = self.logstore.fetch_listens(user=self.testuser, from_ts=from_ts, to_ts=to_ts)
        self.assertEqual(len(listens), 2)
        self.assertEqual(listens[0].ts_since_epoch, 1420000000)
        self.assertEqual(listens[1].ts_since_epoch, 1400000050)

        # test to_ts with gaps
        to_ts = datetime.fromtimestamp(1420000051, timezone.utc)
        listens, min_ts, max_ts = self.logstore.fetch_listens(user=self.testuser, to_ts=to_ts)
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
        listens, min_ts, max_ts = self.logstore.fetch_listens(user=self.testuser, from_ts=from_ts, limit=1)
        self.assertEqual(len(listens), 1)
        self.assertEqual(listens[0].data["mbid_mapping"]["artist_mbids"], ['678d88b2-87b0-403b-b63d-5da7465aecc3'])
        self.assertEqual(listens[0].data["mbid_mapping"]["release_mbid"], '93ac1812-d38d-4125-88e8-8440e3e89072')
        self.assertEqual(listens[0].data["mbid_mapping"]["recording_mbid"], '2cfad207-3f55-4aec-8120-86cf66e34d59')

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
        uid = random.randint(2000, 1 << 31)
        testuser = db_user.get_or_create(self.db_conn, uid, "user_%d" % uid)
        testuser_name = testuser['musicbrainz_id']
        self._create_test_data(testuser_name, testuser["id"])

        to_ts = datetime.fromtimestamp(1400000300, timezone.utc)
        listens, min_ts, max_ts = self.logstore.fetch_listens(user=testuser, to_ts=to_ts)
        self.assertEqual(len(listens), 5)
        self.assertEqual(listens[0].ts_since_epoch, 1400000200)
        self.assertEqual(listens[1].ts_since_epoch, 1400000150)
        self.assertEqual(listens[2].ts_since_epoch, 1400000100)
        self.assertEqual(listens[3].ts_since_epoch, 1400000050)
        self.assertEqual(listens[4].ts_since_epoch, 1400000000)

        self.logstore.delete(testuser["id"])

        to_ts = datetime.fromtimestamp(1400000300, timezone.utc)
        listens, min_ts, max_ts = self.logstore.fetch_listens(user=testuser, to_ts=to_ts)
        self.assertEqual(len(listens), 0)

    def test_delete_single_listen(self):
        uid = random.randint(2000, 1 << 31)
        testuser = db_user.get_or_create(self.db_conn, uid, "user_%d" % uid)
        testuser_name = testuser['musicbrainz_id']
        self._create_test_data(testuser_name, testuser["id"])

        to_ts = datetime.fromtimestamp(1400000300, timezone.utc)
        listens, min_ts, max_ts = self.logstore.fetch_listens(user=testuser, to_ts=to_ts)
        self.assertEqual(len(listens), 5)
        self.assertEqual(listens[0].ts_since_epoch, 1400000200)
        self.assertEqual(listens[1].ts_since_epoch, 1400000150)
        self.assertEqual(listens[2].ts_since_epoch, 1400000100)
        self.assertEqual(listens[3].ts_since_epoch, 1400000050)
        self.assertEqual(listens[4].ts_since_epoch, 1400000000)

        self.logstore.delete_listen(datetime.fromtimestamp(1400000050, timezone.utc), testuser["id"], "c7a41965-9f1e-456c-8b1d-27c0f0dde280")

        pending = self._get_pending_deletes()
        self.assertEqual(len(pending), 1)
        self.assertEqual(pending[0]["listened_at"], datetime.fromtimestamp(1400000050, timezone.utc))
        self.assertEqual(pending[0]["user_id"], testuser["id"])
        self.assertEqual(str(pending[0]["recording_msid"]), "c7a41965-9f1e-456c-8b1d-27c0f0dde280")

        delete_listens_and_update_user_listen_data()

        # clear cache entry so that count is fetched from db again
        cache.delete(REDIS_USER_LISTEN_COUNT + str(testuser["id"]))

        to_ts = datetime.fromtimestamp(1400000300, timezone.utc)
        listens, min_ts, max_ts = self.logstore.fetch_listens(user=testuser, to_ts=to_ts)
        self.assertEqual(len(listens), 4)
        self.assertEqual(listens[0].ts_since_epoch, 1400000200)
        self.assertEqual(listens[1].ts_since_epoch, 1400000150)
        self.assertEqual(listens[2].ts_since_epoch, 1400000100)
        self.assertEqual(listens[3].ts_since_epoch, 1400000000)

        self.assertEqual(self.logstore.get_listen_count_for_user(testuser["id"]), 4)
        min_ts, max_ts = self.logstore.get_timestamps_for_user(testuser["id"])
        self.assertEqual(min_ts, datetime.fromtimestamp(1400000000, timezone.utc))
        self.assertEqual(max_ts, datetime.fromtimestamp(1400000200, timezone.utc))

    def _get_pending_deletes(self):
        with timescale.engine.connect() as connection:
            result = connection.execute(text("SELECT * FROM listen_delete_metadata"))
            return [{
                "user_id": row.user_id,
                "recording_msid": row.recording_msid,
                "listened_at": row.listened_at
            } for row in result.fetchall()]

    def _get_count_and_timestamps(self, user_id):
        with timescale.engine.connect() as connection:
            result = connection.execute(
                text("""
                    SELECT count, min_listened_at, max_listened_at
                      FROM listen_user_metadata
                     WHERE user_id = :user_id
                """), {"user_id": user_id})
            return result.fetchone()._asdict()

    def test_for_empty_timestamps(self):
        """Test newly created user has empty timestamps and count stored in the database."""
        uid = random.randint(2000, 1 << 31)
        testuser = db_user.get_or_create(self.db_conn, uid, "user_%d" % uid)
        self.logstore.set_empty_values_for_user(testuser["id"])
        data = self._get_count_and_timestamps(testuser["id"])
        self.assertEqual(data["count"], 0)
        self.assertEqual(data["min_listened_at"], None)
        self.assertEqual(data["max_listened_at"], None)

    def test_get_total_listen_count(self):
        total_count = self.logstore.get_total_listen_count()
        self.assertEqual(total_count, 0)

        count_user_1 = self._create_test_data(self.testuser["musicbrainz_id"], self.testuser["id"])
        uid = random.randint(2000, 1 << 31)
        testuser2 = db_user.get_or_create(self.db_conn, uid, f"user_{uid}")
        count_user_2 = self._create_test_data(testuser2["musicbrainz_id"], testuser2["id"])

        cache.delete(REDIS_TOTAL_LISTEN_COUNT)
        add_missing_to_listen_users_metadata()
        update_user_listen_data()

        total_count = self.logstore.get_total_listen_count()
        self.assertEqual(total_count, count_user_1 + count_user_2)

    def test_get_timestamps_for_user(self):
        self._create_test_data(self.testuser["musicbrainz_id"], self.testuser["id"])
        min_ts, max_ts = self.logstore.get_timestamps_for_user(self.testuser["id"])
        self.assertEqual(datetime.fromtimestamp(1400000200, timezone.utc), max_ts)
        self.assertEqual(datetime.fromtimestamp(1400000000, timezone.utc), min_ts)

        # test timestamps consider listens which were created since last cron run as well
        self._create_test_data(
            self.testuser["musicbrainz_id"],
            self.testuser["id"],
            "timescale_listenstore_test_listens_2.json",
            recalculate=False
        )
        # do not recalculate/update user data
        min_ts, max_ts = self.logstore.get_timestamps_for_user(self.testuser["id"])
        self.assertEqual(datetime.fromtimestamp(1400000500, timezone.utc), max_ts)
        self.assertEqual(datetime.fromtimestamp(1400000000, timezone.utc), min_ts)

    def test_fetch_listens_for_since_cron_run(self):
        """ Test listens created since last cron run to update user metadata are returned """
        self._create_test_data(self.testuser["musicbrainz_id"], self.testuser["id"])

        # insert more data but do not call recalculate now
        self._create_test_data(
            self.testuser["musicbrainz_id"],
            self.testuser["id"],
            "timescale_listenstore_test_listens_2.json",
            recalculate=False
        )
        from_ts = datetime.fromtimestamp(1400000300, timezone.utc)
        listens, min_ts, max_ts = self.logstore.fetch_listens(user=self.testuser, from_ts=from_ts, limit=1)
        self.assertEqual(len(listens), 1)
        self.assertEqual(listens[0].ts_since_epoch, 1400000500)
        self.assertEqual(min_ts, datetime.fromtimestamp(1400000000, timezone.utc))
        self.assertEqual(max_ts, datetime.fromtimestamp(1400000500, timezone.utc))
