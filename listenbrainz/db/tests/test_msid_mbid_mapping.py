from sqlalchemy import text

from listenbrainz import messybrainz
from listenbrainz.db.msid_mbid_mapping import load_recordings_from_mapping, fetch_track_metadata_for_items, MsidMbidModel
from listenbrainz.db.testing import TimescaleTestCase
from listenbrainz.db import timescale as ts


class MappingTestCase(TimescaleTestCase):

    def insert_recording_in_mapping(self, recording):
        with ts.engine.connect() as connection:
            if recording["recording_mbid"]:
                connection.execute(text("""
                    INSERT INTO mbid_mapping_metadata (artist_credit_id, recording_mbid, release_mbid, release_name,
                                                       artist_mbids, artist_credit_name, recording_name)
                     VALUES (:artist_credit_id, :recording_mbid ::UUID, :release_mbid ::UUID, :release,
                             :artist_mbids ::UUID[], :artist, :title)
                """), **recording)
                match_type = "exact_match"
            else:
                match_type = "no_match"

            connection.execute(
                text("""
                INSERT INTO mbid_mapping (recording_msid, recording_mbid, match_type)
                                  VALUES (:recording_msid, :recording_mbid, :match_type)
            """),
                recording_msid=recording["recording_msid"],
                recording_mbid=recording["recording_mbid"],
                match_type=match_type
            )

    def insert_recordings(self):
        recordings = [
            {
                "artist_credit_id": 204,
                "recording_mbid": "00000737-3a59-4499-b30a-31fe2464555d",
                "release_mbid": "a2589025-8517-45ab-9d64-fe927ba087b1",
                "release": "Batman Returns",
                "artist_mbids": ["5b24fbab-c58f-4c37-a59d-ab232e2d98c4"],
                "artist": "Danny Elfman",
                "title": "The Final Confrontation, Part 1"
            },
            {
                "artist_credit_id": 133549,
                "recording_mbid": "c5bfd98d-ccde-4cf3-8abb-63fad1b6065a",
                "release_mbid": "5da4af04-d796-4d07-801d-a878e83dea48",
                "release": "Random Is Resistance",
                "artist_mbids": ["797bcf41-0e02-431d-ab99-020e1cb3d0fd"],
                "artist": "Rotersand",
                "title": "A Number and a Name"
            },
            {
                "artist": "James S.A. Corey",
                "title": "The Churn"
            },
            {
                "artist_credit_id": 347,
                "recording_mbid": "67bcde07-bfb1-4b30-88ba-6b995ec04123",
                "release_mbid": "27280632-fa33-3801-a5b1-081ed0b65bb3",
                "release": "Year Zero",
                "artist_mbids": ["b7ffd2af-418f-4be2-bdd1-22f8b48613da"],
                "artist": "Nine Inch Nails",
                "title": "The Warning"
            }
        ]
        submitted = messybrainz.insert_all_in_transaction(recordings)
        # data sent to msb cannot contain nulls but we want it when inserting in mapping
        recordings[2].update(**{
            "artist_credit_id": None,
            "recording_mbid": None,
            "release_mbid": None,
            "release": None,
            "artist_mbids": None,
        })
        for recording, submission in zip(recordings, submitted):
            recording["recording_msid"] = submission["ids"]["recording_msid"]
            self.insert_recording_in_mapping(recording)
            # artist_credit_id is not retrieved, remove from dict after submitting
            del recording["artist_credit_id"]
        return recordings

    def test_load_recordings_from_mapping(self):
        recordings = self.insert_recordings()
        expected_mbid_map = {
            recordings[0]["recording_mbid"]: recordings[0],
            recordings[1]["recording_mbid"]: recordings[1]
        }
        expected_msid_map = {
            recordings[3]["recording_msid"]: recordings[3]
        }
        mbid_map, msid_map = load_recordings_from_mapping(
            mbids=[recordings[0]["recording_mbid"], recordings[1]["recording_mbid"]],
            msids=[recordings[2]["recording_msid"], recordings[3]["recording_msid"]]
        )
        self.assertEqual(expected_msid_map, msid_map)
        self.assertEqual(expected_mbid_map, mbid_map)

    def test_fetch_track_metadata_for_items(self):
        recordings = self.insert_recordings()
        models = [
            # these recordings test we find mapping metadata from mbids
            MsidMbidModel(recording_msid=recordings[0]["recording_msid"], recording_mbid=recordings[0]["recording_mbid"]),
            MsidMbidModel(recording_msid=recordings[1]["recording_msid"], recording_mbid=recordings[1]["recording_mbid"]),
            # this recording tests loading data from MsB when no mapping is available
            MsidMbidModel(recording_msid=recordings[2]["recording_msid"], recording_mbid=None),
            # this recording tests loading mapping metadata from msid but no mbid
            # (we actually have a mapped mbid in the corresponding recording but omit it here for testing this case)
            MsidMbidModel(recording_msid=recordings[3]["recording_msid"], recording_mbid=None)
        ]
        models = fetch_track_metadata_for_items(models)

        for model, recording in zip(models, recordings):
            self.assertEqual(model.recording_msid, recording["recording_msid"])
            self.assertEqual(model.recording_mbid, recording["recording_mbid"])
            metadata = model.track_metadata
            self.assertEqual(metadata["track_name"], recording["title"])
            self.assertEqual(metadata["artist_name"], recording["artist"])

            if recording["recording_mbid"] is None:  # 3rd recording which only present in MsB
                continue

            self.assertEqual(metadata["release_name"], recording["release"])
            self.assertEqual(metadata["release_name"], recording["release"])
            self.assertEqual(metadata["recording_mbid"], recording["recording_mbid"])
            self.assertEqual(metadata["release_mbid"], recording["release_mbid"])
            self.assertEqual(metadata["artist_mbids"], recording["artist_mbids"])
