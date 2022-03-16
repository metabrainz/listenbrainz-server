import logging
import os
import random
from time import time

import psycopg2
import sqlalchemy
from brainzutils import cache
from sqlalchemy import text

import listenbrainz.db.user as db_user
from listenbrainz.db import timescale as ts, timescale
from listenbrainz.db.testing import DatabaseTestCase, TimescaleTestCase
from listenbrainz.listen import Listen
from listenbrainz.listenstore.tests.util import create_test_data_for_timescalelistenstore
from listenbrainz.listenstore.timescale_listenstore import REDIS_USER_LISTEN_COUNT, REDIS_USER_TIMESTAMPS, \
    TimescaleListenStore, REDIS_TOTAL_LISTEN_COUNT
from listenbrainz.listenstore.timescale_utils import delete_listens_and_update_user_listen_data,\
    recalculate_all_user_data, add_missing_to_listen_users_metadata, update_user_listen_data


class TestTimescaleListenStore(DatabaseTestCase, TimescaleTestCase):

    def setUp(self):
        DatabaseTestCase.setUp(self)
        TimescaleTestCase.setUp(self)
        self.log = logging.getLogger(__name__)
        self.logstore = TimescaleListenStore(self.log)

        self.testuser = db_user.get_or_create(1, "test")
        self.testuser_id = self.testuser["id"]
        self.testuser_name = self.testuser["musicbrainz_id"]

    def tearDown(self):
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

        query = """INSERT INTO mbid_mapping_metadata
                               (recording_mbid, release_mbid, release_name, artist_credit_id, 
                                artist_mbids, artist_credit_name, recording_name)
                        VALUES ('076255b4-1575-11ec-ac84-135bf6a670e3',
                                '1fd178b4-1575-11ec-b98a-d72392cd8c97',
                                'release_name',
                                65,
                                '{6a221fda-2200-11ec-ac7d-dfa16a57158f}'::UUID[],
                                'artist name', 'recording name')"""

        join_query = """INSERT INTO mbid_mapping
                               (recording_msid, recording_mbid, match_type)
                        VALUES ('%s', '%s', 'exact_match')""" % (msid, '076255b4-1575-11ec-ac84-135bf6a670e3')

        with ts.engine.connect() as connection:
            connection.execute(sqlalchemy.text(query))
            connection.execute(sqlalchemy.text(join_query))

    def test_insert_timescale(self):
        count = self._create_test_data(self.testuser_name, self.testuser_id)
        listens, min_ts, max_ts = self.logstore.fetch_listens(user=self.testuser, from_ts=1399999999)
        self.assertEqual(len(listens), count)

    def test_fetch_listens_0(self):
        self._create_test_data(self.testuser_name, self.testuser_id)
        listens, min_ts, max_ts = self.logstore.fetch_listens(user=self.testuser, from_ts=1400000000, limit=1)
        self.assertEqual(len(listens), 1)
        self.assertEqual(listens[0].ts_since_epoch, 1400000050)
        self.assertEqual(min_ts, 1400000000)
        self.assertEqual(max_ts, 1400000200)

    def test_fetch_listens_1(self):
        self._create_test_data(self.testuser_name, self.testuser_id)
        listens, min_ts, max_ts = self.logstore.fetch_listens(user=self.testuser, from_ts=1400000000)
        self.assertEqual(len(listens), 4)
        self.assertEqual(listens[0].ts_since_epoch, 1400000200)
        self.assertEqual(listens[1].ts_since_epoch, 1400000150)
        self.assertEqual(listens[2].ts_since_epoch, 1400000100)
        self.assertEqual(listens[3].ts_since_epoch, 1400000050)

    def test_fetch_listens_2(self):
        self._create_test_data(self.testuser_name, self.testuser_id)
        listens, min_ts, max_ts = self.logstore.fetch_listens(user=self.testuser, from_ts=1400000100)
        self.assertEqual(len(listens), 2)
        self.assertEqual(listens[0].ts_since_epoch, 1400000200)
        self.assertEqual(listens[1].ts_since_epoch, 1400000150)

    def test_fetch_listens_3(self):
        self._create_test_data(self.testuser_name, self.testuser_id)
        listens, min_ts, max_ts = self.logstore.fetch_listens(user=self.testuser, to_ts=1400000300)
        self.assertEqual(len(listens), 5)
        self.assertEqual(listens[0].ts_since_epoch, 1400000200)
        self.assertEqual(listens[1].ts_since_epoch, 1400000150)
        self.assertEqual(listens[2].ts_since_epoch, 1400000100)
        self.assertEqual(listens[3].ts_since_epoch, 1400000050)
        self.assertEqual(listens[4].ts_since_epoch, 1400000000)

    def test_fetch_listens_4(self):
        self._create_test_data(self.testuser_name, self.testuser_id)
        listens, min_ts, max_ts = self.logstore.fetch_listens(user=self.testuser, from_ts=1400000049, to_ts=1400000101)
        self.assertEqual(len(listens), 2)
        self.assertEqual(listens[0].ts_since_epoch, 1400000100)
        self.assertEqual(listens[1].ts_since_epoch, 1400000050)

    def test_fetch_listens_5(self):
        self._create_test_data(self.testuser_name, self.testuser_id)
        with self.assertRaises(ValueError):
            self.logstore.fetch_listens(user=self.testuser, from_ts=1400000101, to_ts=1400000001)

    def test_fetch_listens_with_gaps(self):
        self._create_test_data(self.testuser_name, self.testuser_id,
                               test_data_file_name='timescale_listenstore_test_listens_over_greater_time_range.json')

        # test from_ts with gaps
        listens, min_ts, max_ts = self.logstore.fetch_listens(user=self.testuser, from_ts=1399999999)
        self.assertEqual(len(listens), 4)
        self.assertEqual(listens[0].ts_since_epoch, 1420000050)
        self.assertEqual(listens[1].ts_since_epoch, 1420000000)
        self.assertEqual(listens[2].ts_since_epoch, 1400000050)
        self.assertEqual(listens[3].ts_since_epoch, 1400000000)

        # test from_ts and to_ts with gaps
        listens, min_ts, max_ts = self.logstore.fetch_listens(user=self.testuser, from_ts=1400000049, to_ts=1420000001)
        self.assertEqual(len(listens), 2)
        self.assertEqual(listens[0].ts_since_epoch, 1420000000)
        self.assertEqual(listens[1].ts_since_epoch, 1400000050)

        # test to_ts with gaps
        listens, min_ts, max_ts = self.logstore.fetch_listens(user=self.testuser, to_ts=1420000051)
        self.assertEqual(len(listens), 4)
        self.assertEqual(listens[0].ts_since_epoch, 1420000050)
        self.assertEqual(listens[1].ts_since_epoch, 1420000000)
        self.assertEqual(listens[2].ts_since_epoch, 1400000050)
        self.assertEqual(listens[3].ts_since_epoch, 1400000000)

    def test_fetch_listens_with_mapping(self):
        self._create_test_data(self.testuser_name, self.testuser_id)
        self._insert_mapping_metadata("c7a41965-9f1e-456c-8b1d-27c0f0dde280")
        listens, min_ts, max_ts = self.logstore.fetch_listens(user=self.testuser, from_ts=1400000000, limit=1)
        self.assertEqual(len(listens), 1)
        self.assertEqual(listens[0].data["mbid_mapping"]["artist_mbids"], ['6a221fda-2200-11ec-ac7d-dfa16a57158f'])
        self.assertEqual(listens[0].data["mbid_mapping"]["release_mbid"], '1fd178b4-1575-11ec-b98a-d72392cd8c97')
        self.assertEqual(listens[0].data["mbid_mapping"]["recording_mbid"], '076255b4-1575-11ec-ac84-135bf6a670e3')

    def test_get_listen_count_for_user(self):
        uid = random.randint(2000, 1 << 31)
        testuser = db_user.get_or_create(uid, "user_%d" % uid)
        testuser_name = testuser['musicbrainz_id']

        count = self._create_test_data(testuser_name, testuser["id"])
        listen_count = self.logstore.get_listen_count_for_user(testuser["id"])
        self.assertEqual(count, listen_count)

    def test_fetch_recent_listens(self):
        user = db_user.get_or_create(2, 'someuser')
        user_name = user['musicbrainz_id']
        self._create_test_data(user_name, user["id"])

        user2 = db_user.get_or_create(3, 'otheruser')
        user_name2 = user2['musicbrainz_id']
        self._create_test_data(user_name2, user2["id"])

        recent = self.logstore.fetch_recent_listens_for_users([user, user2], per_user_limit=1, min_ts=int(time()) - 10000000000)
        self.assertEqual(len(recent), 2)

        recent = self.logstore.fetch_recent_listens_for_users([user, user2], min_ts=int(time()) - 10000000000)
        self.assertEqual(len(recent), 4)

        recent = self.logstore.fetch_recent_listens_for_users([user], min_ts=recent[0].ts_since_epoch - 1)
        self.assertEqual(len(recent), 1)
        self.assertEqual(recent[0].ts_since_epoch, 1400000200)

    def test_listen_counts_in_cache(self):
        uid = random.randint(2000, 1 << 31)
        testuser = db_user.get_or_create(uid, "user_%d" % uid)
        testuser_name = testuser['musicbrainz_id']
        count = self._create_test_data(testuser_name, testuser["id"])
        user_key = REDIS_USER_LISTEN_COUNT + str(testuser["id"])
        self.assertEqual(count, self.logstore.get_listen_count_for_user(testuser["id"]))
        self.assertEqual(count, cache.get(user_key))

    def test_delete_listens(self):
        uid = random.randint(2000, 1 << 31)
        testuser = db_user.get_or_create(uid, "user_%d" % uid)
        testuser_name = testuser['musicbrainz_id']
        self._create_test_data(testuser_name, testuser["id"])
        listens, min_ts, max_ts = self.logstore.fetch_listens(user=testuser, to_ts=1400000300)
        self.assertEqual(len(listens), 5)
        self.assertEqual(listens[0].ts_since_epoch, 1400000200)
        self.assertEqual(listens[1].ts_since_epoch, 1400000150)
        self.assertEqual(listens[2].ts_since_epoch, 1400000100)
        self.assertEqual(listens[3].ts_since_epoch, 1400000050)
        self.assertEqual(listens[4].ts_since_epoch, 1400000000)

        self.logstore.delete(testuser["id"])
        listens, min_ts, max_ts = self.logstore.fetch_listens(user=testuser, to_ts=1400000300)
        self.assertEqual(len(listens), 0)

    def test_delete_single_listen(self):
        uid = random.randint(2000, 1 << 31)
        testuser = db_user.get_or_create(uid, "user_%d" % uid)
        testuser_name = testuser['musicbrainz_id']
        self._create_test_data(testuser_name, testuser["id"])

        listens, min_ts, max_ts = self.logstore.fetch_listens(user=testuser, to_ts=1400000300)
        self.assertEqual(len(listens), 5)
        self.assertEqual(listens[0].ts_since_epoch, 1400000200)
        self.assertEqual(listens[1].ts_since_epoch, 1400000150)
        self.assertEqual(listens[2].ts_since_epoch, 1400000100)
        self.assertEqual(listens[3].ts_since_epoch, 1400000050)
        self.assertEqual(listens[4].ts_since_epoch, 1400000000)

        self.logstore.delete_listen(1400000050, testuser["id"], "c7a41965-9f1e-456c-8b1d-27c0f0dde280")

        pending = self._get_pending_deletes()
        self.assertEqual(len(pending), 1)
        self.assertEqual(pending[0]["listened_at"], 1400000050)
        self.assertEqual(pending[0]["user_id"], testuser["id"])
        self.assertEqual(str(pending[0]["recording_msid"]), "c7a41965-9f1e-456c-8b1d-27c0f0dde280")

        delete_listens_and_update_user_listen_data()

        # clear cache entry so that count is fetched from db again
        cache.delete(REDIS_USER_LISTEN_COUNT + str(testuser["id"]))

        listens, min_ts, max_ts = self.logstore.fetch_listens(user=testuser, to_ts=1400000300)
        self.assertEqual(len(listens), 4)
        self.assertEqual(listens[0].ts_since_epoch, 1400000200)
        self.assertEqual(listens[1].ts_since_epoch, 1400000150)
        self.assertEqual(listens[2].ts_since_epoch, 1400000100)
        self.assertEqual(listens[3].ts_since_epoch, 1400000000)

        self.assertEqual(self.logstore.get_listen_count_for_user(testuser["id"]), 4)
        min_ts, max_ts = self.logstore.get_timestamps_for_user(testuser["id"])
        self.assertEqual(min_ts, 1400000000)
        self.assertEqual(max_ts, 1400000200)

    def _get_pending_deletes(self):
        with timescale.engine.connect() as connection:
            result = connection.execute(text("SELECT * FROM listen_delete_metadata"))
            return result.fetchall()

    def _get_count_and_timestamps(self, user_id):
        with timescale.engine.connect() as connection:
            result = connection.execute(
                text("""
                    SELECT count, min_listened_at, max_listened_at
                      FROM listen_user_metadata
                     WHERE user_id = :user_id
                """), user_id=user_id)
            return dict(**result.fetchone())

    def test_for_empty_timestamps(self):
        """Test newly created user has empty timestamps and count stored in the database."""
        uid = random.randint(2000, 1 << 31)
        testuser = db_user.get_or_create(uid, "user_%d" % uid)
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
        testuser2 = db_user.get_or_create(uid, f"user_{uid}")
        count_user_2 = self._create_test_data(testuser2["musicbrainz_id"], testuser2["id"])

        cache.delete(REDIS_TOTAL_LISTEN_COUNT)
        add_missing_to_listen_users_metadata()
        update_user_listen_data()

        total_count = self.logstore.get_total_listen_count()
        self.assertEqual(total_count, count_user_1 + count_user_2)

    def test_get_timestamps_for_user(self):
        self._create_test_data(self.testuser["musicbrainz_id"], self.testuser["id"])
        min_ts, max_ts = self.logstore.get_timestamps_for_user(self.testuser["id"])
        self.assertEqual(1400000200, max_ts)
        self.assertEqual(1400000000, min_ts)

        # test timestamps consider listens which were created since last cron run as well
        self._create_test_data(
            self.testuser["musicbrainz_id"],
            self.testuser["id"],
            "timescale_listenstore_test_listens_2.json",
            recalculate=False
        )
        # do not recalculate/update user data
        min_ts, max_ts = self.logstore.get_timestamps_for_user(self.testuser["id"])
        self.assertEqual(1400000500, max_ts)
        self.assertEqual(1400000000, min_ts)

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
        listens, min_ts, max_ts = self.logstore.fetch_listens(user=self.testuser, from_ts=1400000300, limit=1)
        self.assertEqual(len(listens), 1)
        self.assertEqual(listens[0].ts_since_epoch, 1400000500)
        self.assertEqual(min_ts, 1400000000)
        self.assertEqual(max_ts, 1400000500)
