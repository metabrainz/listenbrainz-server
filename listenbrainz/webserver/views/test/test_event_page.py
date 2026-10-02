import json
import uuid

from sqlalchemy import text

import listenbrainz.db.event_interaction as db_event_interaction
import listenbrainz.db.user as db_user
from listenbrainz.db.testing import TimescaleTestCase
from listenbrainz.tests.integration import IntegrationTestCase


class EventPageTestCase(IntegrationTestCase, TimescaleTestCase):

    def setUp(self):
        IntegrationTestCase.setUp(self)
        TimescaleTestCase.setUp(self)
        self.event_mbid = str(uuid.uuid4())

    def tearDown(self):
        IntegrationTestCase.tearDown(self)
        TimescaleTestCase.tearDown(self)

    def insert_event(self, event_mbid, event_id, **fields):
        self.ts_conn.execute(text("""
            INSERT INTO mapping.mb_event_cache
                        (event_mbid, event_id, event_name, begin_date_year, begin_date_month, begin_date_day,
                         cancelled, ended, place_name, event_data)
                 VALUES (:event_mbid ::UUID, :event_id, :event_name, :begin_date_year, :begin_date_month,
                         :begin_date_day, false, false, :place_name, :event_data)
        """), {
            "event_mbid": event_mbid,
            "event_id": event_id,
            "event_name": fields.get("event_name", "Test Concert"),
            "begin_date_year": fields.get("begin_date_year", 2027),
            "begin_date_month": fields.get("begin_date_month", 1),
            "begin_date_day": fields.get("begin_date_day", 16),
            "place_name": fields.get("place_name"),
            "event_data": json.dumps(fields.get("event_data", {})),
        })
        self.ts_conn.commit()

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
        self.ts_conn.commit()

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
        self.ts_conn.commit()

    def test_event_page(self):
        self.insert_event(
            self.event_mbid, 1, place_name="Worthy Farm", event_data={"type": "Festival", "area_name": "Pilton"}
        )
        resp = self.client.get(self.custom_url_for("event.event_page", event_mbid=self.event_mbid))
        self.assert200(resp)
        self.assertIn('<meta property="og:title" content="Test Concert" />', resp.text)
        self.assertIn("Festival — 2027-01-16 — Worthy Farm, Pilton — ListenBrainz", resp.text)

    def test_event_page_unknown_event(self):
        resp = self.client.get(self.custom_url_for("event.event_page", event_mbid=self.event_mbid))
        self.assert200(resp)
        self.assertIn('<meta property="og:title" content="ListenBrainz" />', resp.text)

    def test_event_entity_invalid_mbid(self):
        resp = self.client.post(self.custom_url_for("event.event_entity", event_mbid="not-a-uuid"))
        self.assert400(resp)

    def test_event_entity_not_found(self):
        resp = self.client.post(self.custom_url_for("event.event_entity", event_mbid=self.event_mbid))
        self.assert404(resp)

    def test_event_entity(self):
        headliner, support = str(uuid.uuid4()), str(uuid.uuid4())
        self.insert_artist(headliner, "Headliner", [
            {"tag": "rock", "count": 5, "artist_mbid": headliner, "genre_mbid": str(uuid.uuid4())},
            {"tag": "seen live", "count": 10, "artist_mbid": headliner},
        ], listen_count=500)
        self.insert_artist(support, "Support", [])

        festival_mbid, other_stage_mbid, matinee_mbid = str(uuid.uuid4()), str(uuid.uuid4()), str(uuid.uuid4())
        series = [{"mbid": str(uuid.uuid4()), "name": "The Tour"}]
        part_of = [{"mbid": festival_mbid, "name": "The Festival"}]
        self.insert_event(festival_mbid, 2, event_name="The Festival", event_data={
            "parts": [{"mbid": self.event_mbid, "name": "Test Concert"}, {"mbid": other_stage_mbid, "name": "Other Stage"}],
        })
        self.insert_event(other_stage_mbid, 3, event_name="Other Stage", event_data={"part_of": part_of})
        self.insert_event(matinee_mbid, 4, event_name="Matinee", event_data={"part_of": [
            {"mbid": self.event_mbid, "name": "Test Concert"},
        ]})
        self.insert_event(self.event_mbid, 1, event_data={
            "tags": [{"tag": "rock", "count": 2}],
            "rels": {"ticketing": ["https://tickets.example.org/"]},
            "setlist": "* Opening Track",
            "series": series,
            "parts": [{"mbid": matinee_mbid, "name": "Matinee"}],
            "part_of": part_of,
        })
        self.insert_performer(1, headliner, 1, "main performer")
        self.insert_performer(1, support, 2, "support act", credited_as="Support Band")
        self.insert_performer(4, headliner, 3, "main performer")

        watcher = db_user.get_or_create(self.db_conn, 1, "watcher")
        db_event_interaction.watch_event(self.db_conn, watcher["id"], self.event_mbid)

        resp = self.client.post(self.custom_url_for("event.event_entity", event_mbid=self.event_mbid))
        self.assert200(resp)
        data = resp.json

        event = data["event"]
        self.assertEqual(event["event_mbid"], self.event_mbid)
        self.assertEqual(event["event_name"], "Test Concert")
        self.assertEqual(event["tag"], [{"tag": "rock", "count": 2}])
        self.assertEqual(event["rels"], {"ticketing": ["https://tickets.example.org/"]})
        self.assertEqual(event["setlist"], "* Opening Track")
        self.assertEqual(event["series"], series)
        self.assertEqual(event["part_of"], part_of)

        self.assertCountEqual(data["performers"], [
            {
                "artist_mbid": headliner,
                "artist_name": "Headliner",
                "link_type_name": "main performer",
                "genres": ["rock"],
                "listen_count": 500,
            },
            {
                "artist_mbid": support,
                "artist_name": "Support Band",
                "link_type_name": "support act",
                "genres": [],
                "listen_count": 0,
            },
        ])

        self.assertEqual([part["event_mbid"] for part in data["parts"]], [matinee_mbid])
        self.assertEqual(data["parts"][0]["performers"][0]["artist_name"], "Headliner")

        self.assertEqual(list(data["otherParts"]), [festival_mbid])
        self.assertEqual([part["event_mbid"] for part in data["otherParts"][festival_mbid]], [other_stage_mbid])

        self.assertEqual(data["watchersCount"], 1)

    def test_event_entity_without_relationships(self):
        self.insert_event(self.event_mbid, 1)
        resp = self.client.post(self.custom_url_for("event.event_entity", event_mbid=self.event_mbid))
        self.assert200(resp)
        data = resp.json
        self.assertEqual(data["event"]["tag"], [])
        self.assertEqual(data["event"]["rels"], {})
        self.assertIsNone(data["event"]["setlist"])
        self.assertEqual(data["event"]["series"], [])
        self.assertEqual(data["event"]["part_of"], [])
        self.assertEqual(data["performers"], [])
        self.assertEqual(data["parts"], [])
        self.assertEqual(data["otherParts"], {})
        self.assertEqual(data["watchersCount"], 0)
