from datetime import datetime, timezone
from unittest.mock import patch

from sqlalchemy import text

import listenbrainz.db.user as db_user
from listenbrainz.db import listens as listens_db

from listenbrainz.listenstore.tests.util import create_test_data_for_timescalelistenstore
from listenbrainz.listenstore.timescale_listenstore import EPOCH
from listenbrainz.listenstore.timescale_utils import recalculate_all_user_data, delete_listens
from listenbrainz.tests.integration import NonAPIIntegrationTestCase
from listenbrainz.webserver import timescale_connection, redis_connection


class TestTimescaleUtils(NonAPIIntegrationTestCase):

    def setUp(self):
        super(TestTimescaleUtils, self).setUp()
        self.ls = timescale_connection._ts
        self.rs = redis_connection._redis

    def _create_test_data(self, user, file=None):
        test_data = create_test_data_for_timescalelistenstore(user["musicbrainz_id"], user["id"], file)
        self.ls.insert(test_data)
        return len(test_data)

    def _get_listen_count(self, user):
        with listens_db.engine.connect() as connection:
            return connection.execute(
                text("SELECT count FROM listen_user_metadata WHERE user_id = :user_id"),
                {"user_id": user["id"]}
            ).scalar()

    def test_ingestion_counts_inserted_listens_only(self):
        user = db_user.get_or_create(self.db_conn, 1, "user_1")
        self._create_test_data(user)
        self.assertEqual(self._get_listen_count(user), 5)

        # resubmitted listens are duplicates and must not be counted again
        self._create_test_data(user)
        self.assertEqual(self._get_listen_count(user), 5)

        self._create_test_data(user, "timescale_listenstore_test_listens_2.json")
        self.assertEqual(self._get_listen_count(user), 6)
        self.assertEqual(self.ls.get_timestamps_for_user(user["id"]), (
            datetime.fromtimestamp(1400000000, timezone.utc),
            datetime.fromtimestamp(1400000500, timezone.utc),
        ))

    def test_delete_listens_updates_counts(self):
        user_1 = db_user.get_or_create(self.db_conn, 1, "user_1")
        user_2 = db_user.get_or_create(self.db_conn, 2, "user_2")
        self._create_test_data(user_1)
        self._create_test_data(user_2)

        self.ls.delete_listen(
            datetime.fromtimestamp(1400000000, timezone.utc),
            user_1["id"],
            "4269ddbc-9241-46da-935d-4fa9e0f7f371"
        )
        # a duplicate delete request must not be subtracted twice
        self.ls.delete_listen(
            datetime.fromtimestamp(1400000000, timezone.utc),
            user_1["id"],
            "4269ddbc-9241-46da-935d-4fa9e0f7f371"
        )
        # a delete for a listen that does not exist must not change the count
        self.ls.delete_listen(
            datetime.fromtimestamp(1400000500, timezone.utc),
            user_1["id"],
            "4269ddbc-9241-46da-935d-4fa9e0f7f371"
        )
        self.ls.delete_listen(
            datetime.fromtimestamp(1400000100, timezone.utc),
            user_2["id"],
            "08ade1eb-800e-4ad8-8184-32941664ac02"
        )

        delete_listens()

        self.assertEqual(self._get_listen_count(user_1), 4)
        self.assertEqual(self._get_listen_count(user_2), 4)
        # the oldest listen of user_1 was deleted
        self.assertEqual(self.ls.get_timestamps_for_user(user_1["id"]), (
            datetime.fromtimestamp(1400000050, timezone.utc),
            datetime.fromtimestamp(1400000200, timezone.utc),
        ))
        with listens_db.engine.connect() as connection:
            statuses = connection.execute(text(
                "SELECT status, count(*) FROM listen_delete_metadata GROUP BY status"
            )).all()
        self.assertEqual(dict(statuses), {"complete": 3, "invalid": 1})

        delete_listens()
        self.assertEqual(self._get_listen_count(user_1), 4)

    def test_delete_user_listens_recounts_retained_listens(self):
        user = db_user.get_or_create(self.db_conn, 1, "user_1")
        self._create_test_data(user)
        with listens_db.engine.connect() as connection:
            cutoff = connection.execute(text(
                "SELECT max(created) FROM listen WHERE user_id = :user_id"
            ), {"user_id": user["id"]}).scalar()
        # listens created after the cutoff survive the history deletion
        self._create_test_data(user, "timescale_listenstore_test_listens_2.json")

        self.ls.delete(user["id"], cutoff)

        self.assertEqual(self._get_listen_count(user), 1)
        min_ts, max_ts = self.ls.get_timestamps_for_user(user["id"])
        self.assertEqual(min_ts, datetime.fromtimestamp(1400000500, timezone.utc))
        self.assertEqual(max_ts, datetime.fromtimestamp(1400000500, timezone.utc))

    def test_recalculate_all_user_data(self):
        user_1 = db_user.get_or_create(self.db_conn, 1, "user_1")
        user_2 = db_user.get_or_create(self.db_conn, 2, "user_2")
        self._create_test_data(user_1)
        with listens_db.engine.begin() as connection:
            connection.execute(text("TRUNCATE listen_user_metadata"))
            connection.execute(text("""
                INSERT INTO listen_user_metadata (user_id, count, min_listened_at, max_listened_at)
                     VALUES (:user_id, 42, 'epoch', NOW())
            """), {"user_id": user_2["id"]})

        recalculate_all_user_data()

        self.assertEqual(self._get_listen_count(user_1), 5)
        self.assertEqual(self.ls.get_timestamps_for_user(user_1["id"]), (
            datetime.fromtimestamp(1400000000, timezone.utc),
            datetime.fromtimestamp(1400000200, timezone.utc),
        ))
        self.assertEqual(self._get_listen_count(user_2), 0)
        self.assertEqual(self.ls.get_timestamps_for_user(user_2["id"]), (EPOCH, EPOCH))

    def test_recalculate_corrects_stale_bounds(self):
        user = db_user.get_or_create(self.db_conn, 1, "user_1")
        self._create_test_data(user)
        # the count is right, only the bounds are wrong
        with listens_db.engine.begin() as connection:
            connection.execute(text("UPDATE listen_user_metadata SET max_listened_at = NOW()"))

        recalculate_all_user_data()

        self.assertEqual(self._get_listen_count(user), 5)
        self.assertEqual(
            self.ls.get_timestamps_for_user(user["id"])[1],
            datetime.fromtimestamp(1400000200, timezone.utc)
        )

    def test_recalculate_corrects_deletes_without_metadata_row(self):
        user = db_user.get_or_create(self.db_conn, 1, "user_1")
        self._create_test_data(user)
        # listens inserted before counts were maintained have no row
        with listens_db.engine.begin() as connection:
            connection.execute(text("TRUNCATE listen_user_metadata"))

        self.ls.delete_listen(
            datetime.fromtimestamp(1400000000, timezone.utc),
            user["id"],
            "4269ddbc-9241-46da-935d-4fa9e0f7f371"
        )
        delete_listens()
        self.assertEqual(self._get_listen_count(user), -1)

        recalculate_all_user_data()
        self.assertEqual(self._get_listen_count(user), 4)
        self.assertEqual(self.ls.get_timestamps_for_user(user["id"]), (
            datetime.fromtimestamp(1400000050, timezone.utc),
            datetime.fromtimestamp(1400000200, timezone.utc),
        ))

    def test_recalculate_keeps_concurrent_inserts(self):
        user = db_user.get_or_create(self.db_conn, 1, "user_1")
        self._create_test_data(user)
        with listens_db.engine.begin() as connection:
            connection.execute(text("UPDATE listen_user_metadata SET count = 42"))

        original_refresh = listens_db._refresh_listen_metadata
        inserted = False

        def insert_between_snapshot_and_refresh(*args, **kwargs):
            # simulate a listen committed after the stale users were found but before they are locked
            nonlocal inserted
            inserted = True
            self._create_test_data(user, "timescale_listenstore_test_listens_2.json")
            return original_refresh(*args, **kwargs)

        with patch.object(listens_db, "_refresh_listen_metadata", side_effect=insert_between_snapshot_and_refresh):
            recalculate_all_user_data()

        self.assertTrue(inserted)
        self.assertEqual(self._get_listen_count(user), 6)
        self.assertEqual(
            self.ls.get_timestamps_for_user(user["id"])[1],
            datetime.fromtimestamp(1400000500, timezone.utc)
        )

    def test_delete_user_listens_without_metadata_row(self):
        user = db_user.get_or_create(self.db_conn, 1, "user_1")
        self._create_test_data(user)
        with listens_db.engine.begin() as connection:
            cutoff = connection.execute(text(
                "SELECT max(created) FROM listen WHERE user_id = :user_id"
            ), {"user_id": user["id"]}).scalar()
            connection.execute(text("TRUNCATE listen_user_metadata"))
        self._create_test_data(user, "timescale_listenstore_test_listens_2.json")

        self.ls.delete(user["id"], cutoff)

        self.assertEqual(self._get_listen_count(user), 1)
        self.assertEqual(self.ls.get_timestamps_for_user(user["id"]), (
            datetime.fromtimestamp(1400000500, timezone.utc),
            datetime.fromtimestamp(1400000500, timezone.utc),
        ))

    def test_insert_reports_listens_db_rows_after_history_delete(self):
        user = db_user.get_or_create(self.db_conn, 1, "user_1")
        test_data = create_test_data_for_timescalelistenstore(user["musicbrainz_id"], user["id"])
        self.assertEqual(len(self.ls.insert(test_data)), 5)
        self.assertEqual(self.ls.insert(test_data), [])

        # Timescale retains the deleted listens, so a re-import is only new in the listens DB
        self.ls.delete(user["id"])
        inserted = self.ls.insert(test_data)
        self.assertEqual(
            sorted((int(listened_at.timestamp()), user_id, msid) for listened_at, user_id, msid in inserted),
            sorted((listen.ts_since_epoch, listen.user_id, listen.recording_msid) for listen in test_data),
        )
        self.assertEqual(self._get_listen_count(user), 5)

    def test_insert_commits_in_chunks(self):
        user = db_user.get_or_create(self.db_conn, 1, "user_1")
        test_data = create_test_data_for_timescalelistenstore(user["musicbrainz_id"], user["id"])
        with patch.object(listens_db, "INSERT_BATCH_SIZE", 2):
            self.assertEqual(len(self.ls.insert(test_data)), 5)
        self.assertEqual(self._get_listen_count(user), 5)

    @patch("listenbrainz.listenstore.timescale_utils.invalidate_user_listen_caches")
    def test_delete_listens_invalidates_caches(self, mock_invalidate):
        user_1 = db_user.get_or_create(self.db_conn, 1, "user_1")
        user_2 = db_user.get_or_create(self.db_conn, 2, "user_2")
        self._create_test_data(user_1)
        self._create_test_data(user_2)
        self.ls.delete_listen(
            datetime.fromtimestamp(1400000000, timezone.utc),
            user_1["id"],
            "4269ddbc-9241-46da-935d-4fa9e0f7f371"
        )

        delete_listens()

        mock_invalidate.assert_called_once_with(user_1["id"])

    def test_delete_user_removes_metadata_row(self):
        user = db_user.get_or_create(self.db_conn, 1, "user_1")
        self._create_test_data(user)

        listens_db.delete_user(user["id"], datetime.now(timezone.utc), delete_metadata=True)

        self.assertIsNone(self._get_listen_count(user))
