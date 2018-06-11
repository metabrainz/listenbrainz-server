from messybrainz import db
from messybrainz import submit_listens_and_sing_me_a_sweet_song as submit_listens
from messybrainz.db import artist
from messybrainz.db.testing import DatabaseTestCase
from unittest.mock import patch
from uuid import UUID

import json


class ArtistTestCase(DatabaseTestCase):

    def _load_test_data(self, filename):
        """Loads data for tests from a given JSON file name."""

        with open(self.path_to_data_file(filename)) as f:
            recordings = json.load(f)
        
        msb_listens = []
        for recording in recordings:
            messy_dict = {
                'artist': recording['artist'],
                'title': recording['title'],
                'recording_mbid': recording['recording_mbid'],
            }
            msb_listens.append(messy_dict)
        return msb_listens


    @patch('messybrainz.db.artist.fetch_artist_mbids')
    def test_fetch_recording_mbids_not_in_recording_artist_join(self, mock_fetch_artist_mbids):
        """Tests if recording MBIDs that are not in recording_artist_join table
           are fetched correctly.
        """

        msb_listens = self._load_test_data("valid_recordings_with_recording_mbids.json")
        submit_listens(msb_listens)

        recording_mbids_submitted = {"5465ca86-3881-4349-81b2-6efbd3a59451",
            "6ba092ae-aaf7-4154-b987-9eb9d05f8616",
            "cad174ad-d683-4858-a205-7bdc4175fff7",
        }

        recording_1 = {
            "artist": "Syreeta",
            "title": "She's Leaving Home",
            "recording_mbid": "9ed38583-437f-4186-8183-9c31ffa2c116"
        }

        mock_fetch_artist_mbids.side_effect = [
            ["f82bcf78-5b69-4622-a5ef-73800768d9ac", "859d0860-d480-4efd-970c-c05d5f1776b8"],
            ["bc1b5c95-e6d6-46b5-957a-5e8908b02c1e"],
            ["f82bcf78-5b69-4622-a5ef-73800768d9ac"],
            ["5cfeec75-f6e2-439c-946d-5317334cdc6c"],
        ]

        with db.engine.begin() as connection:
            mbids = artist.fetch_recording_mbids_not_in_recording_artist_join(connection)
            self.assertSetEqual(recording_mbids_submitted, set(mbids))

            artist.fetch_and_store_artist_mbids_for_all_recording_mbids()
            mbids = artist.fetch_recording_mbids_not_in_recording_artist_join(connection)
            self.assertListEqual(mbids, [])

            submit_listens([recording_1])
            mbids = artist.fetch_recording_mbids_not_in_recording_artist_join(connection)
            self.assertEqual(recording_1['recording_mbid'], mbids[0])

            artist.fetch_and_store_artist_mbids_for_all_recording_mbids()
            mbids = artist.fetch_recording_mbids_not_in_recording_artist_join(connection)
            self.assertListEqual(mbids, [])


    @patch('messybrainz.db.artist.fetch_artist_mbids')
    def test_insert_artist_mbids(self, mock_fetch_artist_mbids):
        """Tests if artist MBIDs are correctly inserted into recording_artist_join table."""

        recording_mbid = "5465ca86-3881-4349-81b2-6efbd3a59451"
        mock_fetch_artist_mbids.return_value = [UUID("f82bcf78-5b69-4622-a5ef-73800768d9ac"), UUID("859d0860-d480-4efd-970c-c05d5f1776b8")]
        with db.engine.begin() as connection:
            artist_mbids = artist.fetch_artist_mbids(connection, recording_mbid)
            artist.insert_artist_mbids(connection, recording_mbid, artist_mbids)
            artist_mbids_from_join = artist.get_artist_mbids_for_recording_mbid(connection, recording_mbid)
            self.assertSetEqual(set(artist_mbids), set(artist_mbids_from_join))


    @patch('messybrainz.db.artist.fetch_artist_mbids')
    def test_get_artist_mbids_for_recording_mbid(self, mock_fetch_artist_mbids):
        """Tests if recording_mbids store artist_mbids correctly."""

        recording_mbid = "5465ca86-3881-4349-81b2-6efbd3a59451"
        mock_fetch_artist_mbids.return_value = [UUID("f82bcf78-5b69-4622-a5ef-73800768d9ac"), UUID("859d0860-d480-4efd-970c-c05d5f1776b8")]
        with db.engine.begin() as connection:
            artist_mbids_from_join = artist.get_artist_mbids_for_recording_mbid(connection, recording_mbid)
            self.assertIsNone(artist_mbids_from_join)

            artist_mbids = artist.fetch_artist_mbids(connection, recording_mbid)
            artist.insert_artist_mbids(connection, recording_mbid, artist_mbids)
            artist_mbids_from_join = artist.get_artist_mbids_for_recording_mbid(connection, recording_mbid)
            self.assertSetEqual(set(artist_mbids), set(artist_mbids_from_join))


    @patch('messybrainz.db.artist.fetch_artist_mbids')
    def test_fetch_and_store_artist_mbids_for_all_recording_mbids(self, mock_fetch_artist_mbids):
        """Test if artist MBIDs are fetched and stored correctly for all recording MBIDs
           not in recording_artist_join table.
        """

        msb_listens = self._load_test_data("valid_recordings_with_recording_mbids.json")
        submit_listens(msb_listens)

        recording_mbids_submitted = ["5465ca86-3881-4349-81b2-6efbd3a59451",
            "6ba092ae-aaf7-4154-b987-9eb9d05f8616",
            "cad174ad-d683-4858-a205-7bdc4175fff7",
        ]

        recording_1 = {
            "artist": "Syreeta",
            "title": "She's Leaving Home",
            "recording_mbid": "9ed38583-437f-4186-8183-9c31ffa2c116"
        }

        artist_mbids_fetched = [
            ["f82bcf78-5b69-4622-a5ef-73800768d9ac"],
            ["f82bcf78-5b69-4622-a5ef-73800768d9ac", "859d0860-d480-4efd-970c-c05d5f1776b8"],
            ["bc1b5c95-e6d6-46b5-957a-5e8908b02c1e"],
            ["5cfeec75-f6e2-439c-946d-5317334cdc6c"],
        ]

        artist_mbids_fetched = [
            [UUID(artist_mbid) for artist_mbid in artist_mbids]
            for artist_mbids in artist_mbids_fetched
        ]

        mock_fetch_artist_mbids.side_effect = artist_mbids_fetched

        with db.engine.begin() as connection:
            artist.fetch_and_store_artist_mbids_for_all_recording_mbids()
            # Using sets for assertions because we can get multiple artist MBIDs for a
            # single recording MBID, but the order of retrieval is not known.
            artist_mbids = artist.get_artist_mbids_for_recording_mbid(connection, "cad174ad-d683-4858-a205-7bdc4175fff7")
            self.assertSetEqual(set(artist_mbids), set(artist_mbids_fetched[0]))

            artist_mbids = artist.get_artist_mbids_for_recording_mbid(connection, "5465ca86-3881-4349-81b2-6efbd3a59451")
            self.assertSetEqual(set(artist_mbids), set(artist_mbids_fetched[1]))

            artist_mbids = artist.get_artist_mbids_for_recording_mbid(connection, "6ba092ae-aaf7-4154-b987-9eb9d05f8616")
            self.assertSetEqual(set(artist_mbids), set(artist_mbids_fetched[2]))

            artist_mbids = artist.get_artist_mbids_for_recording_mbid(connection, "9ed38583-437f-4186-8183-9c31ffa2c116")
            self.assertIsNone(artist_mbids)

            submit_listens([recording_1])
            artist.fetch_and_store_artist_mbids_for_all_recording_mbids()
            artist_mbids = artist.get_artist_mbids_for_recording_mbid(connection, "9ed38583-437f-4186-8183-9c31ffa2c116")
            self.assertSetEqual(set(artist_mbids), set(artist_mbids_fetched[3]))
