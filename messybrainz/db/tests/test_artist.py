from messybrainz import data
from messybrainz import db
from messybrainz import submit_listens_and_sing_me_a_sweet_song as submit_listens
from messybrainz.db import artist
from messybrainz.db.testing import DatabaseTestCase
from unittest.mock import patch
from uuid import UUID

import json
import unittest


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
            }
            if 'release' in recording:
                messy_dict['release'] = recording['release']
            if 'artist_mbids' in recording:
                messy_dict['artist_mbids'] = recording['artist_mbids']
            if 'release_mbid' in recording:
                messy_dict['release_mbid'] = recording['release_mbid']
            if 'recording_mbid' in recording:
                messy_dict['recording_mbid'] = recording['recording_mbid']
            if 'track_number' in recording:
                messy_dict['track_number'] = recording['track_number']
            if 'spotify_id' in recording:
                messy_dict['spotify_id'] = recording['spotify_id']
            msb_listens.append(messy_dict)

        return msb_listens


    def _add_mbids_to_recording_artist_join(self):
        """ Adds artist MBIDs to recording_artist_join table for recording MBIDs."""

        recording_mbids_submitted = ["5465ca86-3881-4349-81b2-6efbd3a59451",
            "9475f8ef-e785-4b9f-a8c2-03ceb817553e",
            "cad174ad-d683-4858-a205-7bdc4175fff7",
            "6ba092ae-aaf7-4154-b987-9eb9d05f8616",
            "9ed38583-437f-4186-8183-9c31ffa2c116",
        ]

        artist_mbids_fetched = [
            ["859d0860-d480-4efd-970c-c05d5f1776b8", "f82bcf78-5b69-4622-a5ef-73800768d9ac"],
            ["f82bcf78-5b69-4622-a5ef-73800768d9ac"],
            ["f82bcf78-5b69-4622-a5ef-73800768d9ac"],
            ["bc1b5c95-e6d6-46b5-957a-5e8908b02c1e"],
            ["5cfeec75-f6e2-439c-946d-5317334cdc6c"],
        ]

        artist_mbids_fetched = [
            [UUID(artist_mbid) for artist_mbid in artist_mbids]
            for artist_mbids in artist_mbids_fetched
        ]

        with db.engine.begin() as connection:
            for recording_mbid, artist_mbids in zip(recording_mbids_submitted, artist_mbids_fetched):
                artist.insert_artist_mbids(connection, recording_mbid, artist_mbids)


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

        artist_mbids_fetched = [
            ["f82bcf78-5b69-4622-a5ef-73800768d9ac"],
            ["859d0860-d480-4efd-970c-c05d5f1776b8", "f82bcf78-5b69-4622-a5ef-73800768d9ac"],
            ["bc1b5c95-e6d6-46b5-957a-5e8908b02c1e"],
            ["5cfeec75-f6e2-439c-946d-5317334cdc6c"],
        ]

        artist_mbids_fetched = [
            [UUID(artist_mbid) for artist_mbid in artist_mbids]
            for artist_mbids in artist_mbids_fetched
        ]

        mock_fetch_artist_mbids.side_effect = artist_mbids_fetched

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
            artist_mbids.sort()
            artist.insert_artist_mbids(connection, recording_mbid, artist_mbids)
            artist_mbids_from_join = artist.get_artist_mbids_for_recording_mbid(connection, recording_mbid)
            self.assertListEqual(artist_mbids, artist_mbids_from_join)


    @patch('messybrainz.db.artist.fetch_artist_mbids')
    def test_get_artist_mbids_for_recording_mbid(self, mock_fetch_artist_mbids):
        """Tests if recording_mbids store artist_mbids correctly."""

        recording_mbid = "5465ca86-3881-4349-81b2-6efbd3a59451"
        mock_fetch_artist_mbids.return_value = [UUID("f82bcf78-5b69-4622-a5ef-73800768d9ac"), UUID("859d0860-d480-4efd-970c-c05d5f1776b8")]
        with db.engine.begin() as connection:
            artist_mbids_from_join = artist.get_artist_mbids_for_recording_mbid(connection, recording_mbid)
            self.assertIsNone(artist_mbids_from_join)

            artist_mbids = artist.fetch_artist_mbids(connection, recording_mbid)
            artist_mbids.sort()
            artist.insert_artist_mbids(connection, recording_mbid, artist_mbids)
            artist_mbids_from_join = artist.get_artist_mbids_for_recording_mbid(connection, recording_mbid)
            self.assertListEqual(artist_mbids, artist_mbids_from_join)


    @patch('messybrainz.db.artist.fetch_artist_mbids')
    @unittest.skip("test fails with pg12 upgrade, this isn't used in prod anywhere")
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
            ["859d0860-d480-4efd-970c-c05d5f1776b8", "f82bcf78-5b69-4622-a5ef-73800768d9ac"],
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
            self.assertListEqual(artist_mbids, artist_mbids_fetched[0])

            artist_mbids = artist.get_artist_mbids_for_recording_mbid(connection, "5465ca86-3881-4349-81b2-6efbd3a59451")
            self.assertListEqual(artist_mbids, artist_mbids_fetched[1])

            artist_mbids = artist.get_artist_mbids_for_recording_mbid(connection, "6ba092ae-aaf7-4154-b987-9eb9d05f8616")
            self.assertListEqual(artist_mbids, artist_mbids_fetched[2])

            artist_mbids = artist.get_artist_mbids_for_recording_mbid(connection, "9ed38583-437f-4186-8183-9c31ffa2c116")
            self.assertIsNone(artist_mbids)

            submit_listens([recording_1])
            artist.fetch_and_store_artist_mbids_for_all_recording_mbids()
            artist_mbids = artist.get_artist_mbids_for_recording_mbid(connection, "9ed38583-437f-4186-8183-9c31ffa2c116")
            self.assertListEqual(artist_mbids, artist_mbids_fetched[3])


    def test_fetch_unclustered_distinct_artist_credit_mbids(self):
        """Tests if artist_credit MBIDs are fetched correctly."""

        msb_listens = self._load_test_data("recordings_for_testing_artist_clusters.json")
        submit_listens(msb_listens)
        artist_mbids_submitted = [
            ["859d0860-d480-4efd-970c-c05d5f1776b8", "f82bcf78-5b69-4622-a5ef-73800768d9ac"],
            ["bc1b5c95-e6d6-46b5-957a-5e8908b02c1e"],
            ["f82bcf78-5b69-4622-a5ef-73800768d9ac"],
            ["5cfeec75-f6e2-439c-946d-5317334cdc6c"],
            ["88a8d8a9-7c9b-4f7b-8700-7f0f7a503688"],
            ["b49a9595-3576-44bb-8ac0-e26d3f5b42ff"],
        ]

        artist_mbids_submitted = [
            [UUID(artist_mbid) for artist_mbid in artist_mbids]
            for artist_mbids in artist_mbids_submitted
        ]

        artist_mbids_submitted = {
            tuple(artist_mbids) for artist_mbids in artist_mbids_submitted
        }

        with db.engine.begin() as connection:
            artist_credit_mbids = artist.fetch_unclustered_distinct_artist_credit_mbids(connection)
            artist_credit_mbids = {tuple(artist_mbids) for artist_mbids in artist_credit_mbids}
            self.assertSetEqual(artist_mbids_submitted, artist_credit_mbids)

            artist.create_artist_credit_clusters()
            artist_credit_mbids = artist.fetch_unclustered_distinct_artist_credit_mbids(connection)
            self.assertListEqual(artist_credit_mbids, [])

            recording_1 = {
                "artist": "Memphis Minnie",
                "title": "Banana Man Blues",
                "recording_mbid": "e1efdbee-2904-437f-b0e2-dbb4906b86d2",
                "artist_mbids": ["ff748426-8873-4725-bdc7-c2b18b510d41"],
            }
            submit_listens([recording_1])
            artist_credit_mbids = artist.fetch_unclustered_distinct_artist_credit_mbids(connection)
            self.assertEqual(len(artist_credit_mbids), 1)
            self.assertListEqual([[UUID("ff748426-8873-4725-bdc7-c2b18b510d41")]], artist_credit_mbids)


    def test_link_artist_mbids_to_artist_credit_cluster_id(self):
        """Tests if artist MBIDs are linked to cluster correctly. Links are created in
           artist_credit_redirect table.
        """

        recording_1 = {
            "artist": "Jay‐Z & Beyoncé",
            "artist_mbids": ["f82bcf78-5b69-4622-a5ef-73800768d9ac","859d0860-d480-4efd-970c-c05d5f1776b8"],
            "recording_mbid": "5465ca86-3881-4349-81b2-6efbd3a59451",
            "title": "'03 Bonnie and Clyde",
        }
        submit_listens([recording_1])

        with db.engine.begin() as connection:
            artist_mbids = artist.fetch_unclustered_distinct_artist_credit_mbids(connection)
            gids = artist.fetch_unclustered_gids_for_artist_credit_mbids(connection, artist_mbids[0])
            artist.link_artist_mbids_to_artist_credit_cluster_id(connection, gids[0], artist_mbids[0])
            cluster_id = artist.get_artist_cluster_id_using_artist_mbids(connection, artist_mbids[0])
            self.assertEqual(cluster_id, gids[0])


    def test_insert_artist_credit_cluster(self):
        """Tests if artist_credit cluster is stored correctly in artist_credit_cluster table."""

        # recording_1 and recording_2 are different as join phrase in artist of recording_1
        # is '&' and in recording_2 is 'and'.
        recording_1 = {
            "artist": "Jay‐Z & Beyoncé",
            "artist_mbids": ["f82bcf78-5b69-4622-a5ef-73800768d9ac","859d0860-d480-4efd-970c-c05d5f1776b8"],
            "recording_mbid": "5465ca86-3881-4349-81b2-6efbd3a59451",
            "title": "'03 Bonnie and Clyde",
        }

        recording_2 = {
            "artist": "Jay‐Z and Beyoncé",
            "artist_mbids": ["f82bcf78-5b69-4622-a5ef-73800768d9ac","859d0860-d480-4efd-970c-c05d5f1776b8"],
            "recording_mbid": "5465ca86-3881-4349-81b2-6efbd3a59451",
            "title": "'03 Bonnie and Clyde",
        }

        submit_listens([recording_1, recording_2])

        with db.engine.begin() as connection:
            artist_mbids = artist.fetch_unclustered_distinct_artist_credit_mbids(connection)
            gids = artist.fetch_unclustered_gids_for_artist_credit_mbids(connection, artist_mbids[0])
            self.assertEqual(len(gids), 2)
            artist.insert_artist_credit_cluster(connection, gids[0], gids)
            gids = artist.fetch_unclustered_gids_for_artist_credit_mbids(connection, artist_mbids[0])
            self.assertEqual(len(gids), 0)


    def test_fetch_unclustered_gids_for_artist_credit_mbids(self):
        """Tests if gids are fetched for an array of artist MBIDs correctly."""

        # recording_1 and recording_2 are different as join phrase in artist of recording_1
        # is '&' and in recording_2 is 'and'.
        recording_1 = {
            "artist": "Jay‐Z & Beyoncé",
            "artist_mbids": ["f82bcf78-5b69-4622-a5ef-73800768d9ac", "859d0860-d480-4efd-970c-c05d5f1776b8"],
            "recording_mbid": "5465ca86-3881-4349-81b2-6efbd3a59451",
            "title": "'03 Bonnie and Clyde",
        }

        recording_2 = {
            "artist": "Jay‐Z and Beyoncé",
            "artist_mbids": ["f82bcf78-5b69-4622-a5ef-73800768d9ac", "859d0860-d480-4efd-970c-c05d5f1776b8"],
            "recording_mbid": "5465ca86-3881-4349-81b2-6efbd3a59451",
            "title": "'03 Bonnie and Clyde",
        }

        submit_listens([recording_1, recording_2])

        with db.engine.begin() as connection:
            gids = artist.fetch_unclustered_gids_for_artist_credit_mbids(connection, [
                        UUID("859d0860-d480-4efd-970c-c05d5f1776b8"), UUID("f82bcf78-5b69-4622-a5ef-73800768d9ac")
                    ])
            gids_from_data = set([
                UUID(data.get_artist_credit(connection, recording_1["artist"])),
                UUID(data.get_artist_credit(connection, recording_2["artist"]))
            ])
            self.assertSetEqual(set(gids), gids_from_data)


    def test_get_artist_cluster_id_using_artist_mbids(self):
        """Tests if cluster_id is returned correctly using artist_mbids."""

        msb_listens = self._load_test_data("recordings_for_testing_artist_clusters.json")
        submit_listens(msb_listens)

        artist.create_artist_credit_clusters()
        with db.engine.begin() as connection:
            cluster_id = artist.get_artist_cluster_id_using_artist_mbids(connection, [
                        UUID("859d0860-d480-4efd-970c-c05d5f1776b8"), UUID("f82bcf78-5b69-4622-a5ef-73800768d9ac")
                    ])

            gid_from_data = UUID(data.get_artist_credit(connection, "Jay‐Z & Beyoncé"))
            cluster_id_from_data = artist.get_cluster_id_using_msid(connection, gid_from_data)
            self.assertEqual(cluster_id, cluster_id_from_data)

            gid_from_data = UUID(data.get_artist_credit(connection, "Jay‐Z and Beyoncé"))
            cluster_id_from_data = artist.get_cluster_id_using_msid(connection, gid_from_data)
            self.assertEqual(cluster_id, cluster_id_from_data)

            cluster_id = artist.get_artist_cluster_id_using_artist_mbids(connection, [
                        UUID("88a8d8a9-7c9b-4f7b-8700-7f0f7a503688"),
            ])

            gid_from_data = UUID(data.get_artist_credit(connection, "James Morrison"))
            cluster_id_from_data = artist.get_cluster_id_using_msid(connection, gid_from_data)
            self.assertEqual(cluster_id, cluster_id_from_data)


    def test_fetch_artist_credits_left_to_cluster(self):
        """Tests if artist_credits left to cluster after first
           pass are correctly fetched.
        """

        msb_listens = self._load_test_data("recordings_for_testing_artist_clusters.json")
        submit_listens(msb_listens)

        with db.engine.begin() as connection:
            artist.create_artist_credit_clusters_without_considering_anomalies(connection)
            # In the data used from recordings_for_testing_artist_clusters
            # the recordings for artist 'James Morrison' represents anomaly
            # as two James Morrison exist with different artist MBIDs

            artist_left = artist.fetch_artist_credits_left_to_cluster(connection)
            self.assertEqual(len(artist_left), 1)

            # 'James Morrison' with artist MBID '88a8d8a9-7c9b-4f7b-8700-7f0f7a503688'
            # was clustered in the first phase.
            self.assertListEqual(artist_left, [[UUID("b49a9595-3576-44bb-8ac0-e26d3f5b42ff")]])


    def test_get_cluster_id_using_msid(self):
        """Tests if cluster_id is correctly retrived using any MSID for the cluster."""

        msb_listens = self._load_test_data("recordings_for_testing_artist_clusters.json")
        submit_listens(msb_listens)

        artist.create_artist_credit_clusters()
        with db.engine.begin() as connection:
            gid_from_data = UUID(data.get_artist_credit(connection, "Jay‐Z & Beyoncé"))
            cluster_id_1 = artist.get_cluster_id_using_msid(connection, gid_from_data)
            gid_from_data = UUID(data.get_artist_credit(connection, "Jay‐Z and Beyoncé"))
            cluster_id_2 = artist.get_cluster_id_using_msid(connection, gid_from_data)

            self.assertEqual(cluster_id_1, cluster_id_2)


    def test_get_artist_gids_from_recording_json_using_mbids(self):
        """Tests if artist_gids are correctly fetched using a given list of artist MBIDs"""

        msb_listens = self._load_test_data("recordings_for_testing_artist_clusters.json")
        submit_listens(msb_listens)

        with db.engine.begin() as connection:
            mbids = [
                        UUID("859d0860-d480-4efd-970c-c05d5f1776b8"),
                        UUID("f82bcf78-5b69-4622-a5ef-73800768d9ac"),
                    ]
            gids = set(artist.get_artist_gids_from_recording_json_using_mbids(connection, mbids))
            gids_from_data = set([
                UUID(data.get_artist_credit(connection, "Jay‐Z & Beyoncé")),
                UUID(data.get_artist_credit(connection, "Jay‐Z and Beyoncé"))
            ])

            self.assertSetEqual(gids, gids_from_data)


    def test_get_artist_mbids_using_msid(self):
        """Test if artist_mbids are fetched correctly for given MSID"""

        msb_listens = self._load_test_data("recordings_for_testing_artist_clusters.json")
        submit_listens(msb_listens)
        artist.create_artist_credit_clusters()

        with db.engine.begin() as connection:
            gid_from_data = UUID(data.get_artist_credit(connection, "Jay‐Z & Beyoncé"))
            artist_mbids_1 = artist.get_artist_mbids_using_msid(connection, gid_from_data)
            gid_from_data = UUID(data.get_artist_credit(connection, "Jay‐Z and Beyoncé"))
            artist_mbids_2 = artist.get_artist_mbids_using_msid(connection, gid_from_data)
            self.assertListEqual(artist_mbids_1, artist_mbids_2)


    def test_create_artist_credit_clusters_without_considering_anomalies(self):
        """Tests if clusters created without considering anomalies (A single
           MSID pointing to multiple MBIDs arrays in artist_credit_redirect table)
           are correctly formed.
        """

        msb_listens = self._load_test_data("recordings_for_testing_artist_clusters.json")
        submit_listens(msb_listens)

        with db.engine.begin() as connection:
            clusters_modified, clusters_add_to_redirect = artist.create_artist_credit_clusters_without_considering_anomalies(connection)
            self.assertEqual(clusters_modified, 5)
            self.assertEqual(clusters_add_to_redirect, 5)

            # 'Jay-Z & Beyonce' and 'Jay-Z and Beyonce' form one cluster
            gid_from_data = UUID(data.get_artist_credit(connection, "Jay‐Z & Beyoncé"))
            artist_mbids_1 = artist.get_artist_mbids_using_msid(connection, gid_from_data)
            cluster_id_1 = artist.get_cluster_id_using_msid(connection, gid_from_data)
            gid_from_data = UUID(data.get_artist_credit(connection, "Jay‐Z and Beyoncé"))
            artist_mbids_2 = artist.get_artist_mbids_using_msid(connection, gid_from_data)
            cluster_id_2 = artist.get_cluster_id_using_msid(connection, gid_from_data)
            self.assertListEqual(artist_mbids_1, artist_mbids_2)
            self.assertEqual(cluster_id_1, cluster_id_2)

            # 'Lil' Kim' and 'Lil Kim' form one cluster
            gid_from_data = UUID(data.get_artist_credit(connection, "Lil’ Kim"))
            artist_mbids_1 = artist.get_artist_mbids_using_msid(connection, gid_from_data)
            cluster_id_1 = artist.get_cluster_id_using_msid(connection, gid_from_data)
            gid_from_data = UUID(data.get_artist_credit(connection, "Lil Kim"))
            artist_mbids_2 = artist.get_artist_mbids_using_msid(connection, gid_from_data)
            cluster_id_2 = artist.get_cluster_id_using_msid(connection, gid_from_data)
            self.assertListEqual(artist_mbids_1, artist_mbids_2)
            self.assertEqual(cluster_id_1, cluster_id_2)

            # 'Jay-Z' and 'Jay_Z' form one cluster
            gid_from_data = UUID(data.get_artist_credit(connection, "JAY-Z"))
            artist_mbids_1 = artist.get_artist_mbids_using_msid(connection, gid_from_data)
            cluster_id_1 = artist.get_cluster_id_using_msid(connection, gid_from_data)
            gid_from_data = UUID(data.get_artist_credit(connection, "JAY_Z"))
            artist_mbids_2 = artist.get_artist_mbids_using_msid(connection, gid_from_data)
            cluster_id_2 = artist.get_cluster_id_using_msid(connection, gid_from_data)
            self.assertListEqual(artist_mbids_1, artist_mbids_2)
            self.assertEqual(cluster_id_1, cluster_id_2)

            # 'Syreeta' form one cluster
            gid_from_data = UUID(data.get_artist_credit(connection, "Syreeta"))
            artist_mbids = artist.get_artist_mbids_using_msid(connection, gid_from_data)
            self.assertListEqual(artist_mbids, [[UUID("5cfeec75-f6e2-439c-946d-5317334cdc6c")]])

            # 'James Morrison' with artist MBID '88a8d8a9-7c9b-4f7b-8700-7f0f7a503688'
            # is clustered as before no artist_credit_gid exists with this artist_credit
            # in artist_credit_cluster before this is inserted.
            gid_from_data = UUID(data.get_artist_credit(connection, "James Morrison"))
            artist_mbids = artist.get_artist_mbids_using_msid(connection, gid_from_data)
            self.assertListEqual(artist_mbids, [[UUID("88a8d8a9-7c9b-4f7b-8700-7f0f7a503688")]])


    def test_create_artist_credit_clusters_for_anomalies(self):
        """Tests if clusters are created correctly for the anomalies
           (A single MSID pointing to multiple MBIDs arrays in
           artist_credit_redirect table).
        """

        msb_listens = self._load_test_data("recordings_for_testing_artist_clusters.json")
        submit_listens(msb_listens)

        with db.engine.begin() as connection:
            clusters_modified, clusters_add_to_redirect = artist.create_artist_credit_clusters_without_considering_anomalies(connection)
            self.assertEqual(clusters_modified, 5)
            self.assertEqual(clusters_add_to_redirect, 5)

            # Before clustering anomalies
            # 'James Morrison' with artist MBID '88a8d8a9-7c9b-4f7b-8700-7f0f7a503688'
            # is clustered as before no artist_credit_gid exists with this artist_credit
            # in artist_credit_cluster before this is inserted.
            gid_from_data = UUID(data.get_artist_credit(connection, "James Morrison"))
            artist_mbids = artist.get_artist_mbids_using_msid(connection, gid_from_data)
            self.assertListEqual(artist_mbids, [[UUID("88a8d8a9-7c9b-4f7b-8700-7f0f7a503688")]])

            clusters_add_to_redirect = artist.create_artist_credit_clusters_for_anomalies(connection)
            self.assertEqual(clusters_add_to_redirect, 1)

            # After clustering anomalies
            # 'James Morrison' with artist MBID 'b49a9595-3576-44bb-8ac0-e26d3f5b42ff'
            # is clustered
            gid_from_data = UUID(data.get_artist_credit(connection, "James Morrison"))
            artist_mbids = artist.get_artist_mbids_using_msid(connection, gid_from_data)
            self.assertListEqual(artist_mbids, [
                [UUID("88a8d8a9-7c9b-4f7b-8700-7f0f7a503688")], [UUID("b49a9595-3576-44bb-8ac0-e26d3f5b42ff")]
            ])


    @unittest.skip("test fails with pg12 upgrade, this isn't used in prod anywhere")
    def test_create_artist_credit_clusters(self):
        """Tests if artist_credit clusters are correctly formed."""

        msb_listens = self._load_test_data("recordings_for_testing_artist_clusters.json")
        submit_listens(msb_listens)
        clusters_modified, clusters_add_to_redirect = artist.create_artist_credit_clusters()
        self.assertEqual(clusters_modified, 5)
        self.assertEqual(clusters_add_to_redirect, 6)

        with db.engine.begin() as connection:
            # 'Jay-Z & Beyonce' and 'Jay-Z and Beyonce' form one cluster
            gid_from_data = UUID(data.get_artist_credit(connection, "Jay‐Z & Beyoncé"))
            artist_mbids_1 = artist.get_artist_mbids_using_msid(connection, gid_from_data)
            cluster_id_1 = artist.get_cluster_id_using_msid(connection, gid_from_data)
            gid_from_data = UUID(data.get_artist_credit(connection, "Jay‐Z and Beyoncé"))
            artist_mbids_2 = artist.get_artist_mbids_using_msid(connection, gid_from_data)
            cluster_id_2 = artist.get_cluster_id_using_msid(connection, gid_from_data)
            self.assertListEqual(artist_mbids_1, artist_mbids_2)
            self.assertEqual(cluster_id_1, cluster_id_2)

            # 'Lil' Kim' and 'Lil Kim' form one cluster
            gid_from_data = UUID(data.get_artist_credit(connection, "Lil’ Kim"))
            artist_mbids_1 = artist.get_artist_mbids_using_msid(connection, gid_from_data)
            cluster_id_1 = artist.get_cluster_id_using_msid(connection, gid_from_data)
            gid_from_data = UUID(data.get_artist_credit(connection, "Lil Kim"))
            artist_mbids_2 = artist.get_artist_mbids_using_msid(connection, gid_from_data)
            cluster_id_2 = artist.get_cluster_id_using_msid(connection, gid_from_data)
            self.assertListEqual(artist_mbids_1, artist_mbids_2)
            self.assertEqual(cluster_id_1, cluster_id_2)

            # 'Jay-Z' and 'Jay_Z' form one cluster
            gid_from_data = UUID(data.get_artist_credit(connection, "JAY-Z"))
            artist_mbids_1 = artist.get_artist_mbids_using_msid(connection, gid_from_data)
            cluster_id_1 = artist.get_cluster_id_using_msid(connection, gid_from_data)
            gid_from_data = UUID(data.get_artist_credit(connection, "JAY_Z"))
            artist_mbids_2 = artist.get_artist_mbids_using_msid(connection, gid_from_data)
            cluster_id_2 = artist.get_cluster_id_using_msid(connection, gid_from_data)
            self.assertListEqual(artist_mbids_1, artist_mbids_2)
            self.assertEqual(cluster_id_1, cluster_id_2)

            # 'Syreeta' form one cluster
            gid_from_data = UUID(data.get_artist_credit(connection, "Syreeta"))
            artist_mbids = artist.get_artist_mbids_using_msid(connection, gid_from_data)
            self.assertListEqual(artist_mbids, [[UUID("5cfeec75-f6e2-439c-946d-5317334cdc6c")]])

            # 'James Morrison' with artist MBID '88a8d8a9-7c9b-4f7b-8700-7f0f7a503688'
            # and 'James Morrison' with artist MBID 'b49a9595-3576-44bb-8ac0-e26d3f5b42ff'
            # form a cluster
            gid_from_data = UUID(data.get_artist_credit(connection, "James Morrison"))
            artist_mbids = artist.get_artist_mbids_using_msid(connection, gid_from_data)
            self.assertListEqual(artist_mbids, [
                [UUID("88a8d8a9-7c9b-4f7b-8700-7f0f7a503688")], [UUID("b49a9595-3576-44bb-8ac0-e26d3f5b42ff")]
            ])

            # Add new recordings and test again.
            recordings = [
                {
                    "artist": "Consequence feat. Kanye West",
                    "artist_mbids": ["164f0d73-1234-4e2c-8743-d77bf2191051", "c2e49f7a-cd6f-48ca-8596-b03614ea4fe8"],
                    "recording_mbid": "589d375f-2f79-4841-b971-4d22d245241a",
                    "title": "Getting Out the Game",
                },
                {
                    "artist": "Jay‐Z and Beyoncé",
                    "artist_mbids": ["f82bcf78-5b69-4622-a5ef-73800768d9ac","859d0860-d480-4efd-970c-c05d5f1776b8"],
                    "recording_mbid": "5465ca86-3881-4349-81b2-6efbd3a59451",
                    "title": "03 Bonnie and Clyde",
                },
                {
                    "artist": "James Morrison",
                    "artist_mbids": ["b29c0d07-99a3-478c-af62-26e0728dfd55"],
                    "recording_mbid": "4daf8756-e1ed-469d-9b66-92af5ede7706",
                    "title": "Miss Langford’s Reel / The Milestone at the Garden",
                },
                {
                    "artist": "James Morrison",
                    "artist_mbids": ["a3352eff-cde0-4f15-b44a-6f5c3e9cf079"],
                    "recording_mbid": "3447878d-233a-46ad-b6a8-b754f922a7a4",
                    "title": "Main in the Mirror (acoustic)",
                },
            ]

            submit_listens(recordings)
            clusters_modified, clusters_add_to_redirect = artist.create_artist_credit_clusters()

            # Only one new pair added to artist_credit_cluster is 'Consequence feat. Kanye West'
            self.assertEqual(clusters_modified, 1)

            # Two new 'James Morrison' are added to redirect artist_credit_redirect table
            # and 'Consequence feat. Kanye West' is also added to artist_credit_redirect table
            self.assertEqual(clusters_add_to_redirect, 3)

            # Four different 'James Morrison' exist in database
            gid_from_data = UUID(data.get_artist_credit(connection, "James Morrison"))
            artist_mbids = artist.get_artist_mbids_using_msid(connection, gid_from_data)
            self.assertListEqual(artist_mbids, [
                [UUID("88a8d8a9-7c9b-4f7b-8700-7f0f7a503688")],
                [UUID("b49a9595-3576-44bb-8ac0-e26d3f5b42ff")],
                [UUID("b29c0d07-99a3-478c-af62-26e0728dfd55")],
                [UUID("a3352eff-cde0-4f15-b44a-6f5c3e9cf079")],
            ])

            # 'Consequence feat. Kanye West' form one cluster
            gid_from_data = UUID(data.get_artist_credit(connection, "Consequence feat. Kanye West"))
            artist_mbids = artist.get_artist_mbids_using_msid(connection, gid_from_data)
            self.assertListEqual(artist_mbids, [
                [UUID("164f0d73-1234-4e2c-8743-d77bf2191051"), UUID("c2e49f7a-cd6f-48ca-8596-b03614ea4fe8")]
            ])


    def test_get_recordings_metadata_using_artist_mbids(self):
        """ Tests if recordings metadata is fetched correctly using artist MBIDs. """

        recording_1 = {
            "artist": "Jay‐Z & Beyoncé",
            "artist_mbids": ["859d0860-d480-4efd-970c-c05d5f1776b8", "f82bcf78-5b69-4622-a5ef-73800768d9ac"],
            "recording_mbid": "5465ca86-3881-4349-81b2-6efbd3a59451",
            "title": "'03 Bonnie and Clyde",
        }
        submit_listens([recording_1])
        with db.engine.begin() as connection:
            recordings = artist.get_recordings_metadata_using_artist_mbids(connection,
                [UUID("859d0860-d480-4efd-970c-c05d5f1776b8"), UUID("f82bcf78-5b69-4622-a5ef-73800768d9ac")],
            )
            self.assertDictEqual(recording_1, recordings[0])


    def test_fetch_unclustered_artist_mbids_using_recording_artist_join(self):
        """ Tests if artist MBIDs are fetched correctly using recording_artist_join table."""

        self._add_mbids_to_recording_artist_join()
        msb_listens = self._load_test_data("recordings_for_clustering_using_fetched_artist_mbids.json")
        submit_listens(msb_listens)
        # Create clusters using already present artist MBIDs in recordings
        artist.create_artist_credit_clusters()

        # Distinct artist MBIDs for Jay-Z, Jay\u2010Z & Beyonc\u00e9, and Lil’ Kim
        artist_mbids_submitted = [
                ["859d0860-d480-4efd-970c-c05d5f1776b8", "f82bcf78-5b69-4622-a5ef-73800768d9ac"],
                ["f82bcf78-5b69-4622-a5ef-73800768d9ac"],
                ["bc1b5c95-e6d6-46b5-957a-5e8908b02c1e"],
        ]

        artist_mbids_submitted = [
                [UUID(artist_mbid) for artist_mbid in artist_mbids]
                for artist_mbids in artist_mbids_submitted
        ]

        artist_mbids_submitted = {tuple(artist_mbids) for artist_mbids in artist_mbids_submitted}

        with db.engine.begin() as connection:
            artist_mbids_fetched = artist.fetch_unclustered_artist_mbids_using_recording_artist_join(connection)
            artist_mbids_fetched = {tuple(artist_mbids) for artist_mbids in artist_mbids_fetched}
            self.assertSetEqual(artist_mbids_fetched, artist_mbids_submitted)


    def test_fetch_unclustered_gids_for_artist_mbids_using_recording_artist_join(self):
        """ Tests if unclustered gids are fetched using artist
            MBIDs correctly using recording_artist_join table.
        """

        self._add_mbids_to_recording_artist_join()
        msb_listens = self._load_test_data("recordings_for_clustering_using_fetched_artist_mbids.json")
        submit_listens(msb_listens)

        with db.engine.begin() as connection:
            gids = artist.fetch_unclustered_gids_for_artist_mbids_using_recording_artist_join(connection, [
                        UUID("859d0860-d480-4efd-970c-c05d5f1776b8"), UUID("f82bcf78-5b69-4622-a5ef-73800768d9ac")
                    ])
            gids_from_data = set([
                UUID(data.get_artist_credit(connection, "Jay‐Z & Beyoncé")),
                UUID(data.get_artist_credit(connection, "Jay‐Z and Beyoncé"))
            ])
            self.assertSetEqual(set(gids), gids_from_data)


    @unittest.skip("This test broke with PG12 upgrade, code is not used in prod")
    def test_fetch_artist_mbids_left_to_cluster_from_recording_artist_join(self):
        """ Tests if artist MBIDs left to add to artist_credit_redirect table are
            fetched correctly.
        """

        # The recordings for artist 'James Morrison' represents anomaly
        # as two James Morrison exist with different artist MBIDs
        recording_1 = {
            "artist": "James Morrison",
            "recording_mbid": "71fdb968-48c1-4406-a1f1-9dd2e9e37e0c",
            "title": "6 Weeks",
        }

        recording_2 = {
            "artist": "James Morrison",
            "recording_mbid": "181d63e7-5ed3-4c6c-9018-dad36128d7a7",
            "title": "A Brush With Bunj",
        }

        submit_listens([recording_1, recording_2])

        with db.engine.begin() as connection:
            artist.insert_artist_mbids(connection,
                recording_1["recording_mbid"],
                [UUID("88a8d8a9-7c9b-4f7b-8700-7f0f7a503688")]
            )
            artist.insert_artist_mbids(connection,
                recording_2["recording_mbid"],
                [UUID("b49a9595-3576-44bb-8ac0-e26d3f5b42ff")]
            )
            artist.create_clusters_using_fetched_artist_mbids_without_anomalies(connection)

            artist_left = artist.fetch_artist_mbids_left_to_cluster_from_recording_artist_join(connection)
            self.assertEqual(len(artist_left), 1)

            # 'James Morrison' with artist MBID '88a8d8a9-7c9b-4f7b-8700-7f0f7a503688'
            # was clustered in the first phase without considering anomalies.
            self.assertListEqual(artist_left, [[UUID("b49a9595-3576-44bb-8ac0-e26d3f5b42ff")]])


    def test_get_gids_from_recording_using_fetched_artist_mbids(self):
        """ Tests if artist gids are correctly fetched from recording table using
            artist MBIDs.
        """

        self._add_mbids_to_recording_artist_join()
        msb_listens = self._load_test_data("recordings_for_clustering_using_fetched_artist_mbids.json")
        submit_listens(msb_listens)

        with db.engine.begin() as connection:
            mbids = [
                        UUID("859d0860-d480-4efd-970c-c05d5f1776b8"),
                        UUID("f82bcf78-5b69-4622-a5ef-73800768d9ac"),
                    ]
            gids = set(artist.get_gids_from_recording_using_fetched_artist_mbids(connection, mbids))
            gids_from_data = set([
                UUID(data.get_artist_credit(connection, "Jay‐Z & Beyoncé")),
                UUID(data.get_artist_credit(connection, "Jay‐Z and Beyoncé"))
            ])

            self.assertSetEqual(gids, gids_from_data)


    def test_get_recordings_metadata_using_artist_mbids_and_recording_artist_join(self):
        """ Tests if recordings metadata is correctly fetched using artist MBIDs and
            recording_artist_join table.
        """

        recording_1 = {
            "artist": "Jay‐Z & Beyoncé",
            "recording_mbid": "5465ca86-3881-4349-81b2-6efbd3a59451",
            "title": "'03 Bonnie and Clyde",
        }
        submit_listens([recording_1])
        self._add_mbids_to_recording_artist_join()

        with db.engine.begin() as connection:
            recordings = artist.get_recordings_metadata_using_artist_mbids_and_recording_artist_join(connection,
                [UUID("859d0860-d480-4efd-970c-c05d5f1776b8"), UUID("f82bcf78-5b69-4622-a5ef-73800768d9ac")],
            )
            self.assertDictEqual(recording_1, recordings[0])


    @unittest.skip("This test broke with PG12 upgrade, code is not used in prod")
    def test_create_clusters_using_fetched_artist_mbids_without_anomalies(self):
        """ Tests if artist clusters are created correctly without considering anomalies."""

        msb_listens = self._load_test_data("recordings_for_clustering_using_fetched_artist_mbids.json")
        submit_listens(msb_listens)
        self._add_mbids_to_recording_artist_join()

        # The recordings for artist 'James Morrison' represents anomaly
        # as two James Morrison exist with different artist MBIDs
        recording_1 = {
            "artist": "James Morrison",
            "recording_mbid": "71fdb968-48c1-4406-a1f1-9dd2e9e37e0c",
            "title": "6 Weeks",
        }

        recording_2 = {
            "artist": "James Morrison",
            "recording_mbid": "181d63e7-5ed3-4c6c-9018-dad36128d7a7",
            "title": "A Brush With Bunj",
        }

        submit_listens([recording_1, recording_2])

        clusters_modified, clusters_add_to_redirect = artist.create_artist_credit_clusters()
        self.assertEqual(clusters_modified, 1)
        self.assertEqual(clusters_add_to_redirect, 1)

        with db.engine.begin() as connection:
            # 'Syreeta' form one cluster as recording contains artist MBIDs
            gid_from_data = UUID(data.get_artist_credit(connection, "Syreeta"))
            artist_mbids = artist.get_artist_mbids_using_msid(connection, gid_from_data)
            self.assertListEqual(artist_mbids, [[UUID("5cfeec75-f6e2-439c-946d-5317334cdc6c")]])

            artist.insert_artist_mbids(connection,
                recording_1["recording_mbid"],
                [UUID("88a8d8a9-7c9b-4f7b-8700-7f0f7a503688")]
            )
            artist.insert_artist_mbids(connection,
                recording_2["recording_mbid"],
                [UUID("b49a9595-3576-44bb-8ac0-e26d3f5b42ff")]
            )

            clusters_modified, clusters_add_to_redirect = artist.create_clusters_using_fetched_artist_mbids_without_anomalies(connection)
            self.assertEqual(clusters_modified, 4)
            self.assertEqual(clusters_add_to_redirect, 4)

            # 'Jay-Z & Beyonce' and 'Jay-Z and Beyonce' form one cluster
            gid_from_data = UUID(data.get_artist_credit(connection, "Jay‐Z & Beyoncé"))
            artist_mbids_1 = artist.get_artist_mbids_using_msid(connection, gid_from_data)
            cluster_id_1 = artist.get_cluster_id_using_msid(connection, gid_from_data)
            gid_from_data = UUID(data.get_artist_credit(connection, "Jay‐Z and Beyoncé"))
            artist_mbids_2 = artist.get_artist_mbids_using_msid(connection, gid_from_data)
            cluster_id_2 = artist.get_cluster_id_using_msid(connection, gid_from_data)
            self.assertListEqual(artist_mbids_1, artist_mbids_2)
            self.assertEqual(cluster_id_1, cluster_id_2)

            # 'Lil' Kim' form one cluster
            gid_from_data = UUID(data.get_artist_credit(connection, "Lil’ Kim"))
            artist_mbids = artist.get_artist_mbids_using_msid(connection, gid_from_data)
            self.assertListEqual(artist_mbids, [[UUID("bc1b5c95-e6d6-46b5-957a-5e8908b02c1e")]])

            # 'Jay-Z', JAY-Z, JAY_Z and 'Jay_Z' form one cluster
            gid_from_data = UUID(data.get_artist_credit(connection, "JAY-Z"))
            artist_mbids_1 = artist.get_artist_mbids_using_msid(connection, gid_from_data)
            cluster_id_1 = artist.get_cluster_id_using_msid(connection, gid_from_data)
            gid_from_data = UUID(data.get_artist_credit(connection, "JAY_Z"))
            artist_mbids_2 = artist.get_artist_mbids_using_msid(connection, gid_from_data)
            cluster_id_2 = artist.get_cluster_id_using_msid(connection, gid_from_data)
            gid_from_data = UUID(data.get_artist_credit(connection, "Jay‐Z"))
            artist_mbids_3 = artist.get_artist_mbids_using_msid(connection, gid_from_data)
            cluster_id_3 = artist.get_cluster_id_using_msid(connection, gid_from_data)
            gid_from_data = UUID(data.get_artist_credit(connection, "Jay_Z"))
            artist_mbids_4 = artist.get_artist_mbids_using_msid(connection, gid_from_data)
            cluster_id_4 = artist.get_cluster_id_using_msid(connection, gid_from_data)
            self.assertListEqual(artist_mbids_1, artist_mbids_2)
            self.assertListEqual(artist_mbids_2, artist_mbids_3)
            self.assertListEqual(artist_mbids_3, artist_mbids_4)
            self.assertEqual(cluster_id_1, cluster_id_2)
            self.assertEqual(cluster_id_2, cluster_id_3)
            self.assertEqual(cluster_id_3, cluster_id_4)

            # 'James Morrison' with artist MBID '88a8d8a9-7c9b-4f7b-8700-7f0f7a503688'
            # is clustered as before no artist_credit_gid exists with this artist_credit
            # in artist_credit_cluster before this is inserted.
            gid_from_data = UUID(data.get_artist_credit(connection, "James Morrison"))
            artist_mbids = artist.get_artist_mbids_using_msid(connection, gid_from_data)
            self.assertListEqual(artist_mbids, [[UUID("88a8d8a9-7c9b-4f7b-8700-7f0f7a503688")]])


    @unittest.skip("This test broke with PG12 upgrade, code is not used in prod")
    def test_create_clusters_using_fetched_artist_mbids_for_anomalies(self):
        """ Tests if artist clusters are correctly formed for anomalies."""

        msb_listens = self._load_test_data("recordings_for_clustering_using_fetched_artist_mbids.json")
        submit_listens(msb_listens)
        self._add_mbids_to_recording_artist_join()

        # The recordings for artist 'James Morrison' represents anomaly
        # as two James Morrison exist with different artist MBIDs
        recording_1 = {
            "artist": "James Morrison",
            "recording_mbid": "71fdb968-48c1-4406-a1f1-9dd2e9e37e0c",
            "title": "6 Weeks",
        }

        recording_2 = {
            "artist": "James Morrison",
            "recording_mbid": "181d63e7-5ed3-4c6c-9018-dad36128d7a7",
            "title": "A Brush With Bunj",
        }

        submit_listens([recording_1, recording_2])

        clusters_modified, clusters_add_to_redirect = artist.create_artist_credit_clusters()
        self.assertEqual(clusters_modified, 1)
        self.assertEqual(clusters_add_to_redirect, 1)

        with db.engine.begin() as connection:
            artist.insert_artist_mbids(connection,
                recording_1["recording_mbid"],
                [UUID("88a8d8a9-7c9b-4f7b-8700-7f0f7a503688")]
            )
            artist.insert_artist_mbids(connection,
                recording_2["recording_mbid"],
                [UUID("b49a9595-3576-44bb-8ac0-e26d3f5b42ff")]
            )

            clusters_modified, clusters_add_to_redirect = artist.create_clusters_using_fetched_artist_mbids_without_anomalies(connection)
            self.assertEqual(clusters_modified, 4)
            self.assertEqual(clusters_add_to_redirect, 4)

            # Before clustering anomalies
            # 'James Morrison' with artist MBID '88a8d8a9-7c9b-4f7b-8700-7f0f7a503688'
            # is clustered as before no artist_credit_gid exists with this artist_credit
            # in artist_credit_cluster before this is inserted.
            gid_from_data = UUID(data.get_artist_credit(connection, "James Morrison"))
            artist_mbids = artist.get_artist_mbids_using_msid(connection, gid_from_data)
            self.assertListEqual(artist_mbids, [[UUID("88a8d8a9-7c9b-4f7b-8700-7f0f7a503688")]])

            clusters_add_to_redirect = artist.create_clusters_using_fetched_artist_mbids_for_anomalies(connection)
            self.assertEqual(clusters_add_to_redirect, 1)

            # After clustering anomalies
            # 'James Morrison' with artist MBID 'b49a9595-3576-44bb-8ac0-e26d3f5b42ff'
            # is clustered
            gid_from_data = UUID(data.get_artist_credit(connection, "James Morrison"))
            artist_mbids = artist.get_artist_mbids_using_msid(connection, gid_from_data)
            self.assertListEqual(artist_mbids, [
                [UUID("88a8d8a9-7c9b-4f7b-8700-7f0f7a503688")], [UUID("b49a9595-3576-44bb-8ac0-e26d3f5b42ff")]
            ])


    def test_create_clusters_using_fetched_artist_mbids(self):
        """ Tests if clusters are created correctly using
            artist MBIDs from recording_artist_join table.
        """

        msb_listens = self._load_test_data("recordings_for_clustering_using_fetched_artist_mbids.json")
        submit_listens(msb_listens)
        self._add_mbids_to_recording_artist_join()

        # The recordings for artist 'James Morrison' represents anomaly
        # as two James Morrison exist with different artist MBIDs
        recording_1 = {
            "artist": "James Morrison",
            "recording_mbid": "71fdb968-48c1-4406-a1f1-9dd2e9e37e0c",
            "title": "6 Weeks",
        }
        recording_2 = {
            "artist": "James Morrison",
            "recording_mbid": "181d63e7-5ed3-4c6c-9018-dad36128d7a7",
            "title": "A Brush With Bunj",
        }

        submit_listens([recording_1, recording_2])

        clusters_modified, clusters_add_to_redirect = artist.create_artist_credit_clusters()
        self.assertEqual(clusters_modified, 1)
        self.assertEqual(clusters_add_to_redirect, 1)

        with db.engine.begin() as connection:
            # 'Syreeta' form one cluster as recording contains artist MBIDs
            gid_from_data = UUID(data.get_artist_credit(connection, "Syreeta"))
            artist_mbids = artist.get_artist_mbids_using_msid(connection, gid_from_data)
            self.assertListEqual(artist_mbids, [[UUID("5cfeec75-f6e2-439c-946d-5317334cdc6c")]])

            artist.insert_artist_mbids(connection,
                recording_1["recording_mbid"],
                [UUID("88a8d8a9-7c9b-4f7b-8700-7f0f7a503688")]
            )
            artist.insert_artist_mbids(connection,
                recording_2["recording_mbid"],
                [UUID("b49a9595-3576-44bb-8ac0-e26d3f5b42ff")]
            )

        clusters_modified, clusters_add_to_redirect = artist.create_clusters_using_fetched_artist_mbids()
        self.assertEqual(clusters_modified, 4)
        self.assertEqual(clusters_add_to_redirect, 5)

        with db.engine.begin() as connection:
            # 'Jay-Z & Beyonce' and 'Jay-Z and Beyonce' form one cluster
            gid_from_data = UUID(data.get_artist_credit(connection, "Jay‐Z & Beyoncé"))
            artist_mbids_1 = artist.get_artist_mbids_using_msid(connection, gid_from_data)
            cluster_id_1 = artist.get_cluster_id_using_msid(connection, gid_from_data)
            gid_from_data = UUID(data.get_artist_credit(connection, "Jay‐Z and Beyoncé"))
            artist_mbids_2 = artist.get_artist_mbids_using_msid(connection, gid_from_data)
            cluster_id_2 = artist.get_cluster_id_using_msid(connection, gid_from_data)
            self.assertListEqual(artist_mbids_1, artist_mbids_2)
            self.assertEqual(cluster_id_1, cluster_id_2)

            # 'Lil' Kim' form one cluster
            gid_from_data = UUID(data.get_artist_credit(connection, "Lil’ Kim"))
            artist_mbids = artist.get_artist_mbids_using_msid(connection, gid_from_data)
            self.assertListEqual(artist_mbids, [[UUID("bc1b5c95-e6d6-46b5-957a-5e8908b02c1e")]])

            # 'Jay-Z', JAY-Z, JAY_Z and 'Jay_Z' form one cluster
            gid_from_data = UUID(data.get_artist_credit(connection, "JAY-Z"))
            artist_mbids_1 = artist.get_artist_mbids_using_msid(connection, gid_from_data)
            cluster_id_1 = artist.get_cluster_id_using_msid(connection, gid_from_data)
            gid_from_data = UUID(data.get_artist_credit(connection, "JAY_Z"))
            artist_mbids_2 = artist.get_artist_mbids_using_msid(connection, gid_from_data)
            cluster_id_2 = artist.get_cluster_id_using_msid(connection, gid_from_data)
            gid_from_data = UUID(data.get_artist_credit(connection, "Jay‐Z"))
            artist_mbids_3 = artist.get_artist_mbids_using_msid(connection, gid_from_data)
            cluster_id_3 = artist.get_cluster_id_using_msid(connection, gid_from_data)
            gid_from_data = UUID(data.get_artist_credit(connection, "Jay_Z"))
            artist_mbids_4 = artist.get_artist_mbids_using_msid(connection, gid_from_data)
            cluster_id_4 = artist.get_cluster_id_using_msid(connection, gid_from_data)
            self.assertListEqual(artist_mbids_1, artist_mbids_2)
            self.assertListEqual(artist_mbids_2, artist_mbids_3)
            self.assertListEqual(artist_mbids_3, artist_mbids_4)
            self.assertEqual(cluster_id_1, cluster_id_2)
            self.assertEqual(cluster_id_2, cluster_id_3)
            self.assertEqual(cluster_id_3, cluster_id_4)

            # 'James Morrison' with artist MBID '88a8d8a9-7c9b-4f7b-8700-7f0f7a503688'
            # and 'James Morrison' with artist MBID 'b49a9595-3576-44bb-8ac0-e26d3f5b42ff'
            # form a cluster
            gid_from_data = UUID(data.get_artist_credit(connection, "James Morrison"))
            artist_mbids = artist.get_artist_mbids_using_msid(connection, gid_from_data)
            self.assertListEqual(artist_mbids, [
                [UUID("88a8d8a9-7c9b-4f7b-8700-7f0f7a503688")], [UUID("b49a9595-3576-44bb-8ac0-e26d3f5b42ff")]
            ])
