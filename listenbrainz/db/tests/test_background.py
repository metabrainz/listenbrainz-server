from datetime import datetime, timezone

from sqlalchemy import text

import listenbrainz.db.user as db_user
from listenbrainz.db import background
from listenbrainz.db.testing import DatabaseTestCase


class BackgroundTestCase(DatabaseTestCase):

    def setUp(self):
        super().setUp()
        self.user = db_user.get_or_create(self.db_conn, 1, "background_user")

    def _create_import(self, service):
        return background.create_import_task(
            self.db_conn,
            user_id=self.user["id"],
            service=service,
            from_date=datetime(2021, 1, 1, tzinfo=timezone.utc),
            to_date=datetime(2022, 1, 1, tzinfo=timezone.utc),
            file_path=f"{service}.zip",
            filename=f"{service}.zip",
        )

    def test_second_import_while_one_is_queued(self):
        self.assertIsNotNone(self._create_import("spotify"))
        self.db_conn.commit()

        # an import for a different service passes the API's per-service check but gets no task row
        self.assertIsNone(self._create_import("librefm"))
        self.db_conn.rollback()

        count = self.db_conn.execute(text("SELECT count(*) FROM user_data_import")).scalar()
        self.assertEqual(count, 1)
