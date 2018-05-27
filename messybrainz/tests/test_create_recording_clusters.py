import json
from messybrainz import submit_listens_and_sing_me_a_sweet_song as submit_listens
from messybrainz import db
from messybrainz import data
from messybrainz.testing import DatabaseTestCase
from messybrainz.create_recording_clusters import fetch_distinct_recording_mbids,\
                                                fetch_gids_for_recording_mbid,\
                                                is_recording_cluster_present_in_recording_redirect,\
                                                is_recording_cluster_present_in_recording_cluster,\
                                                link_recording_mbid_to_recording_msid,\
                                                insert_recording_cluster,\
                                                create_recording_clusters


class CreateRecordingClustersTestCase(DatabaseTestCase):
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


    def test_fetch_distinct_recording_mbids(self):
        """Tests if recording_mbids are correctly fetched from recording_json table."""

        msb_listens = self._load_test_data('valid_recordings_with_recording_mbids.json')
        submit_listens(msb_listens)
        recording_mbids_submitted = {'5465ca86-3881-4349-81b2-6efbd3a59451',
            '6ba092ae-aaf7-4154-b987-9eb9d05f8616',
            'cad174ad-d683-4858-a205-7bdc4175fff7',
        }
        with db.engine.begin() as connection:
            recording_mbids = fetch_distinct_recording_mbids(connection)
            self.assertEqual(recording_mbids.rowcount, 3)

            recording_mbids_fetched = set()
            for recording_mbid in recording_mbids:
                recording_mbids_fetched.add(str(recording_mbid[0]))

            self.assertSetEqual(recording_mbids_submitted, recording_mbids_fetched)


    def test_fetch_gids_for_recording_mbid(self):
        """Tests if gids are correctly fetched."""

        recording_1 = {
            "artist": "Jay‐Z & Beyoncé",
            "title": "'03 Bonnie & Clyde",
            "recording_mbid": "5465ca86-3881-4349-81b2-6efbd3a59451"
        }
        submit_listens([recording_1])

        recording_2 = {
            "artist": "Jay‐Z and Beyoncé",
            "title": "'03 Bonnie & Clyde",
            "recording_mbid": "5465ca86-3881-4349-81b2-6efbd3a59451"
        }
        submit_listens([recording_2])

        with db.engine.begin() as connection:
            gids = fetch_gids_for_recording_mbid(connection, '5465ca86-3881-4349-81b2-6efbd3a59451')
            gid_fetched = set(gids)
            gid_from_data = set([data.get_id_from_recording(connection, recording_1),
                data.get_id_from_recording(connection, recording_2),
            ])

            self.assertSetEqual(gid_fetched, gid_from_data)


    def test_is_recording_cluster_present_in_recording_redirect(self):
        """Tests if proper value is returned if an ID is present in recording_redirect table."""

        recording = {
            "artist": "Jay‐Z & Beyoncé",
            "title": "'03 Bonnie & Clyde",
            "recording_mbid": "5465ca86-3881-4349-81b2-6efbd3a59451"
        }
        submit_listens([recording])
        mbid = recording["recording_mbid"]
        with db.engine.begin() as connection:
            gids = fetch_gids_for_recording_mbid(connection, mbid)
            insert_recording_cluster(connection, gids[0], gids)
            link_recording_mbid_to_recording_msid(connection, gids[0], mbid)
            result = is_recording_cluster_present_in_recording_redirect(connection, gids[0], mbid)
            self.assertTrue(result)


    def test_is_recording_cluster_present_in_recording_cluster(self):
        """Tests if proper value is returned if an ID is present in recording_cluster table."""

        recording = {
            "artist": "Jay‐Z & Beyoncé",
            "title": "'03 Bonnie & Clyde",
            "recording_mbid": "5465ca86-3881-4349-81b2-6efbd3a59451"
        }
        submit_listens([recording])
        mbid = recording["recording_mbid"]
        with db.engine.begin() as connection:
            gids = fetch_gids_for_recording_mbid(connection, mbid)
            insert_recording_cluster(connection, gids[0], gids)
            result = is_recording_cluster_present_in_recording_cluster(connection, gids[0], gids[0])
            self.assertTrue(result)


    def test_link_recording_mbid_to_recording_msid(self):
        """Tests if MBIDs are linked to MSIDs correctly."""

        recording = {
            "artist": "Jay‐Z & Beyoncé",
            "title": "'03 Bonnie & Clyde",
            "recording_mbid": "5465ca86-3881-4349-81b2-6efbd3a59451"
        }
        submit_listens([recording])
        mbid = recording["recording_mbid"]
        with db.engine.begin() as connection:
            msid = data.get_id_from_recording(connection, recording)
            result = is_recording_cluster_present_in_recording_redirect(connection, msid, mbid)
            self.assertFalse(result)
            link_recording_mbid_to_recording_msid(connection, msid, mbid)
            result = is_recording_cluster_present_in_recording_redirect(connection, msid, mbid)
            self.assertTrue(result)


    def test_insert_recording_cluster(self):
        """Tests if clusters are inserted properly into recording_cluster table."""

        recording_1 = {
            "artist": "Jay‐Z & Beyoncé",
            "title": "'03 Bonnie & Clyde",
            "recording_mbid": "5465ca86-3881-4349-81b2-6efbd3a59451"
        }
        submit_listens([recording_1])

        recording_2 = {
            "artist": "Jay‐Z and Beyoncé",
            "title": "'03 Bonnie & Clyde",
            "recording_mbid": "5465ca86-3881-4349-81b2-6efbd3a59451"
        }
        submit_listens([recording_2])

        with db.engine.begin() as connection:
            recording_gids = fetch_gids_for_recording_mbid(connection, '5465ca86-3881-4349-81b2-6efbd3a59451')
            result = is_recording_cluster_present_in_recording_cluster(connection, recording_gids[0], recording_gids[0])
            self.assertFalse(result)
            result = is_recording_cluster_present_in_recording_cluster(connection, recording_gids[0], recording_gids[1])
            self.assertFalse(result)
            insert_recording_cluster(connection, recording_gids[0], recording_gids)
            result = is_recording_cluster_present_in_recording_cluster(connection, recording_gids[0], recording_gids[0])
            self.assertTrue(result)
            result = is_recording_cluster_present_in_recording_cluster(connection, recording_gids[0], recording_gids[1])
            self.assertTrue(result)


    def test_create_recording_clusters(self):
        """Tests the create_recording_clusters to make sure clusters are created properly."""

        msb_listens = self._load_test_data('data_for_creating_recording_cluster.json')
        submit_listens(msb_listens)

        # Create clusters with empty recording_cluster, recording_redirect tables.
        clusters_modified, clusters_add_to_redirect, num_msid_processed = create_recording_clusters(reset=True)
        self.assertEqual(clusters_modified, 4)
        self.assertEqual(clusters_add_to_redirect, 4)
        self.assertEqual(num_msid_processed, 7)

        # Create clusters again to make sure duplication of data does not take place.
        clusters_modified, clusters_add_to_redirect, num_msid_processed = create_recording_clusters(reset=False)
        self.assertEqual(clusters_modified, 0)
        self.assertEqual(clusters_add_to_redirect, 0)
        self.assertEqual(num_msid_processed, 7)

        # Add new recordings and create clusters again.
        recording_1 = {
            "artist": "Memphis Minnie",
            "title": "Banana Man Blues",
            "recording_mbid": "e1efdbee-2904-437f-b0e2-dbb4906b86d2",
        }

        recording_2 = {
            "artist": "Jay-Z & Beyonce",
            "title": "'03 Bonnie & Clyde",
            "recording_mbid": "5465ca86-3881-4349-81b2-6efbd3a59451"
        }
        submit_listens([recording_1, recording_2])

        clusters_modified, clusters_add_to_redirect, num_msid_processed = create_recording_clusters(reset=False)
        self.assertEqual(clusters_modified, 2)
        self.assertEqual(clusters_add_to_redirect, 1)
        self.assertEqual(num_msid_processed, 9)
