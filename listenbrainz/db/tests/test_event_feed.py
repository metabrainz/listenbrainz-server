import json
import uuid
from datetime import date, datetime, timedelta, timezone

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
                         end_date_year, end_date_month, end_date_day, event_time, cancelled, ended, event_data)
                 VALUES (:event_mbid ::UUID, :event_id, :event_name, :begin_date_year, :begin_date_month, :begin_date_day,
                         :end_date_year, :end_date_month, :end_date_day, :event_time, :cancelled, :ended, '{}')
        """), {
            "event_mbid": event_mbid,
            "event_id": event_id,
            "event_name": "Event %d" % event_id,
            "begin_date_year": fields.get("begin_date_year"),
            "begin_date_month": fields.get("begin_date_month"),
            "begin_date_day": fields.get("begin_date_day"),
            "end_date_year": fields.get("end_date_year"),
            "end_date_month": fields.get("end_date_month"),
            "end_date_day": fields.get("end_date_day"),
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
        """ Each event exists to exercise one rule of the feed queries. Events with an end date are marked
            ended, as MB always marks them, to show that the queries do not rely on it.
            1: later date than 2, so ordering is by date and not by event_id; a one day event next year
            2: started last week and ends next week, so in progress; linked twice to artist 1 and once to
               artist 2, so must appear only once
            3: no date at all, excluded from both upcoming and past events
            4: cancelled, excluded
            5: ended last year, so a past event and not an upcoming one; linked twice to artist 1, so must
               appear only once
            6: only artist 2, so must not appear in artist 1's feed; partial date (no day)
            7: ended later last year than 5 despite its higher event_id, so past events are ordered by date
            8: cancelled last year, later than 5, so must not appear in the past events either
        """
        today = date.today()
        started = today - timedelta(days=7)
        ends = today + timedelta(days=7)
        next_year = today.year + 1
        last_year = today.year - 1
        return {
            1: self.insert_event(1, [self.artist_mbid_1], begin_date_year=next_year, begin_date_month=1, begin_date_day=1,
                                 end_date_year=next_year, end_date_month=1, end_date_day=1, ended=True),
            2: self.insert_event(2, [self.artist_mbid_1, self.artist_mbid_1, self.artist_mbid_2],
                                 begin_date_year=started.year, begin_date_month=started.month, begin_date_day=started.day,
                                 end_date_year=ends.year, end_date_month=ends.month, end_date_day=ends.day, ended=True,
                                 event_time=datetime(started.year, started.month, started.day, 20, 0, tzinfo=timezone.utc)),
            3: self.insert_event(3, [self.artist_mbid_1]),
            4: self.insert_event(4, [self.artist_mbid_1], begin_date_year=next_year, begin_date_month=2, begin_date_day=1,
                                 cancelled=True),
            5: self.insert_event(5, [self.artist_mbid_1, self.artist_mbid_1], begin_date_year=last_year, begin_date_month=3,
                                 begin_date_day=1, end_date_year=last_year, end_date_month=3, end_date_day=1, ended=True),
            6: self.insert_event(6, [self.artist_mbid_2], begin_date_year=next_year, begin_date_month=6),
            7: self.insert_event(7, [self.artist_mbid_1], begin_date_year=last_year, begin_date_month=11, begin_date_day=1,
                                 end_date_year=last_year, end_date_month=11, end_date_day=1, ended=True),
            8: self.insert_event(8, [self.artist_mbid_1], begin_date_year=last_year, begin_date_month=6, begin_date_day=1,
                                 end_date_year=last_year, end_date_month=6, end_date_day=1, ended=True, cancelled=True),
        }

    def test_get_upcoming_events_for_artists(self):
        self.assertEqual([], db_event_feed.get_upcoming_events_for_artists(self.ts_conn, []))

        self.insert_events()

        events = db_event_feed.get_upcoming_events_for_artists(self.ts_conn, [self.artist_mbid_1])
        self.assertEqual([2, 1], [e.event_id for e in events])

        events = db_event_feed.get_upcoming_events_for_artists(self.ts_conn, [self.artist_mbid_1, self.artist_mbid_2])
        self.assertEqual([2, 1, 6], [e.event_id for e in events])

        events = db_event_feed.get_upcoming_events_for_artists(self.ts_conn, [self.artist_mbid_1], limit=1)
        self.assertEqual([2], [e.event_id for e in events])

        events = db_event_feed.get_upcoming_events_for_artists(
            self.ts_conn, [self.artist_mbid_1, self.artist_mbid_2], limit=25, offset=1
        )
        self.assertEqual([1, 6], [e.event_id for e in events])

        self.assertEqual([], db_event_feed.get_upcoming_events_for_artists(self.ts_conn, [str(uuid.uuid4())]))

    def test_get_past_events_for_artists(self):
        self.assertEqual([], db_event_feed.get_past_events_for_artists(self.ts_conn, []))

        self.insert_events()

        events = db_event_feed.get_past_events_for_artists(self.ts_conn, [self.artist_mbid_1])
        self.assertEqual([7, 5], [e.event_id for e in events])

        events = db_event_feed.get_past_events_for_artists(self.ts_conn, [self.artist_mbid_1], limit=1)
        self.assertEqual([7], [e.event_id for e in events])

        events = db_event_feed.get_past_events_for_artists(self.ts_conn, [self.artist_mbid_1], limit=25, offset=1)
        self.assertEqual([5], [e.event_id for e in events])

        self.assertEqual([], db_event_feed.get_past_events_for_artists(self.ts_conn, [self.artist_mbid_2]))

    def test_get_upcoming_events_global(self):
        events, total_count = db_event_feed.get_upcoming_events_global(self.ts_conn)
        self.assertEqual([], events)
        self.assertEqual(0, total_count)

        self.insert_events()

        events, total_count = db_event_feed.get_upcoming_events_global(self.ts_conn)
        self.assertEqual(3, total_count)
        self.assertEqual([2, 1, 6], [e.event_id for e in events])

        events, total_count = db_event_feed.get_upcoming_events_global(self.ts_conn, limit=2)
        self.assertEqual(3, total_count)
        self.assertEqual([2, 1], [e.event_id for e in events])

        events, total_count = db_event_feed.get_upcoming_events_global(self.ts_conn, limit=25, offset=2)
        self.assertEqual(3, total_count)
        self.assertEqual([6], [e.event_id for e in events])

    def test_events_on_the_same_day_page_in_mbid_order(self):
        day = date.today() + timedelta(days=1)
        mbids = sorted(
            self.insert_event(event_id, [], begin_date_year=day.year, begin_date_month=day.month, begin_date_day=day.day)
            for event_id in range(1, 4)
        )

        pages = []
        for offset in range(3):
            events, _ = db_event_feed.get_upcoming_events_global(self.ts_conn, limit=1, offset=offset)
            pages.extend(str(e.event_mbid) for e in events)
        self.assertEqual(mbids, pages)

    def insert_dated_event(self, event_id, begins, ends=None, cancelled=False, artists=None):
        return self.insert_event(
            event_id, artists or [], begin_date_year=begins.year, begin_date_month=begins.month,
            begin_date_day=begins.day, end_date_year=ends.year if ends else None,
            end_date_month=ends.month if ends else None, end_date_day=ends.day if ends else None,
            ended=ends is not None, cancelled=cancelled
        )

    def insert_window_events(self):
        """ Events placed around today to exercise the window arguments.
            1: in 10 days
            2: started 3 days ago and ends in 3 days, so it overlaps every window
            3: ended 20 days ago
            4: ended 100 days ago, further back than the 90 days the API allows
            5: in 200 days
            6: cancelled, in 5 days
            7: month only, 75 days from now, so read as the 1st of that month, 45 to 75 days away
        """
        today = date.today()
        in_75_days = today + timedelta(days=75)
        self.insert_dated_event(1, today + timedelta(days=10), artists=[self.artist_mbid_1])
        self.insert_dated_event(2, today - timedelta(days=3), today + timedelta(days=3), artists=[self.artist_mbid_1])
        self.insert_dated_event(3, today - timedelta(days=20), today - timedelta(days=20), artists=[self.artist_mbid_1])
        self.insert_dated_event(4, today - timedelta(days=100), today - timedelta(days=100))
        self.insert_dated_event(5, today + timedelta(days=200))
        self.insert_dated_event(6, today + timedelta(days=5), cancelled=True, artists=[self.artist_mbid_1])
        self.insert_event(7, [], begin_date_year=in_75_days.year, begin_date_month=in_75_days.month)

    def test_get_upcoming_events_global_window(self):
        self.insert_window_events()

        def event_ids(**kwargs):
            events, total_count = db_event_feed.get_upcoming_events_global(self.ts_conn, **kwargs)
            self.assertEqual(len(events), total_count)
            return [e.event_id for e in events]

        self.assertEqual([2, 1, 7, 5], event_ids())
        self.assertEqual([2], event_ids(days=7))
        self.assertEqual([2, 1], event_ids(days=30))
        self.assertEqual([2, 1, 7], event_ids(days=90))
        self.assertEqual([2, 1, 7, 5], event_ids(days=365))

        self.assertEqual([2], event_ids(days=7, past=True, future=False))
        self.assertEqual([3, 2], event_ids(days=30, past=True, future=False))
        self.assertEqual([4, 3, 2], event_ids(days=100, past=True, future=False))
        self.assertEqual([3, 2, 1], event_ids(days=30, past=True))
        self.assertEqual([2], event_ids(future=False))

        self.assertEqual([2, 6, 1], event_ids(days=30, cancelled=True))

    def test_get_upcoming_events_for_artists_window(self):
        self.insert_window_events()

        events = db_event_feed.get_upcoming_events_for_artists(self.ts_conn, [self.artist_mbid_1], days=30)
        self.assertEqual([2, 1], [e.event_id for e in events])

        events = db_event_feed.get_upcoming_events_for_artists(
            self.ts_conn, [self.artist_mbid_1], days=30, past=True, cancelled=True
        )
        self.assertEqual([3, 2, 6, 1], [e.event_id for e in events])

    def insert_performer(self, event_id, artist_mbid, link_id, link_type_name, credited_as=None):
        relationship_data = {"credited_as": credited_as} if credited_as else {}
        self.ts_conn.execute(text("""
            INSERT INTO mapping.mb_event_artist_cache
                        (event_mbid, event_id, artist_mbid, artist_id, link_id, link_type_gid,
                         link_type_name, relationship_data)
                 SELECT event_mbid, event_id, :artist_mbid ::UUID, 1, :link_id, gen_random_uuid(),
                        :link_type_name, :relationship_data ::JSONB
                   FROM mapping.mb_event_cache
                  WHERE event_id = :event_id
        """), {
            "event_id": event_id,
            "artist_mbid": artist_mbid,
            "link_id": link_id,
            "link_type_name": link_type_name,
            "relationship_data": json.dumps(relationship_data),
        })

    def insert_artist(self, artist_mbid, name, tags, listen_count=None):
        self.ts_conn.execute(text("""
            INSERT INTO mapping.mb_artist_metadata_cache (dirty, artist_mbid, artist_data, tag_data, release_group_data)
                 VALUES (false, :artist_mbid ::UUID, :artist_data, :tag_data, '[]')
        """), {
            "artist_mbid": artist_mbid,
            "artist_data": json.dumps({"name": name, "mbid": artist_mbid}),
            "tag_data": json.dumps({"artist": tags}),
        })
        if listen_count is not None:
            self.ts_conn.execute(text("""
                INSERT INTO popularity.artist (artist_mbid, total_listen_count, total_user_count)
                     VALUES (:artist_mbid ::UUID, :listen_count, 1)
            """), {"artist_mbid": artist_mbid, "listen_count": listen_count})

    def test_add_performers_to_events(self):
        headliner, support, opener = str(uuid.uuid4()), str(uuid.uuid4()), str(uuid.uuid4())
        self.insert_artist(headliner, "Headliner", [
            {"tag": "pop", "count": 2, "artist_mbid": headliner, "genre_mbid": str(uuid.uuid4())},
            {"tag": "seen live", "count": 10, "artist_mbid": headliner},
            {"tag": "rock", "count": 5, "artist_mbid": headliner, "genre_mbid": str(uuid.uuid4())},
        ], listen_count=500)
        self.insert_artist(support, "Support", [
            {"tag": "jazz", "count": 3, "artist_mbid": support, "genre_mbid": str(uuid.uuid4())},
        ], listen_count=1000)
        self.insert_artist(opener, "Opener", [])

        today = date.today()
        self.insert_dated_event(1, today)
        self.insert_performer(1, support, 1, "support act")
        self.insert_performer(1, headliner, 2, "main performer")
        self.insert_performer(1, headliner, 3, "main performer")
        self.insert_dated_event(2, today)
        self.insert_performer(2, support, 1, "support act", credited_as="Support Band")
        self.insert_performer(2, opener, 2, "support act")
        self.insert_dated_event(3, today)

        events, _ = db_event_feed.get_upcoming_events_global(self.ts_conn)
        items = {item["event_name"]: item for item in db_event_feed.add_performers_to_events(self.ts_conn, events)}

        # the headliner comes first and only once; genres and listen count come from the headliner alone
        self.assertEqual([
            {"artist_mbid": headliner, "artist_name": "Headliner", "link_type_name": "main performer"},
            {"artist_mbid": support, "artist_name": "Support", "link_type_name": "support act"},
        ], items["Event 1"]["performers"])
        self.assertEqual(["rock", "pop"], items["Event 1"]["genres"])
        self.assertEqual(500, items["Event 1"]["listen_count"])

        # with no main performer every performer counts, alphabetically, and a credited name wins over the
        # artist's own
        self.assertEqual(["Opener", "Support Band"], [p["artist_name"] for p in items["Event 2"]["performers"]])
        self.assertEqual(["jazz"], items["Event 2"]["genres"])
        self.assertEqual(1000, items["Event 2"]["listen_count"])

        self.assertEqual([], items["Event 3"]["performers"])
        self.assertEqual([], items["Event 3"]["genres"])
        self.assertEqual(0, items["Event 3"]["listen_count"])
