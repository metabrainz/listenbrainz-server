from datetime import datetime, timedelta

from sqlalchemy import text

from listenbrainz.db.testing import DatabaseTestCase
from listenbrainz.db import user as db_user, do_not_recommend
from listenbrainz import db


class DoNotRecommendDatabaseTestCase(DatabaseTestCase):

    def _get_all_entries(self):
        with db.engine.connect() as conn:
            results = conn.execute(text("""
                SELECT entity, entity_mbid::text, extract(epoch from until)::int as until
                  FROM recommendation.do_not_recommend
            """))
            return results.mappings().all()

    def test_clear_expired(self):
        self.user = db_user.get_or_create(1, "test_user")
        items = [
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
        for item in items:
            do_not_recommend.insert(self.user["id"], item["entity"], item["entity_mbid"], item["until"])

        # all inserted items found
        found = self._get_all_entries()
        self.assertCountEqual(found, items)

        # deleted expired item
        do_not_recommend.clear_expired()

        # expired item not found but non-expired items exist
        found = self._get_all_entries()
        self.assertCountEqual(found, [items[1], items[2]])
