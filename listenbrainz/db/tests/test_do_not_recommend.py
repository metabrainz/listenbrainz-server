from datetime import datetime, timedelta

from sqlalchemy import text

from listenbrainz.db.testing import DatabaseTestCase
from listenbrainz.db import user as db_user, do_not_recommend


class DoNotRecommendDatabaseTestCase(DatabaseTestCase):

    def setUp(self):
        super(DoNotRecommendDatabaseTestCase, self).setUp()
        self.user = db_user.get_or_create(self.db_conn, 1, "test_user")
        self.items = [
            {
                "entity": "release",
                "entity_mbid": "e16bf88e-643d-4d9f-9e2e-fb4ddb0b2ea7",
                "until": int((datetime.now() - timedelta(days=1)).timestamp())
            },
            {
                "entity": "release",
                "entity_mbid": "79e6db72-0254-4ddf-856f-aa4e3e1c87ae",
                "until": None
            },
            {
                "entity": "release",
                "entity_mbid": "e6472b5e-6d82-42de-a3d5-906af710feeb",
                "until": int((datetime.now() + timedelta(days=1)).timestamp())
            },
        ]

    def _get_all_entries(self):
        results = self.db_conn.execute(text("""
            SELECT entity, entity_mbid::text, extract(epoch from until)::int as until
              FROM recommendation.do_not_recommend
        """))
        return results.mappings().all()

    def create_dummy_data(self):
        for item in self.items:
            do_not_recommend.insert(self.db_conn, self.user["id"], item["entity"], item["entity_mbid"], item["until"])

    def test_clear_expired(self):
        self.create_dummy_data()

        # all inserted items found
        found = self._get_all_entries()
        self.assertCountEqual(found, self.items)

        # deleted expired item
        do_not_recommend.clear_expired(self.db_conn)

        # expired item not found but non-expired items exist
        found = self._get_all_entries()
        self.assertCountEqual(found, self.items[1:])

    def test_get_total_count(self):
        self.create_dummy_data()
        received = do_not_recommend.get_total_count(self.db_conn, self.user["id"])
        # inserted 3 pins but one is expired so don't include it in total count
        self.assertEqual(2, received)
