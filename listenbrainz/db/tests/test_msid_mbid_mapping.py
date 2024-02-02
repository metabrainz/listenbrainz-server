import json
import uuid

from psycopg2.extras import DictCursor
from sqlalchemy import text

from listenbrainz import messybrainz
from listenbrainz.db.msid_mbid_mapping import fetch_track_metadata_for_items, MsidMbidModel, load_recordings_from_mbids
from listenbrainz.db.testing import TimescaleTestCase


class MappingTestCase(TimescaleTestCase):

    def test_msid_mbid_model(self):
        with self.assertRaisesRegex(ValueError, 'at least one of recording_msid or recording_mbid should be specified'):
            model = MsidMbidModel(recording_mbid=None, recording_msid=None)

        with self.assertRaisesRegex(ValueError, "(?s)recording_msid.*must be a valid UUID"):
            model = MsidMbidModel(recording_msid='', recording_mbid=str(uuid.uuid4()))

        with self.assertRaisesRegex(ValueError, "(?s)recording_mbid.*must be a valid UUID"):
            model = MsidMbidModel(recording_msid=str(uuid.uuid4()), recording_mbid='')

        # test that 2 valid uuids doesn't raise error
        model = MsidMbidModel(recording_msid=str(uuid.uuid4()), recording_mbid=str(uuid.uuid4()))

    def insert_recording_in_mapping(self, recording, match_type):
        if match_type == "exact_match":

            release_data = {"name": recording["release"]}
            if recording.get("caa_id"):
                release_data["caa_id"] = recording["caa_id"]
                release_data["caa_release_mbid"] = recording["caa_release_mbid"]

            artists = [
                {"name": a["artist_credit_name"], "join_phrase": a["join_phrase"]}
                for a in recording["artists"]
            ]
            artist_data = {"name": recording["artist"], "artists": artists}

            self.ts_conn.execute(text("""
                INSERT INTO mapping.mb_metadata_cache
                        (recording_mbid, artist_mbids, release_mbid, recording_data, artist_data, tag_data, release_data, dirty)
                 VALUES (:recording_mbid ::UUID, :artist_mbids ::UUID[], :release_mbid ::UUID, :recording_data, :artist_data, :tag_data, :release_data, 'f')
            """), {
                "recording_mbid": recording["recording_mbid"],
                "artist_mbids": recording["artist_mbids"],
                "release_mbid": recording["release_mbid"],
                "recording_data": json.dumps({"name": recording["title"]}),
                "artist_data": json.dumps(artist_data),
                "release_data": json.dumps(release_data),
                "tag_data": json.dumps({"artist": [], "recording": [], "release_group": []})
            })

        self.ts_conn.execute(
            text("""
            INSERT INTO mbid_mapping (recording_msid, recording_mbid, match_type)
                              VALUES (:recording_msid, :recording_mbid, :match_type)
        """),
            {
                "recording_msid": recording["recording_msid"],
                "recording_mbid": recording["recording_mbid"],
                "match_type": match_type
            }
        )

    def insert_recordings(self):
        recordings = [
            {
                "recording_mbid": "00000737-3a59-4499-b30a-31fe2464555d",
                "release_mbid": "a2589025-8517-45ab-9d64-fe927ba087b1",
                "release": "Batman Returns",
                "artist_mbids": ["5b24fbab-c58f-4c37-a59d-ab232e2d98c4"],
                "artist": "Danny Elfman",
                "artists": [
                    {
                        "artist_credit_name": "Danny Elfman",
                        "join_phrase": "",
                        "artist_mbid": "5b24fbab-c58f-4c37-a59d-ab232e2d98c4"
                    }
                ],
                "title": "The Final Confrontation, Part 1",
                "caa_release_mbid": "a2589025-8517-45ab-9d64-fe927ba087b1-3151246737",
                "caa_id": 3151246737,
                "length": None,
                "artist_credit_id": None,
            },
            {
                "recording_mbid": "c5bfd98d-ccde-4cf3-8abb-63fad1b6065a",
                "release_mbid": "5da4af04-d796-4d07-801d-a878e83dea48",
                "release": "Random Is Resistance",
                "artist_mbids": ["797bcf41-0e02-431d-ab99-020e1cb3d0fd"],
                "artist": "Rotersand",
                "artists": [
                    {
                        "artist_credit_name": "Rotersand",
                        "join_phrase": "",
                        "artist_mbid": "797bcf41-0e02-431d-ab99-020e1cb3d0fd"
                    }
                ],
                "title": "A Number and a Name",
                "caa_id": None,
                "caa_release_mbid": None,
                "length": None,
                "artist_credit_id": None,
            },
            {
                "artist": "James S.A. Corey",
                "title": "The Churn",
                "release": None
            },
            {
                "recording_mbid": "67bcde07-bfb1-4b30-88ba-6b995ec04123",
                "release_mbid": "27280632-fa33-3801-a5b1-081ed0b65bb3",
                "release": "Year Zero",
                "artist_mbids": ["b7ffd2af-418f-4be2-bdd1-22f8b48613da"],
                "artist": "Nine Inch Nails",
                "artists": [
                    {
                        "artist_credit_name": "Nine Inch Nails",
                        "join_phrase": "",
                        "artist_mbid": "b7ffd2af-418f-4be2-bdd1-22f8b48613da"
                    }
                ],
                "title": "The Warning"
            },
            {
                "artist": "Thanks for the Advice",
                "title": "Repairs",
                "release": None
            }
        ]
        submitted = messybrainz.insert_all_in_transaction(self.ts_conn, recordings)
        # data sent to msb cannot contain nulls but we want it when inserting in mapping
        recordings[2].update(**{
            "recording_mbid": None,
            "release_mbid": None,
            "release": None,
            "artist_mbids": None,
        })
        recordings[4].update(**{
            "recording_mbid": None,
            "release_mbid": None,
            "release": None,
            "artist_mbids": None,
        })
        for idx in range(5):
            recordings[idx]["recording_msid"] = submitted[idx]
            if idx == 2 or idx == 4:
                match_type = "no_match"
            else:
                match_type = "exact_match"
            self.insert_recording_in_mapping(recordings[idx], match_type)
        return recordings

    def test_load_recordings_from_mapping(self):
        recordings = self.insert_recordings()
        del recordings[0]["recording_msid"]
        del recordings[1]["recording_msid"]
        expected = {
            recordings[0]["recording_mbid"]: recordings[0],
            recordings[1]["recording_mbid"]: recordings[1]
        }
        with self.ts_conn.connection.cursor(cursor_factory=DictCursor) as ts_curs:
            received = load_recordings_from_mbids(
                ts_curs,
                [recordings[0]["recording_mbid"], recordings[1]["recording_mbid"]]
            )
        self.maxDiff = None
        self.assertEqual(expected, received)

    def test_fetch_track_metadata_for_items(self):
        self.maxDiff = None
        recordings = self.insert_recordings()
        models = [
            # these recordings test we find mapping metadata from mbids
            MsidMbidModel(recording_msid=recordings[0]["recording_msid"], recording_mbid=recordings[0]["recording_mbid"]),
            MsidMbidModel(recording_msid=recordings[1]["recording_msid"], recording_mbid=recordings[1]["recording_mbid"]),
            # this recording tests loading data from MsB when no mapping is available
            MsidMbidModel(recording_msid=recordings[2]["recording_msid"], recording_mbid=None),
            # this recording tests loading mapping metadata from msid but no mbid
            # (we actually have a mapped mbid in the corresponding recording but omit it here for testing this case)
            MsidMbidModel(recording_msid=recordings[3]["recording_msid"], recording_mbid=None),
            # test the case where user submitted a mbid for the item but its absent from mbid_mapping
            MsidMbidModel(recording_msid=recordings[4]["recording_msid"], recording_mbid="0f53fa2f-f015-40c6-a5cd-f17af596764c")
        ]
        models = fetch_track_metadata_for_items(self.ts_conn, models)

        for idx in range(5):
            metadata = models[idx].track_metadata
            recording = recordings[idx]
            self.assertEqual(metadata["track_name"], recording["title"])
            self.assertEqual(metadata["artist_name"], recording["artist"])

            if 2 <= idx <= 4:  # these recordings are only present in MsB
                continue

            self.assertEqual(metadata["release_name"], recording["release"])
            self.assertEqual(metadata["additional_info"]["recording_msid"], recording["recording_msid"])
            self.assertEqual(metadata["mbid_mapping"]["recording_mbid"], recording["recording_mbid"])
            self.assertEqual(metadata["mbid_mapping"]["release_mbid"], recording["release_mbid"])
            self.assertEqual(metadata["mbid_mapping"]["artist_mbids"], recording["artist_mbids"])
            self.assertEqual(metadata["mbid_mapping"]["artists"], recording["artists"])

    def test_fetch_track_metadata_for_items_with_same_mbid(self):
        recording = self.insert_recordings()[0]
        models = [
            MsidMbidModel(recording_msid=recording["recording_msid"], recording_mbid=recording["recording_mbid"]),
            MsidMbidModel(recording_msid=recording["recording_msid"], recording_mbid=recording["recording_mbid"]),
        ]
        models = fetch_track_metadata_for_items(self.ts_conn, models)
        for model in models:
            metadata = model.track_metadata
            self.assertEqual(metadata["track_name"], recording["title"])
            self.assertEqual(metadata["artist_name"], recording["artist"])
            self.assertEqual(metadata["release_name"], recording["release"])
            self.assertEqual(metadata["additional_info"]["recording_msid"], recording["recording_msid"])
            self.assertEqual(metadata["mbid_mapping"]["recording_mbid"], recording["recording_mbid"])
            self.assertEqual(metadata["mbid_mapping"]["release_mbid"], recording["release_mbid"])
            self.assertEqual(metadata["mbid_mapping"]["artist_mbids"], recording["artist_mbids"])
            self.assertEqual(metadata["mbid_mapping"]["artists"], recording["artists"])
