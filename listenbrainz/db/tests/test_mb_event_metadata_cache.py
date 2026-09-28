import datetime
import uuid
from psycopg2.extras import DictCursor

from listenbrainz.db.testing import TimescaleTestCase
from mbid_mapping.mapping.mb_event_metadata_cache import MusicBrainzEventMetadataCache
from mbid_mapping.mapping.utils import insert_rows


class TestMBEventMetadataCache(TimescaleTestCase):
    def setUp(self):
        super().setUp()
        self.cache = MusicBrainzEventMetadataCache(
            select_conn=None, insert_conn=self.ts_conn.connection
        )
        self.cache.last_updated = datetime.datetime.now(tz=datetime.timezone.utc)

    def test_process_row_comprehensive(self):
        row = {
            "area_mbid": uuid.UUID("edd27a39-ff8a-4af4-8bbf-f369b0fb1899"),
            "area_name": "Midtown Manhattan",
            "artist_edges": [
                [
                    "7cdb68bc-c4f1-4a92-9bd2-739641c5eff0",
                    41094,
                    231885,
                    "9b2d5b96-b4d9-4bce-b056-c369ced25e81",
                    "orchestra",
                    "",
                    0,
                ],
                [
                    "2eac59bd-a1ff-403a-925d-3982a8794be7",
                    436595,
                    231886,
                    "92873f0d-12a7-4fb3-9eac-ff06c38c6a60",
                    "conductor",
                    "",
                    0,
                ],
                [
                    "319e385f-bf48-4ea9-8328-1fff1b049e95",
                    915750,
                    203956,
                    "936c7c95-3156-3889-a062-8a0cd57f8946",
                    "main performer",
                    "",
                    0,
                ],
            ],
            "begin_date_day": 16,
            "begin_date_month": 12,
            "begin_date_year": 1893,
            "cancelled": False,
            "disambiguation": "",
            "end_date_day": 16,
            "end_date_month": 12,
            "end_date_year": 1893,
            "ended": True,
            "event_art_id": None,
            "event_art_presence": "present",
            "event_id": 3079,
            "event_links": [
                [
                    "official homepage",
                    "https://www.carnegiehall.org/About/History/Performance-History-Search?q=&dex=prod_PHS&page=47&event=6018",
                ],
                [
                    "official homepage",
                    "https://www.carnegiehall.org/Blog/2012/09/The-A-to-Z-of-Carnegie-Hall-N-is-for-New-World-Symphony",
                ],
                [
                    "poster",
                    "https://archives.nyphil.org/index.php/artifact/489b901d-bd34-40ce-82f2-250fb4757801-0.1/",
                ],
                [
                    "review",
                    "https://chroniclingamerica.loc.gov/lccn/sn83030272/1893-12-17/ed-1/seq-4/",
                ],
            ],
            "event_mbid": "1bfefc05-dbbb-4aaa-8d1b-6ddc00114eb7",
            "event_name": "Second Concert in the Fifty Second Season",
            "event_part_of": None,
            "event_parts": None,
            "event_series": None,
            "event_tags": [["classical", 1, "6ed4e4d1-9a97-4e2c-b8df-083754f154f4"]],
            "event_time_raw": datetime.time(20, 15),
            "event_type_gid": uuid.UUID("ef55e8d7-3d00-394a-8012-f5506a29ff0b"),
            "event_type_name": "Concert",
            "place_mbid": uuid.UUID("68b175f6-242d-40db-a376-ca0e2dd10c41"),
            "place_name": "Carnegie Hall",
            "rating": None,
            "rating_count": None,
            "setlist": (
                "@ [319e385f-bf48-4ea9-8328-1fff1b049e95|Henri Marteau] - soloist\r\n\r\n"
                "@ [0e85eb79-1c05-44ba-827c-7b259a3d941a|Felix Mendelssohn] - composer\r\n"
                "* [e2a0b12c-c31c-4802-a57d-6bc2a9266e0f|Music to Shakespeare's “Midsummer Night's Dream”] - "
                "[56f42454-be29-4a00-b1fd-4bef7ab8263c|Overture], [3ea58985-a8ca-4513-aa76-5698d4996588|Scherzo], "
                "[44883862-fed5-4063-8a2a-924a918a3ad8|Notturno]\r\n\r\n"
                "@ [c70d12a2-24fe-4f83-a6e6-57d84f8efb51|Johannes Brahms] - composer, "
                "[319e385f-bf48-4ea9-8328-1fff1b049e95|Henri Marteau] - composer of cadenza\r\n"
                "* [40215afd-f532-3cc5-8e69-db60650c526b|Concerto for Violin, D major, op. 77]\r\n\r\n"
                "@ [819eaeb2-8dd8-48a5-ad07-0bcd137985ef|Antonín Dvořák] - composer\r\n"
                "* [aacb1ab0-c740-436a-a782-ed60026cf82b|Symphony E minor, No. 5: “From the New World”] (currently known as no. 9)\r\n"
                "# first performance"
            ),
        }

        result = self.cache.process_row(row)

        event_cache_rows = result["mapping.mb_event_cache"]
        self.assertEqual(len(event_cache_rows), 1)

        artist_cache_rows = result["mapping.mb_event_artist_cache"]
        self.assertEqual(len(artist_cache_rows), 3)

        with self.ts_conn.connection.cursor(cursor_factory=DictCursor) as curs:
            insert_rows(curs, "mapping.mb_event_cache", event_cache_rows)
            insert_rows(curs, "mapping.mb_event_artist_cache", artist_cache_rows)
            self.ts_conn.connection.commit()

            curs.execute(
                "SELECT * FROM mapping.mb_event_cache WHERE event_mbid = %s",
                ("1bfefc05-dbbb-4aaa-8d1b-6ddc00114eb7",),
            )
            db_row = curs.fetchone()

            self.assertIsNotNone(db_row)
            self.assertEqual(
                db_row["event_name"], "Second Concert in the Fifty Second Season"
            )
            self.assertEqual(db_row["event_id"], 3079)
            self.assertEqual(db_row["begin_date_year"], 1893)
            self.assertEqual(
                db_row["event_time"],
                datetime.datetime(
                    1893, 12, 16, 20, 15, 0, tzinfo=datetime.timezone.utc
                ),
            )
            self.assertEqual(db_row["event_art_presence"], "present")
            self.assertEqual(
                str(db_row["event_type_gid"]), "ef55e8d7-3d00-394a-8012-f5506a29ff0b"
            )
            self.assertEqual(
                str(db_row["place_mbid"]), "68b175f6-242d-40db-a376-ca0e2dd10c41"
            )
            self.assertEqual(db_row["place_name"], "Carnegie Hall")
            self.assertEqual(
                str(db_row["area_mbid"]), "edd27a39-ff8a-4af4-8bbf-f369b0fb1899"
            )

            db_json = db_row["event_data"]
            self.assertEqual(db_json["type"], "Concert")
            self.assertEqual(db_json["area_name"], "Midtown Manhattan")
            self.assertEqual(db_json["setlist"], row["setlist"])
            self.assertEqual(db_json["tags"][0]["tag"], "classical")
            self.assertEqual(
                db_json["tags"][0]["genre_mbid"], "6ed4e4d1-9a97-4e2c-b8df-083754f154f4"
            )
            self.assertEqual(
                db_json["rels"]["poster"][0],
                "https://archives.nyphil.org/index.php/artifact/489b901d-bd34-40ce-82f2-250fb4757801-0.1/",
            )

            curs.execute(
                "SELECT * FROM mapping.mb_event_artist_cache WHERE event_mbid = %s ORDER BY artist_mbid",
                ("1bfefc05-dbbb-4aaa-8d1b-6ddc00114eb7",),
            )
            db_artist_rows = curs.fetchall()
            self.assertEqual(len(db_artist_rows), 3)
            self.assertEqual(
                str(db_artist_rows[0]["artist_mbid"]),
                "2eac59bd-a1ff-403a-925d-3982a8794be7",
            )
            self.assertEqual(db_artist_rows[0]["link_type_name"], "conductor")

    def test_process_row_parts(self):
        row = {
            "area_mbid": uuid.UUID("b9576171-3434-4d1b-8883-165ed6e65d2f"),
            "area_name": "Kensington and Chelsea",
            "artist_edges": None,
            "begin_date_day": 14,
            "begin_date_month": 7,
            "begin_date_year": 2000,
            "cancelled": False,
            "disambiguation": "",
            "end_date_day": 9,
            "end_date_month": 9,
            "end_date_year": 2000,
            "ended": True,
            "event_art_id": None,
            "event_art_presence": "absent",
            "event_id": 2624,
            "event_links": None,
            "event_mbid": "4ff6bf2a-ff96-405c-ae4d-b79c2373c775",
            "event_name": "The Proms 2000",
            "event_part_of": [
                ["f5222627-58e6-4883-a189-f5ea486b61c6", "Woodstock \u201994"]
            ],
            "event_parts": [
                ["82acd8f8-afa4-45cd-b669-c08a2abd58fc", "2000 BBC Prom 08"],
                ["a37015fc-035a-4de7-9c5e-dd7707b54ec5", "The Proms 2000: Prom 07"],
                [
                    "0a5a3441-bb4b-4a83-813c-c79be0428ae1",
                    "Prom 72: Last Night of the Proms",
                ],
            ],
            "event_series": [["02c9a5b9-6b2c-461e-953d-6d4f6a9cc2d2", "The Proms"]],
            "event_tags": None,
            "event_time_raw": None,
            "event_type_gid": uuid.UUID("b6ded574-b592-3f0e-b56e-5b5f06aa0678"),
            "event_type_name": "Festival",
            "place_mbid": uuid.UUID("4352063b-a833-421b-a420-e7fb295dece0"),
            "place_name": "Royal Albert Hall",
            "rating": None,
            "rating_count": None,
            "setlist": "",
        }

        result = self.cache.process_row(row)

        event_cache_rows = result["mapping.mb_event_cache"]

        with self.ts_conn.connection.cursor(cursor_factory=DictCursor) as curs:
            insert_rows(curs, "mapping.mb_event_cache", event_cache_rows)
            self.ts_conn.connection.commit()

            curs.execute(
                "SELECT * FROM mapping.mb_event_cache WHERE event_mbid = %s",
                ("4ff6bf2a-ff96-405c-ae4d-b79c2373c775",),
            )
            db_row = curs.fetchone()

            self.assertIsNotNone(db_row)
            self.assertEqual(db_row["event_name"], "The Proms 2000")
            self.assertEqual(
                str(db_row["event_type_gid"]), "b6ded574-b592-3f0e-b56e-5b5f06aa0678"
            )
            self.assertEqual(
                str(db_row["place_mbid"]), "4352063b-a833-421b-a420-e7fb295dece0"
            )
            self.assertEqual(db_row["event_art_presence"], "absent")

            db_json = db_row["event_data"]
            self.assertEqual(len(db_json["parts"]), 3)
            self.assertEqual(
                db_json["parts"][0]["mbid"], "82acd8f8-afa4-45cd-b669-c08a2abd58fc"
            )
            self.assertEqual(db_json["parts"][0]["name"], "2000 BBC Prom 08")

            self.assertEqual(
                db_json["series"][0]["mbid"], "02c9a5b9-6b2c-461e-953d-6d4f6a9cc2d2"
            )
            self.assertEqual(db_json["series"][0]["name"], "The Proms")

            self.assertEqual(
                db_json["part_of"][0]["mbid"], "f5222627-58e6-4883-a189-f5ea486b61c6"
            )
            self.assertEqual(db_json["part_of"][0]["name"], "Woodstock \u201994")

    def test_process_row_tags_ratings(self):
        row = {
            "area_mbid": None,
            "area_name": None,
            "artist_edges": [
                [
                    "7216002f-aacb-4f95-8e1d-41214bcf53f2",
                    2509642,
                    203031,
                    "936c7c95-3156-3889-a062-8a0cd57f8946",
                    "main performer",
                    "",
                    0,
                ],
                [
                    "e30933ad-7cf3-4807-9019-caa525a60a92",
                    2390453,
                    1076385,
                    "936c7c95-3156-3889-a062-8a0cd57f8946",
                    "main performer",
                    "",
                    0,
                ],
            ],
            "begin_date_day": 4,
            "begin_date_month": 2,
            "begin_date_year": 2024,
            "cancelled": False,
            "disambiguation": "",
            "end_date_day": 5,
            "end_date_month": 2,
            "end_date_year": 2024,
            "ended": True,
            "event_art_id": None,
            "event_art_presence": "present",
            "event_id": 78992,
            "event_links": None,
            "event_mbid": "9c81bb52-87be-48d5-a7cb-da91f6c94b5e",
            "event_name": "TSUNGEDDON",
            "event_part_of": None,
            "event_parts": None,
            "event_series": None,
            "event_tags": [
                ["hardcore techno", 1, "3308d0b0-3c7f-45e2-b835-5c2a0d433f02"],
                ["broadcast", 1, None],
                ["virtual event", 1, None],
            ],
            "event_time_raw": datetime.time(6, 45),
            "event_type_gid": None,
            "event_type_name": None,
            "place_mbid": None,
            "place_name": None,
            "rating": 100,
            "rating_count": 1,
            "setlist": "",
        }

        result = self.cache.process_row(row)

        event_cache_rows = result["mapping.mb_event_cache"]
        artist_cache_rows = result["mapping.mb_event_artist_cache"]

        with self.ts_conn.connection.cursor(cursor_factory=DictCursor) as curs:
            insert_rows(curs, "mapping.mb_event_cache", event_cache_rows)
            insert_rows(curs, "mapping.mb_event_artist_cache", artist_cache_rows)
            self.ts_conn.connection.commit()

            curs.execute(
                "SELECT * FROM mapping.mb_event_cache WHERE event_mbid = %s",
                ("9c81bb52-87be-48d5-a7cb-da91f6c94b5e",),
            )
            db_row = curs.fetchone()

            self.assertIsNotNone(db_row)
            self.assertEqual(db_row["event_name"], "TSUNGEDDON")
            self.assertEqual(
                db_row["event_time"],
                datetime.datetime(2024, 2, 4, 6, 45, 0, tzinfo=datetime.timezone.utc),
            )

            self.assertIsNone(db_row["event_type_gid"])
            self.assertIsNone(db_row["place_mbid"])
            self.assertIsNone(db_row["place_name"])
            self.assertIsNone(db_row["area_mbid"])

            self.assertEqual(db_row["rating"], 100)
            self.assertEqual(db_row["rating_count"], 1)
            self.assertEqual(db_row["event_art_presence"], "present")

            db_json = db_row["event_data"]
            self.assertNotIn("type", db_json)
            self.assertNotIn("area_name", db_json)

            self.assertEqual(len(db_json["tags"]), 3)
            self.assertEqual(db_json["tags"][0]["tag"], "hardcore techno")
            self.assertEqual(
                db_json["tags"][0]["genre_mbid"], "3308d0b0-3c7f-45e2-b835-5c2a0d433f02"
            )

            self.assertEqual(db_json["tags"][1]["tag"], "broadcast")
            self.assertNotIn("genre_mbid", db_json["tags"][1])
