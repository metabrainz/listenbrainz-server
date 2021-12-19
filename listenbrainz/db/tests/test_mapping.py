from sqlalchemy import text

from listenbrainz.db.mapping import load_recordings_from_mapping
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

            connection.execute(text("""
                INSERT INTO mbid_mapping (recording_msid, recording_mbid, match_type)
                                  VALUES (:recording_msid, :recording_mbid, :match_type)
            """), recording_msid=recording["recording_msid"], recording_mbid=recording["recording_mbid"], match_type=match_type)

    def test_load_recordings_from_mapping(self):
        recording_1 = {
            "recording_msid": "00000737-3a59-4499-b30a-31fe2464555d",
            "artist_credit_id": 204,
            "recording_mbid": "00000737-3a59-4499-b30a-31fe2464555d",
            "release_mbid": "a2589025-8517-45ab-9d64-fe927ba087b1",
            "release_name": "Batman Returns",
            "artist_mbids": ["5b24fbab-c58f-4c37-a59d-ab232e2d98c4"],
            "artist": "Danny Elfman",
            "title": "The Final Confrontation, Part 1"
        }
        recording_2 = {
            "recording_msid": "000013b3-dbb4-43a0-8fd4-ca92ff5ed033",
            "artist_credit_id": 133549,
            "recording_mbid": "c5bfd98d-ccde-4cf3-8abb-63fad1b6065a",
            "release_mbid": "5da4af04-d796-4d07-801d-a878e83dea48",
            "release_name": "Random Is Resistance",
            "artist_mbids": ["797bcf41-0e02-431d-ab99-020e1cb3d0fd"],
            "artist": "Rotersand",
            "title": "A Number and a Name"
        }
        recording_3 = {
            "recording_msid": "0000032a-3a2f-414c-80e2-a03b23cbeb71",
            "artist_credit_id": None,
            "recording_mbid": None,
            "release_mbid": None,
            "release_name": None,
            "artist_mbids": None,
            "artist": None,
            "title": None
        }

        self.insert_recording_in_mapping(recording_1)
        self.insert_recording_in_mapping(recording_2)
        self.insert_recording_in_mapping(recording_3)

        # artist_credit_id is not retrieved, remove from dict before checking
        del recording_1["artist_credit_id"]
        del recording_2["artist_credit_id"]
        del recording_3["artist_credit_id"]

        expected_mbid_map = {
            recording_1["recording_mbid"]: recording_1,
            recording_2["recording_mbid"]: recording_2
        }
        expected_msid_map = {
            recording_3["recording_msid"]: recording_3
        }
        mbid_map, msid_map = load_recordings_from_mapping(
            mbids=[recording_1["recording_mbid"], recording_2["recording_mbid"]],
            msids=[recording_3["recording_msid"]]
        )
        self.assertEqual(expected_msid_map, msid_map)
        self.assertEqual(expected_mbid_map, mbid_map)
