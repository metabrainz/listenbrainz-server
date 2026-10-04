import json
import uuid
from datetime import datetime, timezone

from sqlalchemy import text

from listenbrainz.db.testing import TimescaleTestCase
from listenbrainz.tests.integration import IntegrationTestCase


class MetadataEventTestCase(IntegrationTestCase, TimescaleTestCase):

    def setUp(self):
        IntegrationTestCase.setUp(self)
        TimescaleTestCase.setUp(self)
        self.event_mbid = str(uuid.uuid4())
        self.artist_mbid = str(uuid.uuid4())

    def tearDown(self):
        IntegrationTestCase.tearDown(self)
        TimescaleTestCase.tearDown(self)

    def insert_event(self, event_mbid, event_id=1, artists=(), **fields):
        self.ts_conn.execute(text("""
            INSERT INTO mapping.mb_event_cache
                        (event_mbid, event_id, event_name, begin_date_year, begin_date_month, begin_date_day,
                         event_time, cancelled, ended, event_type_gid, place_mbid, place_name, area_mbid,
                         rating, rating_count, event_data)
                 VALUES (:event_mbid ::UUID, :event_id, :event_name, :begin_date_year, :begin_date_month,
                         :begin_date_day, :event_time, false, false, :event_type_gid ::UUID, :place_mbid ::UUID,
                         :place_name, :area_mbid ::UUID, :rating, :rating_count, :event_data)
        """), {
            "event_mbid": event_mbid,
            "event_id": event_id,
            "event_name": fields.get("event_name", "Test Concert"),
            "begin_date_year": fields.get("begin_date_year", 2027),
            "begin_date_month": fields.get("begin_date_month", 1),
            "begin_date_day": fields.get("begin_date_day", 16),
            "event_time": fields.get("event_time"),
            "event_type_gid": fields.get("event_type_gid"),
            "place_mbid": fields.get("place_mbid"),
            "place_name": fields.get("place_name"),
            "area_mbid": fields.get("area_mbid"),
            "rating": fields.get("rating"),
            "rating_count": fields.get("rating_count"),
            "event_data": json.dumps(fields.get("event_data", {})),
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
        self.ts_conn.commit()

    def test_event_metadata_no_mbids(self):
        resp = self.client.get(self.custom_url_for("metadata.metadata_event"))
        self.assert400(resp)

    def test_event_metadata_invalid_mbid(self):
        resp = self.client.get(
            self.custom_url_for("metadata.metadata_event", event_mbids="not-a-uuid")
        )
        self.assert400(resp)

    def test_event_metadata_invalid_inc(self):
        resp = self.client.get(
            self.custom_url_for("metadata.metadata_event",
                                event_mbids=self.event_mbid, inc="release")
        )
        self.assert400(resp)

    def test_event_metadata(self):
        place_mbid = str(uuid.uuid4())
        area_mbid = str(uuid.uuid4())
        event_type_gid = str(uuid.uuid4())
        self.insert_event(
            self.event_mbid,
            event_time=datetime(2027, 1, 16, 20, 15, tzinfo=timezone.utc),
            event_type_gid=event_type_gid,
            place_mbid=place_mbid,
            place_name="Carnegie Hall",
            area_mbid=area_mbid,
            rating=80,
            rating_count=3,
        )
        resp = self.client.get(
            self.custom_url_for("metadata.metadata_event", event_mbids=self.event_mbid)
        )
        self.assert200(resp)
        entry = resp.json[self.event_mbid]
        self.assertEqual(entry["event_name"], "Test Concert")
        self.assertEqual(entry["begin_date_year"], 2027)
        self.assertEqual(entry["begin_date_month"], 1)
        self.assertEqual(entry["begin_date_day"], 16)
        self.assertEqual(entry["event_time"], "2027-01-16T20:15:00")
        self.assertFalse(entry["cancelled"])
        self.assertEqual(entry["event_art_presence"], "absent")
        self.assertEqual(entry["rating"], 80)
        self.assertEqual(entry["rating_count"], 3)
        self.assertEqual(entry["event_type_gid"], event_type_gid)
        self.assertEqual(entry["place_mbid"], place_mbid)
        self.assertEqual(entry["place_name"], "Carnegie Hall")
        self.assertEqual(entry["area_mbid"], area_mbid)
        self.assertNotIn("artist", entry)
        self.assertNotIn("tag", entry)

    def test_event_metadata_optional_identifiers_omitted(self):
        self.insert_event(self.event_mbid)
        resp = self.client.get(
            self.custom_url_for("metadata.metadata_event", event_mbids=self.event_mbid)
        )
        self.assert200(resp)
        entry = resp.json[self.event_mbid]
        self.assertNotIn("event_type_gid", entry)
        self.assertNotIn("place_mbid", entry)
        self.assertNotIn("place_name", entry)
        self.assertNotIn("area_mbid", entry)
        self.assertIsNone(entry["rating"])

    def test_event_metadata_unknown_mbid(self):
        unknown_mbid = str(uuid.uuid4())
        self.insert_event(self.event_mbid)
        resp = self.client.get(
            self.custom_url_for("metadata.metadata_event",
                                event_mbids="%s,%s" % (self.event_mbid, unknown_mbid))
        )
        self.assert200(resp)
        self.assertIn(self.event_mbid, resp.json)
        self.assertNotIn(unknown_mbid, resp.json)

    def test_event_metadata_multiple_mbids(self):
        second_mbid = str(uuid.uuid4())
        self.insert_event(self.event_mbid)
        self.insert_event(second_mbid, event_id=2, event_name="Other Concert")
        resp = self.client.get(
            self.custom_url_for("metadata.metadata_event",
                                event_mbids="%s,%s" % (self.event_mbid, second_mbid))
        )
        self.assert200(resp)
        self.assertEqual(resp.json[self.event_mbid]["event_name"], "Test Concert")
        self.assertEqual(resp.json[second_mbid]["event_name"], "Other Concert")

    def test_event_metadata_with_inc_artist(self):
        self.insert_event(self.event_mbid, artists=[self.artist_mbid])
        resp = self.client.get(
            self.custom_url_for("metadata.metadata_event",
                                event_mbids=self.event_mbid, inc="artist")
        )
        self.assert200(resp)
        performers = resp.json[self.event_mbid]["artist"]
        self.assertEqual(1, len(performers))
        self.assertEqual(performers[0]["artist_mbid"], self.artist_mbid)
        self.assertEqual(performers[0]["link_type_name"], "main performer")

    def test_event_metadata_with_inc_artist_no_performers(self):
        self.insert_event(self.event_mbid)
        resp = self.client.get(
            self.custom_url_for("metadata.metadata_event",
                                event_mbids=self.event_mbid, inc="artist")
        )
        self.assert200(resp)
        self.assertEqual(resp.json[self.event_mbid]["artist"], [])

    def test_event_metadata_with_inc_tag(self):
        self.insert_event(self.event_mbid, event_data={"tags": [{"tag": "rock", "count": 3}]})
        resp = self.client.get(
            self.custom_url_for("metadata.metadata_event",
                                event_mbids=self.event_mbid, inc="tag")
        )
        self.assert200(resp)
        self.assertEqual(resp.json[self.event_mbid]["tag"][0]["tag"], "rock")

    def test_event_metadata_with_inc_setlist(self):
        self.insert_event(
            self.event_mbid,
            event_data={"setlist": "1. Opening Track\n2. Fan Favourite"},
        )
        resp = self.client.get(
            self.custom_url_for("metadata.metadata_event",
                                event_mbids=self.event_mbid, inc="setlist")
        )
        self.assert200(resp)
        self.assertIn("Opening Track", resp.json[self.event_mbid]["setlist"])

    def test_event_metadata_with_multiple_incs(self):
        place_mbid = str(uuid.uuid4())
        area_mbid = str(uuid.uuid4())
        self.insert_event(
            self.event_mbid,
            place_mbid=place_mbid,
            place_name="Carnegie Hall",
            area_mbid=area_mbid,
            event_data={
                "area_name": "Midtown Manhattan",
                "series": [{"name": "The Fifty Second Season"}],
                "rels": {"official homepage": ["https://www.carnegiehall.org/"]},
            },
        )
        resp = self.client.get(
            self.custom_url_for("metadata.metadata_event",
                                event_mbids=self.event_mbid, inc="place series rels")
        )
        self.assert200(resp)
        entry = resp.json[self.event_mbid]
        self.assertEqual(entry["place"], {
            "place_mbid": place_mbid,
            "place_name": "Carnegie Hall",
            "area_mbid": area_mbid,
            "area_name": "Midtown Manhattan",
        })
        self.assertEqual(entry["series"][0]["name"], "The Fifty Second Season")
        self.assertEqual(entry["rels"]["official homepage"], ["https://www.carnegiehall.org/"])
