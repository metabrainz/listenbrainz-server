from listenbrainz.db.testing import DatabaseTestCase

import uuid
import listenbrainz.db.user as db_user
import listenbrainz.db.event_interaction as db_event_interaction


class EventInteractionTestCase(DatabaseTestCase):
    def setUp(self):
        super(EventInteractionTestCase, self).setUp()
        self.main_user = db_user.get_or_create(self.db_conn, 1, "failure_san")
        self.other_user = db_user.get_or_create(self.db_conn, 2, "not_failure_san")

        # using sample event MBIDs for testing
        self.event_mbid_1 = str(uuid.uuid4())
        self.event_mbid_2 = str(uuid.uuid4())

    def test_watch_event(self):
        db_event_interaction.watch_event(
            self.db_conn,
            self.main_user["id"],
            self.event_mbid_1,
        )
        self.assertTrue(
            db_event_interaction.is_watching_event(
                self.db_conn,
                self.main_user["id"],
                self.event_mbid_1,
            )
        )

    def test_watch_event_idempotent(self):
        """
        Watching the same event twice should not raise an error.
        """
        db_event_interaction.watch_event(
            self.db_conn,
            self.main_user["id"],
            self.event_mbid_1,
        )
        # second watch should silently do nothing
        db_event_interaction.watch_event(
            self.db_conn,
            self.main_user["id"],
            self.event_mbid_1,
        )
        self.assertTrue(
            db_event_interaction.is_watching_event(
                self.db_conn,
                self.main_user["id"],
                self.event_mbid_1,
            )
        )

    def test_unwatch_event(self):
        db_event_interaction.watch_event(
            self.db_conn,
            self.main_user["id"],
            self.event_mbid_1,
        )
        self.assertTrue(
            db_event_interaction.is_watching_event(
                self.db_conn,
                self.main_user["id"],
                self.event_mbid_1,
            )
        )
        db_event_interaction.unwatch_event(
            self.db_conn,
            self.main_user["id"],
            self.event_mbid_1,
        )
        self.assertFalse(
            db_event_interaction.is_watching_event(
                self.db_conn,
                self.main_user["id"],
                self.event_mbid_1,
            )
        )
        # second unwatch does nothing
        db_event_interaction.unwatch_event(
            self.db_conn,
            self.main_user["id"],
            self.event_mbid_1,
        )

    def test_is_watching_event(self):
        self.assertFalse(
            db_event_interaction.is_watching_event(
                self.db_conn,
                self.main_user["id"],
                self.event_mbid_1,
            )
        )
        db_event_interaction.watch_event(
            self.db_conn,
            self.main_user["id"],
            self.event_mbid_1,
        )
        self.assertTrue(
            db_event_interaction.is_watching_event(
                self.db_conn,
                self.main_user["id"],
                self.event_mbid_1,
            )
        )

    def test_get_watched_events(self):
        watched = db_event_interaction.get_watched_events(
            self.db_conn, self.main_user["id"]
        )
        self.assertListEqual(watched, [])

        db_event_interaction.watch_event(
            self.db_conn,
            self.main_user["id"],
            self.event_mbid_1,
        )
        watched = db_event_interaction.get_watched_events(
            self.db_conn, self.main_user["id"]
        )
        self.assertEqual(1, len(watched))

        db_event_interaction.watch_event(
            self.db_conn,
            self.main_user["id"],
            self.event_mbid_2,
        )
        watched = db_event_interaction.get_watched_events(
            self.db_conn, self.main_user["id"]
        )
        self.assertEqual(2, len(watched))

    def test_get_watched_events_pagination(self):
        db_event_interaction.watch_event(
            self.db_conn,
            self.main_user["id"],
            self.event_mbid_1,
        )
        db_event_interaction.watch_event(
            self.db_conn,
            self.main_user["id"],
            self.event_mbid_2,
        )

        # limit to 1, returns 1 result
        watched = db_event_interaction.get_watched_events(
            self.db_conn, self.main_user["id"], limit=1
        )
        self.assertEqual(1, len(watched))

        # offset by 1, returns 1 result
        watched = db_event_interaction.get_watched_events(
            self.db_conn, self.main_user["id"], limit=50, offset=1
        )
        self.assertEqual(1, len(watched))

    def test_get_watchers_count(self):
        # no watchers
        count = db_event_interaction.get_watchers_count(self.db_conn, self.event_mbid_1)
        self.assertEqual(0, count)

        # first user watching
        db_event_interaction.watch_event(
            self.db_conn,
            self.main_user["id"],
            self.event_mbid_1,
        )
        count = db_event_interaction.get_watchers_count(self.db_conn, self.event_mbid_1)
        self.assertEqual(1, count)

        # second user watching
        db_event_interaction.watch_event(
            self.db_conn,
            self.other_user["id"],
            self.event_mbid_1,
        )
        count = db_event_interaction.get_watchers_count(self.db_conn, self.event_mbid_1)
        self.assertEqual(2, count)

    def test_get_users_watching_event(self):
        # no watchers
        watchers = db_event_interaction.get_users_watching_event(
            self.db_conn, self.event_mbid_1
        )
        self.assertListEqual(watchers, [])

        # first user watching
        db_event_interaction.watch_event(
            self.db_conn,
            self.main_user["id"],
            self.event_mbid_1,
        )
        watchers = db_event_interaction.get_users_watching_event(
            self.db_conn, self.event_mbid_1
        )
        self.assertEqual(1, len(watchers))

        # second user watching
        db_event_interaction.watch_event(
            self.db_conn,
            self.other_user["id"],
            self.event_mbid_1,
        )
        watchers = db_event_interaction.get_users_watching_event(
            self.db_conn, self.event_mbid_1
        )
        self.assertEqual(2, len(watchers))
