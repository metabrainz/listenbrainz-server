import uuid
from datetime import datetime, timezone

from sqlalchemy import text

import listenbrainz.db.event_feed as db_event_feed
from listenbrainz.db.testing import TimescaleTestCase


class EventFeedDBTestCase(TimescaleTestCase):

    def setUp(self):
        super().setUp()
        self.artist_mbid_1 = str(uuid.uuid4())
        self.artist_mbid_2 = str(uuid.uuid4())

    def insert_event(self, event_id, artists, **fields):
        event_mbid = str(uuid.uuid4())
        self.ts_conn.execute(text("""
            INSERT INTO mapping.mb_event_cache
                        (event_mbid, event_id, event_name, begin_date_year, begin_date_month, begin_date_day,
                         event_time, cancelled, ended, event_data)
                 VALUES (:event_mbid ::UUID, :event_id, :event_name, :begin_date_year, :begin_date_month, :begin_date_day,
                         :event_time, :cancelled, :ended, '{}')
        """), {
            "event_mbid": event_mbid,
            "event_id": event_id,
            "event_name": "Event %d" % event_id,
            "begin_date_year": fields.get("begin_date_year"),
            "begin_date_month": fields.get("begin_date_month"),
            "begin_date_day": fields.get("begin_date_day"),
            "event_time": fields.get("event_time"),
            "cancelled": fields.get("cancelled", False),
            "ended": fields.get("ended", False),
        })
        for link_id, artist_mbid in enumerate(artists, start=1):
            self.ts_conn.execute(text("""
                INSERT INTO mapping.mb_event_artist_cache
                            (event_mbid, event_id, artist_mbid, artist_id, link_id, link_type_gid,
                             link_type_name, relationship_data)
                     VALUES (:event_mbid ::UUID, :event_id, :artist_mbid ::UUID, 1, :link_id, gen_random_uuid(),
                             'main performer', '{}')
            """), {
                "event_mbid": event_mbid,
                "event_id": event_id,
                "artist_mbid": artist_mbid,
                "link_id": link_id,
            })
        return event_mbid

    def insert_events(self):
        """ Each event exists to exercise one rule of the feed queries:
            1: later date than 2, so ordering is by date and not by event_id
            2: earliest date; linked twice to artist 1 and once to artist 2, so must appear only once
            3: no date at all, sorts last
            4: cancelled, excluded
            5: ended, excluded
            6: only artist 2, so must not appear in artist 1's feed; partial date (no day)
        """
        return {
            1: self.insert_event(1, [self.artist_mbid_1], begin_date_year=2027, begin_date_month=1, begin_date_day=1),
            2: self.insert_event(2, [self.artist_mbid_1, self.artist_mbid_1, self.artist_mbid_2],
                                 begin_date_year=2026, begin_date_month=12, begin_date_day=1,
                                 event_time=datetime(2026, 12, 1, 20, 0, tzinfo=timezone.utc)),
            3: self.insert_event(3, [self.artist_mbid_1]),
            4: self.insert_event(4, [self.artist_mbid_1], begin_date_year=2027, begin_date_month=2, begin_date_day=1,
                                 cancelled=True),
            5: self.insert_event(5, [self.artist_mbid_1], begin_date_year=2027, begin_date_month=3, begin_date_day=1,
                                 ended=True),
            6: self.insert_event(6, [self.artist_mbid_2], begin_date_year=2027, begin_date_month=6),
        }

    def test_get_upcoming_events_for_artists(self):
        self.assertEqual([], db_event_feed.get_upcoming_events_for_artists(self.ts_conn, []))

        self.insert_events()

        events = db_event_feed.get_upcoming_events_for_artists(self.ts_conn, [self.artist_mbid_1])
        self.assertEqual([2, 1, 3], [e.event_id for e in events])

        events = db_event_feed.get_upcoming_events_for_artists(self.ts_conn, [self.artist_mbid_1, self.artist_mbid_2])
        self.assertEqual([2, 1, 6, 3], [e.event_id for e in events])

        events = db_event_feed.get_upcoming_events_for_artists(self.ts_conn, [self.artist_mbid_1], limit=1)
        self.assertEqual([2], [e.event_id for e in events])

        events = db_event_feed.get_upcoming_events_for_artists(
            self.ts_conn, [self.artist_mbid_1, self.artist_mbid_2], limit=25, offset=1
        )
        self.assertEqual([1, 6, 3], [e.event_id for e in events])

        self.assertEqual([], db_event_feed.get_upcoming_events_for_artists(self.ts_conn, [str(uuid.uuid4())]))

    def test_get_upcoming_events_global(self):
        events, total_count = db_event_feed.get_upcoming_events_global(self.ts_conn)
        self.assertEqual([], events)
        self.assertEqual(0, total_count)

        self.insert_events()

        events, total_count = db_event_feed.get_upcoming_events_global(self.ts_conn)
        self.assertEqual(4, total_count)
        self.assertEqual([2, 1, 6, 3], [e.event_id for e in events])

        events, total_count = db_event_feed.get_upcoming_events_global(self.ts_conn, limit=2)
        self.assertEqual(4, total_count)
        self.assertEqual([2, 1], [e.event_id for e in events])

        events, total_count = db_event_feed.get_upcoming_events_global(self.ts_conn, limit=25, offset=3)
        self.assertEqual(4, total_count)
        self.assertEqual([3], [e.event_id for e in events])
