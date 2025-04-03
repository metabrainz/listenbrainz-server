from datetime import datetime, timezone

from sqlalchemy import text

import listenbrainz.db.user as db_user
from listenbrainz.db import timescale

from listenbrainz.listenstore.tests.util import create_test_data_for_timescalelistenstore
from listenbrainz.listenstore.timescale_utils import recalculate_all_user_data, update_user_listen_data, \
    delete_listens
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

    def _get_count_and_timestamp(self, user):
        with timescale.engine.connect() as connection:
            result = connection.execute(
                text("""
                    SELECT count, min_listened_at, max_listened_at
                      FROM listen_user_metadata
                     WHERE user_id = :user_id
                """), {"user_id": user["id"]})
            row = result.fetchone()
            return {
                "count": row.count,
                "min_listened_at": row.min_listened_at,
                "max_listened_at": row.max_listened_at
            }

    def test_delete_listens_update_metadata(self):
        user_1 = db_user.get_or_create(self.db_conn, 1, "user_1")
        user_2 = db_user.get_or_create(self.db_conn, 2, "user_2")
        recalculate_all_user_data()

        self._create_test_data(user_1)
        self._create_test_data(user_2)
        update_user_listen_data()

        metadata_1 = self._get_count_and_timestamp(user_1)
        self.assertEqual(metadata_1["min_listened_at"], datetime.fromtimestamp(1400000000, timezone.utc))
        self.assertEqual(metadata_1["max_listened_at"], datetime.fromtimestamp(1400000200, timezone.utc))
        self.assertEqual(metadata_1["count"], 5)

        metadata_2 = self._get_count_and_timestamp(user_2)
        self.assertEqual(metadata_2["min_listened_at"], datetime.fromtimestamp(1400000000, timezone.utc))
        self.assertEqual(metadata_2["max_listened_at"], datetime.fromtimestamp(1400000200, timezone.utc))
        self.assertEqual(metadata_2["count"], 5)

        # to test the case when the update script has not run since delete, so metadata in listen_user_metadata does
        # account for this listen and deleting should not affect it either.
        self._create_test_data(user_1, "timescale_listenstore_test_listens_2.json")
        self.ls.delete_listen(
            datetime.fromtimestamp(1400000500, timezone.utc),
            user_1["id"],
            "4269ddbc-9241-46da-935d-4fa9e0f7f371"
        )

        # test min_listened_at is updated if that listen is deleted for a user
        self.ls.delete_listen(
            datetime.fromtimestamp(1400000000, timezone.utc),
            user_1["id"],
            "4269ddbc-9241-46da-935d-4fa9e0f7f371"
        )
        # test max_listened_at is updated if that listen is deleted for a user
        self.ls.delete_listen(
            datetime.fromtimestamp(1400000200, timezone.utc),
            user_1["id"],
            "db072fa7-0c7f-4f55-b90f-a88da531b219"
        )
        # test normal listen delete updates correctly
        self.ls.delete_listen(
            datetime.fromtimestamp(1400000100, timezone.utc),
            user_2["id"],
            "08ade1eb-800e-4ad8-8184-32941664ac02"
        )

        delete_listens()

        metadata_1 = self._get_count_and_timestamp(user_1)
        self.assertEqual(metadata_1["min_listened_at"], datetime.fromtimestamp(1400000050, timezone.utc))
        self.assertEqual(metadata_1["max_listened_at"], datetime.fromtimestamp(1400000150, timezone.utc))
        self.assertEqual(metadata_1["count"], 3)

        metadata_2 = self._get_count_and_timestamp(user_2)
        self.assertEqual(metadata_2["min_listened_at"], datetime.fromtimestamp(1400000000, timezone.utc))
        self.assertEqual(metadata_2["max_listened_at"], datetime.fromtimestamp(1400000200, timezone.utc))
        self.assertEqual(metadata_2["count"], 4)
