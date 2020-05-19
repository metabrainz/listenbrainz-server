import json
import unittest

from messybrainz import submit_listens_and_sing_me_a_sweet_song as submit_listens
from messybrainz import db
from messybrainz.db import data
from messybrainz.db.testing import DatabaseTestCase
from messybrainz.db import release
from messybrainz.db.release import fetch_unclustered_distinct_release_mbids,\
                                    fetch_unclustered_gids_for_release_mbid,\
                                    link_release_mbid_to_release_msid,\
                                    get_release_cluster_id_using_release_mbid,\
                                    insert_release_cluster,\
                                    fetch_release_left_to_cluster,\
                                    create_release_clusters_without_considering_anomalies,\
                                    get_cluster_id_using_msid,\
                                    create_release_clusters,\
                                    get_release_gids_from_recording_json_using_mbid,\
                                    get_release_mbids_using_msid,\
                                    create_release_clusters_for_anomalies,\
                                    get_recordings_metadata_using_release_mbid
from unittest.mock import patch
from uuid import UUID


class ReleaseTestCase(DatabaseTestCase):
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


    def test_fetch_unclustered_distinct_release_mbids(self):
        """Tests if release_mbids are correctly fetched from recording_json table."""

        msb_listens = self._load_test_data('recordings_for_release_clusters.json')
        submit_listens(msb_listens)
        release_mbids_submitted = {'7111c8bc-8549-4abc-8ab9-db13f65b4a55',
            '5f7853be-1f7a-4850-b0b8-2333d6b0318f',
            '09701309-2f7b-4537-a066-daa1c79b3f06',
            'd75e103c-5ef4-4146-ae81-e27d19dc7fc4',
            '2c5e4198-24cf-3c95-a16e-83be8e877dfa',
            'e8c8bbf8-15c1-477f-af5b-2c1479af037e',
            '801678aa-5d30-4342-8227-e9618f164cca',
        }
        with db.engine.begin() as connection:
            release_mbids_fetched = fetch_unclustered_distinct_release_mbids(connection)
            self.assertEqual(len(release_mbids_fetched), 7)
            self.assertSetEqual(release_mbids_submitted, set(release_mbids_fetched))


    def test_fetch_unclustered_gids_for_release_mbid(self):
        """Tests if gids are correctly fetched."""

        # recording_1 and recording_2 differ in the name of release
        # for recording_1 release has 'and' and for recording_2
        # release has '&'
        recording_1 = {
            "artist": "Jay‐Z & Beyoncé",
            "title": "'03 Bonnie & Clyde",
            "recording_mbid": "5465ca86-3881-4349-81b2-6efbd3a59451",
            "release_mbid": "2c5e4198-24cf-3c95-a16e-83be8e877dfa",
            "release": "The Blueprint\u00b2: The Gift and The Curse",
        }

        recording_2 = {
            "artist": "Jay‐Z & Beyoncé",
            "title": "'03 Bonnie & Clyde",
            "recording_mbid": "5465ca86-3881-4349-81b2-6efbd3a59451",
            "release_mbid": "2c5e4198-24cf-3c95-a16e-83be8e877dfa",
            "release":"The Blueprint\u00b2: The Gift & The Curse",
        }
        submit_listens([recording_1, recording_2])

        with db.engine.begin() as connection:
            gids = fetch_unclustered_gids_for_release_mbid(connection, '2c5e4198-24cf-3c95-a16e-83be8e877dfa')
            gid_fetched = set(gids)
            gid_from_data = set([UUID(data.get_release(connection, recording_1['release'])),
                UUID(data.get_release(connection, recording_2['release'])),
            ])

            self.assertSetEqual(gid_fetched, gid_from_data)


    def test_link_release_mbid_to_release_msid(self):
        """Tests if MBIDs are linked to MSIDs correctly."""

        recording = {
            "artist": "Jay‐Z & Beyoncé",
            "title": "'03 Bonnie & Clyde",
            "release_mbid": "2c5e4198-24cf-3c95-a16e-83be8e877dfa",
            "release":"The Blueprint\u00b2: The Gift & The Curse",
        }
        submit_listens([recording])
        mbid = recording['release_mbid']
        with db.engine.begin() as connection:
            msid = UUID(data.get_release(connection, recording['release']))
            result = get_release_cluster_id_using_release_mbid(connection, mbid)
            self.assertIsNone(result)
            link_release_mbid_to_release_msid(connection, msid, mbid)
            result = get_release_cluster_id_using_release_mbid(connection, mbid)
            self.assertEqual(msid, result)


    def test_insert_release_cluster(self):
        """Tests if clusters are inserted properly into release_cluster table."""

        # recording_1 and recording_2 differ in the name of release
        # for recording_1 release has 'and' and for recording_2
        # release has '&'
        recording_1 = {
            "artist": "Jay‐Z & Beyoncé",
            "title": "'03 Bonnie & Clyde",
            "recording_mbid": "5465ca86-3881-4349-81b2-6efbd3a59451",
            "release_mbid": "2c5e4198-24cf-3c95-a16e-83be8e877dfa",
            "release": "The Blueprint\u00b2: The Gift and The Curse",
        }

        recording_2 = {
            "artist": "Jay‐Z & Beyoncé",
            "title": "'03 Bonnie & Clyde",
            "recording_mbid": "5465ca86-3881-4349-81b2-6efbd3a59451",
            "release_mbid": "2c5e4198-24cf-3c95-a16e-83be8e877dfa",
            "release":"The Blueprint\u00b2: The Gift & The Curse",
        }
        submit_listens([recording_1, recording_2])

        with db.engine.begin() as connection:
            release_gids = fetch_unclustered_gids_for_release_mbid(connection, '2c5e4198-24cf-3c95-a16e-83be8e877dfa')
            insert_release_cluster(connection, release_gids[0], release_gids)
            release_gids = fetch_unclustered_gids_for_release_mbid(connection, '2c5e4198-24cf-3c95-a16e-83be8e877dfa')
            self.assertEqual(len(release_gids), 0)


    def test_fetch_release_left_to_cluster(self):
        """Tests if release left to cluster after first
           pass are correctly fetched.
        """

        msb_listens = self._load_test_data("recordings_for_release_clusters.json")
        submit_listens(msb_listens)

        with db.engine.begin() as connection:
            create_release_clusters_without_considering_anomalies(connection)
            # In the data used from recordings_for_release_clusters
            # the recordings for release 'The Blueprint\u00b2: The Gift & The Curse'
            # represents anomaly as two release_mbids exists for this release
            # (2c5e4198-24cf-3c95-a16e-83be8e877dfa, 801678aa-5d30-4342-8227-e9618f164cca)
            # and release 'The Notorious KIM' also represents two release_mbids
            # (e8c8bbf8-15c1-477f-af5b-2c1479af037e, 09701309-2f7b-4537-a066-daa1c79b3f06)

            release_left = fetch_release_left_to_cluster(connection)
            self.assertEqual(len(release_left), 2)

            # 'The Blueprint\u00b2: The Gift & The Curse' with release MBID '2c5e4198-24cf-3c95-a16e-83be8e877dfa'
            # was clustered in the first phase, The Notorious KIM' with release MBID
            # '09701309-2f7b-4537-a066-daa1c79b3f06' was clustered in first phase.

            self.assertSetEqual(set(release_left),
                set(['801678aa-5d30-4342-8227-e9618f164cca', 'e8c8bbf8-15c1-477f-af5b-2c1479af037e'])
            )


    def test_get_cluster_id_using_msid(self):
        """Tests if cluster_id is correctly retrived using any MSID for the cluster."""

        msb_listens = self._load_test_data("recordings_for_release_clusters.json")
        submit_listens(msb_listens)

        create_release_clusters()
        with db.engine.begin() as connection:
            gid_from_data = data.get_release(connection, "The Blueprint\u00b2: The Gift & The Curse")
            cluster_id_1 = get_cluster_id_using_msid(connection, gid_from_data)
            gid_from_data = data.get_release(connection, "The Blueprint\u00b2: The Gift and The Curse")
            cluster_id_2 = get_cluster_id_using_msid(connection, gid_from_data)

            self.assertEqual(cluster_id_1, cluster_id_2)


    def test_get_release_gids_from_recording_json_using_mbids(self):
        """Tests if release_gids are correctly fetched using a given release MBID"""

        msb_listens = self._load_test_data("recordings_for_release_clusters.json")
        submit_listens(msb_listens)

        with db.engine.begin() as connection:
            mbid = UUID("2c5e4198-24cf-3c95-a16e-83be8e877dfa")
            gids = set(get_release_gids_from_recording_json_using_mbid(connection, mbid))
            gids_from_data = set([
                UUID(data.get_release(connection, "The Blueprint\u00b2: The Gift & The Curse")),
                UUID(data.get_release(connection, "The Blueprint\u00b2: The Gift and The Curse")),
            ])

            self.assertSetEqual(gids, gids_from_data)


    def test_get_release_mbids_using_msid(self):
        """Test if release_mbid are fetched correctly for a given MSID"""

        msb_listens = self._load_test_data("recordings_for_release_clusters.json")
        submit_listens(msb_listens)
        create_release_clusters()

        with db.engine.begin() as connection:
            gid_from_data = UUID(data.get_release(connection, "The Blueprint\u00b2: The Gift & The Curse"))
            release_mbid_1 = get_release_mbids_using_msid(connection, gid_from_data)
            gid_from_data = UUID(data.get_release(connection, "The Blueprint\u00b2: The Gift and The Curse"))
            release_mbid_2 = get_release_mbids_using_msid(connection, gid_from_data)
            self.assertEqual(release_mbid_1, release_mbid_2)


    def test_create_release_clusters_without_considering_anomalies(self):
        """Tests if clusters are created without considering anomalies are
           are correctly formed.
        """

        msb_listens = self._load_test_data("recordings_for_release_clusters.json")
        submit_listens(msb_listens)

        with db.engine.begin() as connection:
            clusters_modified, clusters_add_to_redirect = create_release_clusters_without_considering_anomalies(connection)
            self.assertEqual(clusters_modified, 5)
            self.assertEqual(clusters_add_to_redirect, 5)

            # 'The Blueprint\u00b2: The Gift & The Curse' and 'The Blueprint\u00b2: The Gift and The Curse'
            # form one cluster
            gid_from_data = UUID(data.get_release(connection, "The Blueprint\u00b2: The Gift & The Curse"))
            release_mbids_1 = get_release_mbids_using_msid(connection, gid_from_data)
            cluster_id_1 = get_cluster_id_using_msid(connection, gid_from_data)
            gid_from_data = UUID(data.get_release(connection, "The Blueprint\u00b2: The Gift and The Curse"))
            release_mbids_2 = get_release_mbids_using_msid(connection, gid_from_data)
            cluster_id_2 = get_cluster_id_using_msid(connection, gid_from_data)
            self.assertListEqual(release_mbids_1, release_mbids_2)
            self.assertEqual(cluster_id_1, cluster_id_2)

            # 'The Blueprint Collector's Edition' form one cluster
            gid_from_data = UUID(data.get_release(connection, "The Blueprint Collector's Edition"))
            release_mbids = get_release_mbids_using_msid(connection, gid_from_data)
            self.assertListEqual(release_mbids, [UUID("d75e103c-5ef4-4146-ae81-e27d19dc7fc4")])

            # 'Syreeta' form one cluster
            gid_from_data = UUID(data.get_release(connection, "Syreeta"))
            release_mbids = get_release_mbids_using_msid(connection, gid_from_data)
            self.assertListEqual(release_mbids, [UUID("5f7853be-1f7a-4850-b0b8-2333d6b0318f")])

            # 'Blueprint 2.1' form one cluster
            gid_from_data = UUID(data.get_release(connection, "Blueprint 2.1"))
            release_mbids = get_release_mbids_using_msid(connection, gid_from_data)
            self.assertListEqual(release_mbids, [UUID("7111c8bc-8549-4abc-8ab9-db13f65b4a55")])

            # 'The Notorious KIM' with MBID '09701309-2f7b-4537-a066-daa1c79b3f06' form one cluster
            gid_from_data = UUID(data.get_release(connection, "The Notorious KIM"))
            release_mbids = get_release_mbids_using_msid(connection, gid_from_data)
            self.assertListEqual(release_mbids, [UUID("09701309-2f7b-4537-a066-daa1c79b3f06")])


    def test_create_release_clusters_for_anomalies(self):
        """Tests if clusters are created correctly for the anomalies."""

        msb_listens = self._load_test_data("recordings_for_release_clusters.json")
        submit_listens(msb_listens)

        with db.engine.begin() as connection:
            clusters_modified, clusters_add_to_redirect = create_release_clusters_without_considering_anomalies(connection)
            self.assertEqual(clusters_modified, 5)
            self.assertEqual(clusters_add_to_redirect, 5)

            # Before clustering anomalies
            # 'The Notorious KIM' with release MBID '09701309-2f7b-4537-a066-daa1c79b3f06'
            # is clustered as before no release_gid exists with this release
            # in release_cluster table before this is inserted.
            # 'The Blueprint\u00b2: The Gift & The Curse' with release MBID '2c5e4198-24cf-3c95-a16e-83be8e877dfa'
            # has been clustered.
            gid_from_data = UUID(data.get_release(connection, "The Notorious KIM"))
            release_mbids = get_release_mbids_using_msid(connection, gid_from_data)
            self.assertListEqual(release_mbids, [UUID("09701309-2f7b-4537-a066-daa1c79b3f06")])

            gid_from_data = UUID(data.get_release(connection, "The Blueprint\u00b2: The Gift & The Curse"))
            release_mbids = get_release_mbids_using_msid(connection, gid_from_data)
            self.assertListEqual(release_mbids, [UUID("2c5e4198-24cf-3c95-a16e-83be8e877dfa")])

            clusters_add_to_redirect = create_release_clusters_for_anomalies(connection)
            self.assertEqual(clusters_add_to_redirect, 2)

            # After clustering anomalies
            # 'The Notorious KIM' with release MBID 'e8c8bbf8-15c1-477f-af5b-2c1479af037e'
            # is clustered and 'The Blueprint\u00b2: The Gift & The Curse' with release MBID
            # '801678aa-5d30-4342-8227-e9618f164cca' is clustered
            gid_from_data = UUID(data.get_release(connection, "The Notorious KIM"))
            release_mbids = set(get_release_mbids_using_msid(connection, gid_from_data))
            self.assertSetEqual(release_mbids, set([
                UUID("09701309-2f7b-4537-a066-daa1c79b3f06"),
                UUID("e8c8bbf8-15c1-477f-af5b-2c1479af037e"),
            ]))

            gid_from_data = UUID(data.get_release(connection, "The Blueprint\u00b2: The Gift & The Curse"))
            release_mbids = set(get_release_mbids_using_msid(connection, gid_from_data))
            self.assertSetEqual(release_mbids, set([
                UUID("2c5e4198-24cf-3c95-a16e-83be8e877dfa"),
                UUID("801678aa-5d30-4342-8227-e9618f164cca"),
            ]))


    def test_create_release_clusters(self):
        """Tests if release clusters are correctly formed."""

        msb_listens = self._load_test_data("recordings_for_release_clusters.json")
        submit_listens(msb_listens)
        clusters_modified, clusters_add_to_redirect = create_release_clusters()
        self.assertEqual(clusters_modified, 5)
        self.assertEqual(clusters_add_to_redirect, 7)

        with db.engine.begin() as connection:
            # 'The Blueprint\u00b2: The Gift & The Curse' and 'The Blueprint\u00b2: The Gift and The Curse'
            # form one cluster
            gid_from_data = UUID(data.get_release(connection, "The Blueprint\u00b2: The Gift & The Curse"))
            release_mbids_1 = get_release_mbids_using_msid(connection, gid_from_data)
            cluster_id_1 = get_cluster_id_using_msid(connection, gid_from_data)
            gid_from_data = UUID(data.get_release(connection, "The Blueprint\u00b2: The Gift and The Curse"))
            release_mbids_2 = get_release_mbids_using_msid(connection, gid_from_data)
            cluster_id_2 = get_cluster_id_using_msid(connection, gid_from_data)
            self.assertListEqual(release_mbids_1, release_mbids_2)
            self.assertEqual(cluster_id_1, cluster_id_2)

            # 'The Blueprint Collector's Edition' form one cluster
            gid_from_data = UUID(data.get_release(connection, "The Blueprint Collector's Edition"))
            release_mbids = get_release_mbids_using_msid(connection, gid_from_data)
            self.assertListEqual(release_mbids, [UUID("d75e103c-5ef4-4146-ae81-e27d19dc7fc4")])

            # 'Syreeta' form one cluster
            gid_from_data = UUID(data.get_release(connection, "Syreeta"))
            release_mbids = get_release_mbids_using_msid(connection, gid_from_data)
            self.assertListEqual(release_mbids, [UUID("5f7853be-1f7a-4850-b0b8-2333d6b0318f")])

            # 'Blueprint 2.1' form one cluster
            gid_from_data = UUID(data.get_release(connection, "Blueprint 2.1"))
            release_mbids = get_release_mbids_using_msid(connection, gid_from_data)
            self.assertListEqual(release_mbids, [UUID("7111c8bc-8549-4abc-8ab9-db13f65b4a55")])

            # After clustering anomalies
            # 'The Notorious KIM' with MBID '09701309-2f7b-4537-a066-daa1c79b3f06',
            # 'e8c8bbf8-15c1-477f-af5b-2c1479af037e' form one cluster
            gid_from_data = UUID(data.get_release(connection, "The Notorious KIM"))
            release_mbids = set(get_release_mbids_using_msid(connection, gid_from_data))
            self.assertSetEqual(release_mbids, set([
                UUID("09701309-2f7b-4537-a066-daa1c79b3f06"),
                UUID("e8c8bbf8-15c1-477f-af5b-2c1479af037e"),
            ]))

            # 'The Blueprint\u00b2: The Gift & The Curse' with MBID '2c5e4198-24cf-3c95-a16e-83be8e877dfa',
            # '801678aa-5d30-4342-8227-e9618f164cca' form one cluster
            gid_from_data = UUID(data.get_release(connection, "The Blueprint\u00b2: The Gift & The Curse"))
            release_mbids = set(get_release_mbids_using_msid(connection, gid_from_data))
            self.assertSetEqual(release_mbids, set([
                UUID("2c5e4198-24cf-3c95-a16e-83be8e877dfa"),
                UUID("801678aa-5d30-4342-8227-e9618f164cca"),
            ]))

            # Inserting new recordings
            # recording_1 is already clustered
            recording_1 = {
                "artist": "Jay‐Z and Beyoncé",
                "title": "'03 Bonnie and Clyde",
                "release_mbid": "2c5e4198-24cf-3c95-a16e-83be8e877dfa",
                "release": "The Blueprint\u00b2: The Gift and The Curse",
            }
            # recording_2, recording_3 are new recordings
            recording_2 = {
                "artist": "Donal Leace",
                "title": "Today Won't Come Again",
                "release_mbid": "2b82a22b-0492-44be-bfd8-d1cee7d259fb",
                "release": "Donal Leace",
            }
            recording_3 = {
                "artist": "Memphis Minnie",
                "title": "Banana Man Blues",
                "release_mbid": "27b3c191-7e46-4d00-b6bb-cdce39c13568",
                "release": "Please Warm My Weiner: Old Time Hokum Blues",
            }

            submit_listens([recording_1, recording_2, recording_3])
            clusters_modified, clusters_add_to_redirect = create_release_clusters()
            self.assertEqual(clusters_modified, 2)
            self.assertEqual(clusters_add_to_redirect, 2)

            # After clustering retry creating clusters
            clusters_modified, clusters_add_to_redirect = create_release_clusters()
            self.assertEqual(clusters_modified, 0)
            self.assertEqual(clusters_add_to_redirect, 0)


    def test_get_recordings_metadata_using_release_mbid(self):
        """ Tests if recordings metadata is fetched correctly using release MBID. """

        recording_1 = {
            "artist": "Jay‐Z & Beyoncé",
            "title": "'03 Bonnie & Clyde",
            "recording_mbid": "5465ca86-3881-4349-81b2-6efbd3a59451",
            "release_mbid": "2c5e4198-24cf-3c95-a16e-83be8e877dfa",
            "release": "The Blueprint\u00b2: The Gift and The Curse",
        }
        submit_listens([recording_1])
        with db.engine.begin() as connection:
            recordings = get_recordings_metadata_using_release_mbid(connection, recording_1["release_mbid"])
            self.assertDictEqual(recording_1, recordings[0])


    @patch('messybrainz.db.release.fetch_releases_from_musicbrainz_db')
    def test_fetch_recording_mbids_not_in_recording_release_join(self, mock_fetch_releases):
        """Tests if recording MBIDs that are not in recording_release_join table
           are fetched correctly.
        """
        msb_listens = self._load_test_data("recordings_for_fetch_releases.json")
        submit_listens(msb_listens)

        recording_mbids_submitted = {"4a9818ba-5963-4761-864f-7d96841053d2",
            "2977432b-f1a2-4c37-b60f-bac1ce4e0961",
            "5465ca86-3881-4349-81b2-6efbd3a59451",
        }

        recording_1 = {
            "artist": "Syreeta",
            "title": "She's Leaving Home",
            "recording_mbid": "9ed38583-437f-4186-8183-9c31ffa2c116"
        }

        mock_fetch_releases.side_effect = [
            [
                {'id': '6e18c5c8-e487-4f83-9ea6-281c574933b9', 'name': 'The Blueprint 3'},
                {'id': '2829f1bc-b097-31f3-9fbc-00b4f7228a52', 'name': 'The Blueprint 3'},
                {'id': '95ff991b-7af3-42bb-9979-470ec2bd3741', 'name': 'The Blueprint 3 [Soul Assassin Special Edition]'},
                {'id': '5e782ae3-602b-48b7-99be-de6bcffa4aba', 'name': 'The Hits Collection, Volume 1'},
                {'id': '0996e292-5cb4-476b-be04-640eeecca646', 'name': 'The Blueprint 3'},
                {'id': '7ebaaa95-e316-3b20-8819-7e4ca648c135', 'name': 'The Hits Collection, Volume 1'},
                {'id': '74465497-af1a-40f2-8998-3f837a8d29ba', 'name': 'The Blueprint 3'},
                {'id': '5b94f201-0343-4728-a851-05f5abff2495', 'name': 'The Blueprint 3'},
                {'id': '4a441628-2e4d-4032-825f-6bdf4aee382e', 'name': 'The Hits Collection, Volume 1'}
            ],
            [
                {'id': '8f0c9315-6f65-4098-98a8-765e447c6d78', 'name': "Wouldn't You Like to..."}
            ],
            [
                {'id': 'f1183a86-36d2-4f1f-ab8f-6f965dc0b033', 'name': 'The Hits Collection Volume One'},
                {'id': '7111c8bc-8549-4abc-8ab9-db13f65b4a55', 'name': 'Blueprint 2.1'},
                {'id': '3c535d03-2fcc-467a-8d47-34b3250b8211', 'name': 'The Hits Collection Volume One'},
                {'id': '0ff452e3-c306-4082-b0dc-223725f4fbbf', 'name': 'The Blueprint²: The Gift & The Curse'},
                {'id': '801678aa-5d30-4342-8227-e9618f164cca', 'name': 'The Blueprint²: The Gift & The Curse'},
                {'id': '5e782ae3-602b-48b7-99be-de6bcffa4aba', 'name': 'The Hits Collection, Volume 1'},
                {'id': '4f41108c-db36-4616-8614-f504fdef287a', 'name': 'Blueprint 2.1'},
                {'id': '89f64145-2f75-41d1-831a-517b785ed75a', 'name': "The Blueprint Collector's Edition"},
                {'id': '7ebaaa95-e316-3b20-8819-7e4ca648c135', 'name': 'The Hits Collection, Volume 1'},
                {'id': '77a74b85-0ae0-338f-aaca-4f36cd394f88', 'name': 'Blueprint 2.1'},
                {'id': 'd75e103c-5ef4-4146-ae81-e27d19dc7fc4', 'name': "The Blueprint Collector's Edition"},
                {'id': '2c5e4198-24cf-3c95-a16e-83be8e877dfa', 'name': 'The Blueprint²: The Gift & The Curse'},
                {'id': '4a441628-2e4d-4032-825f-6bdf4aee382e', 'name': 'The Hits Collection, Volume 1'}
            ],
            [
                {'id': '5f7853be-1f7a-4850-b0b8-2333d6b0318f', 'name': "Syreeta"}
            ]
        ]

        with db.engine.begin() as connection:
            mbids = release.fetch_recording_mbids_not_in_recording_release_join(connection)
            self.assertSetEqual(recording_mbids_submitted, set(mbids))
            release.fetch_and_store_releases_for_all_recording_mbids()
            mbids = release.fetch_recording_mbids_not_in_recording_release_join(connection)
            self.assertListEqual(mbids, [])

            submit_listens([recording_1])
            mbids = release.fetch_recording_mbids_not_in_recording_release_join(connection)
            self.assertEqual(recording_1['recording_mbid'], mbids[0])

            release.fetch_and_store_releases_for_all_recording_mbids()
            mbids = release.fetch_recording_mbids_not_in_recording_release_join(connection)
            self.assertListEqual(mbids, [])


    @patch('messybrainz.db.release.fetch_releases_from_musicbrainz_db')
    def test_insert_releases_to_recording_release_join(self, mock_fetch_releases):
        """Tests if releases are correctly inserted into recording_release_join table."""

        recording_mbid = "5465ca86-3881-4349-81b2-6efbd3a59451"
        mock_fetch_releases.return_value = [
            {'id': 'f1183a86-36d2-4f1f-ab8f-6f965dc0b033', 'name': 'The Hits Collection Volume One'},
            {'id': '7111c8bc-8549-4abc-8ab9-db13f65b4a55', 'name': 'Blueprint 2.1'},
            {'id': '3c535d03-2fcc-467a-8d47-34b3250b8211', 'name': 'The Hits Collection Volume One'},
            {'id': '0ff452e3-c306-4082-b0dc-223725f4fbbf', 'name': 'The Blueprint²: The Gift & The Curse'},
            {'id': '801678aa-5d30-4342-8227-e9618f164cca', 'name': 'The Blueprint²: The Gift & The Curse'},
            {'id': '5e782ae3-602b-48b7-99be-de6bcffa4aba', 'name': 'The Hits Collection, Volume 1'},
            {'id': '4f41108c-db36-4616-8614-f504fdef287a', 'name': 'Blueprint 2.1'},
            {'id': '89f64145-2f75-41d1-831a-517b785ed75a', 'name': "The Blueprint Collector's Edition"},
            {'id': '7ebaaa95-e316-3b20-8819-7e4ca648c135', 'name': 'The Hits Collection, Volume 1'},
            {'id': '77a74b85-0ae0-338f-aaca-4f36cd394f88', 'name': 'Blueprint 2.1'},
            {'id': 'd75e103c-5ef4-4146-ae81-e27d19dc7fc4', 'name': "The Blueprint Collector's Edition"},
            {'id': '2c5e4198-24cf-3c95-a16e-83be8e877dfa', 'name': 'The Blueprint²: The Gift & The Curse'},
            {'id': '4a441628-2e4d-4032-825f-6bdf4aee382e', 'name': 'The Hits Collection, Volume 1'}
        ]
        with db.engine.begin() as connection:
            releases_fetched = release.fetch_releases_from_musicbrainz_db(connection, recording_mbid)
            release.insert_releases_to_recording_release_join(connection, recording_mbid, releases_fetched)
            releases_from_join = release.get_releases_for_recording_mbid(connection, recording_mbid)

            releases_fetched = {(UUID(release['id']), release['name']) for release in releases_fetched}
            self.assertSetEqual(releases_fetched, set(releases_from_join))



    @patch('messybrainz.db.release.fetch_releases_from_musicbrainz_db')
    def test_get_releases_for_recording_mbid(self, mock_fetch_releases):
        """Tests if recording_mbids store artist_mbids correctly."""

        recording_mbid = "5465ca86-3881-4349-81b2-6efbd3a59451"
        mock_fetch_releases.return_value = [
            {'id': 'f1183a86-36d2-4f1f-ab8f-6f965dc0b033', 'name': 'The Hits Collection Volume One'},
            {'id': '7111c8bc-8549-4abc-8ab9-db13f65b4a55', 'name': 'Blueprint 2.1'},
            {'id': '3c535d03-2fcc-467a-8d47-34b3250b8211', 'name': 'The Hits Collection Volume One'},
            {'id': '0ff452e3-c306-4082-b0dc-223725f4fbbf', 'name': 'The Blueprint²: The Gift & The Curse'},
            {'id': '801678aa-5d30-4342-8227-e9618f164cca', 'name': 'The Blueprint²: The Gift & The Curse'},
            {'id': '5e782ae3-602b-48b7-99be-de6bcffa4aba', 'name': 'The Hits Collection, Volume 1'},
            {'id': '4f41108c-db36-4616-8614-f504fdef287a', 'name': 'Blueprint 2.1'},
            {'id': '89f64145-2f75-41d1-831a-517b785ed75a', 'name': "The Blueprint Collector's Edition"},
            {'id': '7ebaaa95-e316-3b20-8819-7e4ca648c135', 'name': 'The Hits Collection, Volume 1'},
            {'id': '77a74b85-0ae0-338f-aaca-4f36cd394f88', 'name': 'Blueprint 2.1'},
            {'id': 'd75e103c-5ef4-4146-ae81-e27d19dc7fc4', 'name': "The Blueprint Collector's Edition"},
            {'id': '2c5e4198-24cf-3c95-a16e-83be8e877dfa', 'name': 'The Blueprint²: The Gift & The Curse'},
            {'id': '4a441628-2e4d-4032-825f-6bdf4aee382e', 'name': 'The Hits Collection, Volume 1'}
        ]

        with db.engine.begin() as connection:
            releases_from_join = release.get_releases_for_recording_mbid(connection, recording_mbid)
            self.assertListEqual(releases_from_join, [])

            releases_fetched = release.fetch_releases_from_musicbrainz_db(connection, recording_mbid)
            release.insert_releases_to_recording_release_join(connection, recording_mbid, releases_fetched)
            releases_from_join = release.get_releases_for_recording_mbid(connection, recording_mbid)

            releases_fetched = {(UUID(release['id']), release['name']) for release in releases_fetched}
            self.assertSetEqual(releases_fetched, set(releases_from_join))


    @patch('messybrainz.db.release.fetch_releases_from_musicbrainz_db')
    @unittest.skip("This test broke with PG12 upgrade, code is not used in prod")
    def test_fetch_and_store_releases_for_all_recording_mbids(self, mock_fetch_releases):
        """Test if releases are fetched and stored correctly for all recording MBIDs
           not in recording_release_join table.
        """

        msb_listens = self._load_test_data("recordings_for_fetch_releases.json")
        submit_listens(msb_listens)

        recording_mbids_submitted = {"4a9818ba-5963-4761-864f-7d96841053d2",
            "2977432b-f1a2-4c37-b60f-bac1ce4e0961",
            "5465ca86-3881-4349-81b2-6efbd3a59451",
        }

        recording_1 = {
            "artist": "Syreeta",
            "title": "She's Leaving Home",
            "recording_mbid": "9ed38583-437f-4186-8183-9c31ffa2c116"
        }

        releases_fetched = [
            [
                {'id': '8f0c9315-6f65-4098-98a8-765e447c6d78', 'name': "Wouldn't You Like to..."}
            ],
            [
                {'id': 'f1183a86-36d2-4f1f-ab8f-6f965dc0b033', 'name': 'The Hits Collection Volume One'},
                {'id': '7111c8bc-8549-4abc-8ab9-db13f65b4a55', 'name': 'Blueprint 2.1'},
                {'id': '3c535d03-2fcc-467a-8d47-34b3250b8211', 'name': 'The Hits Collection Volume One'},
                {'id': '0ff452e3-c306-4082-b0dc-223725f4fbbf', 'name': 'The Blueprint²: The Gift & The Curse'},
                {'id': '801678aa-5d30-4342-8227-e9618f164cca', 'name': 'The Blueprint²: The Gift & The Curse'},
                {'id': '5e782ae3-602b-48b7-99be-de6bcffa4aba', 'name': 'The Hits Collection, Volume 1'},
                {'id': '4f41108c-db36-4616-8614-f504fdef287a', 'name': 'Blueprint 2.1'},
                {'id': '89f64145-2f75-41d1-831a-517b785ed75a', 'name': "The Blueprint Collector's Edition"},
                {'id': '7ebaaa95-e316-3b20-8819-7e4ca648c135', 'name': 'The Hits Collection, Volume 1'},
                {'id': '77a74b85-0ae0-338f-aaca-4f36cd394f88', 'name': 'Blueprint 2.1'},
                {'id': 'd75e103c-5ef4-4146-ae81-e27d19dc7fc4', 'name': "The Blueprint Collector's Edition"},
                {'id': '2c5e4198-24cf-3c95-a16e-83be8e877dfa', 'name': 'The Blueprint²: The Gift & The Curse'},
                {'id': '4a441628-2e4d-4032-825f-6bdf4aee382e', 'name': 'The Hits Collection, Volume 1'}
            ],
            [
                {'id': '6e18c5c8-e487-4f83-9ea6-281c574933b9', 'name': 'The Blueprint 3'},
                {'id': '2829f1bc-b097-31f3-9fbc-00b4f7228a52', 'name': 'The Blueprint 3'},
                {'id': '95ff991b-7af3-42bb-9979-470ec2bd3741', 'name': 'The Blueprint 3 [Soul Assassin Special Edition]'},
                {'id': '5e782ae3-602b-48b7-99be-de6bcffa4aba', 'name': 'The Hits Collection, Volume 1'},
                {'id': '0996e292-5cb4-476b-be04-640eeecca646', 'name': 'The Blueprint 3'},
                {'id': '7ebaaa95-e316-3b20-8819-7e4ca648c135', 'name': 'The Hits Collection, Volume 1'},
                {'id': '74465497-af1a-40f2-8998-3f837a8d29ba', 'name': 'The Blueprint 3'},
                {'id': '5b94f201-0343-4728-a851-05f5abff2495', 'name': 'The Blueprint 3'},
                {'id': '4a441628-2e4d-4032-825f-6bdf4aee382e', 'name': 'The Hits Collection, Volume 1'}
            ],
            [
                {'id': '5f7853be-1f7a-4850-b0b8-2333d6b0318f', 'name': "Syreeta"}
            ]
        ]

        mock_fetch_releases.side_effect = releases_fetched

        with db.engine.begin() as connection:
            release.fetch_and_store_releases_for_all_recording_mbids()
            # Using sets for assertions because we can get multiple artist MBIDs for a
            # single recording MBID, but the order of retrieval is not known.
            releases_fetched = [
                [tuple([UUID(release['id']), release['name']]) for release in releases] 
                for releases in releases_fetched
            ]

            releases = release.get_releases_for_recording_mbid(connection, "2977432b-f1a2-4c37-b60f-bac1ce4e0961")
            self.assertSetEqual(set(releases), set(releases_fetched[0]))

            releases = release.get_releases_for_recording_mbid(connection, "5465ca86-3881-4349-81b2-6efbd3a59451")
            self.assertSetEqual(set(releases), set(releases_fetched[1]))

            releases = release.get_releases_for_recording_mbid(connection, "4a9818ba-5963-4761-864f-7d96841053d2")
            self.assertSetEqual(set(releases), set(releases_fetched[2]))

            releases = release.get_releases_for_recording_mbid(connection, "9ed38583-437f-4186-8183-9c31ffa2c116")
            self.assertListEqual(releases, [])

            submit_listens([recording_1])
            release.fetch_and_store_releases_for_all_recording_mbids()
            releases = release.get_releases_for_recording_mbid(connection, "9ed38583-437f-4186-8183-9c31ffa2c116")
            self.assertSetEqual(set(releases), set(releases_fetched[3]))
