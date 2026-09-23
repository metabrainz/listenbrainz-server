import json
import uuid
from datetime import datetime, timezone

from sqlalchemy import text

import listenbrainz.db.event as db_event
from listenbrainz.db.model.event import EventMetadata
from listenbrainz.db.testing import TimescaleTestCase
from listenbrainz.webserver.views.api_tools import MAX_ITEMS_PER_GET


class EventDBTestCase(TimescaleTestCase):

    def setUp(self):
        super().setUp()
        self.artist_mbid_1 = str(uuid.uuid4())
        self.artist_mbid_2 = str(uuid.uuid4())

    def insert_event(self, event, artists=()):
        self.ts_conn.execute(text("""
            INSERT INTO mapping.mb_event_cache
                        (event_mbid, event_id, event_name, begin_date_year, begin_date_month, begin_date_day,
                         event_time, cancelled, ended, event_type_gid, place_mbid, place_name, area_mbid,
                         rating, rating_count, event_data)
                 VALUES (:event_mbid ::UUID, :event_id, :event_name, :begin_date_year, :begin_date_month, :begin_date_day,
                         :event_time, :cancelled, :ended, :event_type_gid ::UUID, :place_mbid ::UUID, :place_name,
                         :area_mbid ::UUID, :rating, :rating_count, :event_data)
        """), {
            "event_mbid": event["event_mbid"],
            "event_id": event["event_id"],
            "event_name": event["event_name"],
            "begin_date_year": event.get("begin_date_year"),
            "begin_date_month": event.get("begin_date_month"),
            "begin_date_day": event.get("begin_date_day"),
            "event_time": event.get("event_time"),
            "cancelled": event.get("cancelled", False),
            "ended": event.get("ended", False),
            "event_type_gid": event.get("event_type_gid"),
            "place_mbid": event.get("place_mbid"),
            "place_name": event.get("place_name"),
            "area_mbid": event.get("area_mbid"),
            "rating": event.get("rating"),
            "rating_count": event.get("rating_count"),
            "event_data": json.dumps(event.get("event_data", {})),
        })
        for link_id, (artist_mbid, link_type_name, relationship_data) in enumerate(artists, start=1):
            self.ts_conn.execute(text("""
                INSERT INTO mapping.mb_event_artist_cache
                            (event_mbid, event_id, artist_mbid, artist_id, link_id, link_type_gid,
                             link_type_name, relationship_data)
                     VALUES (:event_mbid ::UUID, :event_id, :artist_mbid ::UUID, 1, :link_id, gen_random_uuid(),
                             :link_type_name, :relationship_data)
            """), {
                "event_mbid": event["event_mbid"],
                "event_id": event["event_id"],
                "artist_mbid": artist_mbid,
                "link_id": link_id,
                "link_type_name": link_type_name,
                "relationship_data": json.dumps(relationship_data),
            })

    def insert_events(self):
        events = [
            {
                "event_mbid": "1bfefc05-dbbb-4aaa-8d1b-6ddc00114eb7",
                "event_id": 1,
                "event_name": "Second Concert in the Fifty Second Season",
                "begin_date_year": 2027,
                "begin_date_month": 1,
                "begin_date_day": 16,
                "event_time": datetime(2027, 1, 16, 20, 15, tzinfo=timezone.utc),
                "event_type_gid": "ef55e8d7-3d00-394a-8012-f5506a29ff0b",
                "place_mbid": "68b175f6-242d-40db-a376-ca0e2dd10c41",
                "place_name": "Carnegie Hall",
                "area_mbid": "edd27a39-ff8a-4af4-8bbf-f369b0fb1899",
                "rating": 80,
                "rating_count": 3,
                "event_data": {
                    "type": "Concert",
                    "area_name": "Midtown Manhattan",
                    "rels": {"official homepage": ["https://www.carnegiehall.org/"]},
                },
            },
            {
                "event_mbid": "9c81bb52-87be-48d5-a7cb-da91f6c94b5e",
                "event_id": 2,
                "event_name": "Unscheduled Jam",
            },
            {
                "event_mbid": "a777f05b-a934-4648-9a5c-60284b588c0e",
                "event_id": 3,
                "event_name": "Cancelled Show",
                "cancelled": True,
            },
        ]
        self.insert_event(events[0], artists=[
            (self.artist_mbid_1, "main performer", {}),
            (self.artist_mbid_2, "support act", {}),
        ])
        self.insert_event(events[1], artists=[
            (self.artist_mbid_1, "main performer", {"credited_as": "The Band"}),
            (self.artist_mbid_1, "conductor", {}),
        ])
        self.insert_event(events[2])
        return events

    def test_get_metadata_for_event(self):
        events = self.insert_events()
        unknown_mbid = str(uuid.uuid4())

        received = db_event.get_metadata_for_event(
            self.ts_conn, [events[1]["event_mbid"], events[0]["event_mbid"], unknown_mbid]
        )
        self.assertEqual(2, len(received))
        self.assertIsInstance(received[0], EventMetadata)
        # results are sorted by event_mbid, not by request order
        self.assertEqual(str(received[0].event_mbid), events[0]["event_mbid"])
        self.assertEqual(str(received[1].event_mbid), events[1]["event_mbid"])

        full = received[0]
        self.assertEqual(full.event_id, 1)
        self.assertEqual(full.event_name, "Second Concert in the Fifty Second Season")
        self.assertEqual(full.begin_date_year, 2027)
        self.assertEqual(full.begin_date_month, 1)
        self.assertEqual(full.begin_date_day, 16)
        self.assertEqual(full.event_time, datetime(2027, 1, 16, 20, 15, tzinfo=timezone.utc))
        self.assertFalse(full.cancelled)
        self.assertEqual(str(full.event_type_gid), "ef55e8d7-3d00-394a-8012-f5506a29ff0b")
        self.assertEqual(str(full.place_mbid), "68b175f6-242d-40db-a376-ca0e2dd10c41")
        self.assertEqual(full.place_name, "Carnegie Hall")
        self.assertEqual(str(full.area_mbid), "edd27a39-ff8a-4af4-8bbf-f369b0fb1899")
        self.assertEqual(full.rating, 80)
        self.assertEqual(full.rating_count, 3)
        self.assertEqual(full.event_data, events[0]["event_data"])

        sparse = received[1]
        self.assertEqual(sparse.event_name, "Unscheduled Jam")
        self.assertIsNone(sparse.begin_date_year)
        self.assertIsNone(sparse.event_time)
        self.assertIsNone(sparse.event_type_gid)
        self.assertIsNone(sparse.place_mbid)
        self.assertIsNone(sparse.place_name)
        self.assertIsNone(sparse.area_mbid)
        self.assertIsNone(sparse.rating)
        self.assertEqual(sparse.event_art_presence, "absent")
        self.assertEqual(sparse.event_data, {})

    def test_get_metadata_for_event_too_many_mbids(self):
        too_many = [str(uuid.uuid4()) for _ in range(MAX_ITEMS_PER_GET + 1)]
        with self.assertRaises(ValueError):
            db_event.get_metadata_for_event(self.ts_conn, too_many)

    def test_get_artists_for_events(self):
        self.assertEqual({}, db_event.get_artists_for_events(self.ts_conn, []))

        self.insert_events()
        received = db_event.get_artists_for_events(self.ts_conn, [1, 2, 3])

        # event 3 has no performers so it is absent rather than mapped to []
        self.assertSetEqual({1, 2}, set(received.keys()))

        # order within an event is unspecified, so compare as a set
        self.assertSetEqual(
            {(self.artist_mbid_1, "main performer"), (self.artist_mbid_2, "support act")},
            {(row["artist_mbid"], row["link_type_name"]) for row in received[1]},
        )
        for row in received[1]:
            self.assertIsInstance(row["artist_mbid"], str)
            self.assertEqual({}, row["relationship_data"])

        # the same artist linked twice to one event yields two entries
        self.assertEqual(2, len(received[2]))
        credited = next(row for row in received[2] if row["link_type_name"] == "main performer")
        self.assertEqual({"credited_as": "The Band"}, credited["relationship_data"])
