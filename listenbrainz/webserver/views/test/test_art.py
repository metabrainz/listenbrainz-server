from unittest.mock import patch

from data.model.user_artist_stat import ArtistRecord
from data.model.user_release_stat import ReleaseRecord
from listenbrainz.art.cover_art_generator import CoverArtGenerator
from listenbrainz.tests.integration import IntegrationTestCase


class ArtViewsTestCase(IntegrationTestCase):

    def test_index(self):
        resp = self.client.get(self.custom_url_for('art.index'))
        self.assert200(resp)

    @patch.object(CoverArtGenerator, "load_release_group_caa_ids")
    @patch.object(CoverArtGenerator, "load_release_caa_ids")
    @patch.object(CoverArtGenerator, "download_user_stats")
    def test_cover_art_grid_stats(self, mock_download_user_stats, mock_get_release_caa_ids, mock_get_release_group_caa_ids):
        mock_download_user_stats.return_value = [
            ReleaseRecord(
                release_mbid="b757afbf-1b6a-4bd1-9d3f-2ad9cac9c3d6",
                release_name="Release 1",
                listen_count=5,
                artist_name="Artist 1",
                artist_mbids=["b757afbf-1b6a-4bd1-9d3f-2ad9cac9c3d6"]
            )
        ], 1
        mock_get_release_caa_ids.return_value = {
            "b757afbf-1b6a-4bd1-9d3f-2ad9cac9c3d6": {
                "original_mbid": "b757afbf-1b6a-4bd1-9d3f-2ad9cac9c3d6",
                "caa_id": 6945,
                "caa_release_mbid": "b757afbf-1b6a-4bd1-9d3f-2ad9cac9c3d6",
                "title": "Release 1",
                "artist": "Artist 1"
            }
        }
        mock_get_release_group_caa_ids.return_value = {}
        resp = self.client.get(
            self.custom_url_for('art_api_v1.cover_art_grid_stats',
                                user_name="rob",
                                time_range="week",
                                dimension=4,
                                layout=0,
                                image_size=500))
        self.assert200(resp)
        self.assertTrue(resp.text.startswith("<svg"))

        # Make sure we find the caa_id in the output SVG
        self.assertNotEqual(resp.text.find("6945"), -1)

    @patch.object(CoverArtGenerator, "download_user_stats")
    def test_cover_art_custom_artist_stats(self, mock_download_user_stats):
        mock_download_user_stats.return_value = [
            ArtistRecord(artist_mbids=["b757afbf-1b6a-4bd1-9d3f-2ad9cac9c3d6"], artist_name="Artist", listen_count=1)
            for _ in range(5)
        ], 5
        resp = self.client.get(
            self.custom_url_for('art_api_v1.cover_art_custom_stats',
                                custom_name="designer-top-5",
                                user_name="rob",
                                time_range="week",
                                image_size=500))
        self.assert200(resp)
        self.assertTrue(resp.text.startswith("<svg"))
        self.assertNotEqual(resp.text.find("ROB"), -1)

    @patch.object(CoverArtGenerator, "load_release_group_caa_ids")
    @patch.object(CoverArtGenerator, "load_release_caa_ids")
    @patch.object(CoverArtGenerator, "download_user_stats")
    def test_cover_art_custom_release_stats(self, mock_download_user_stats,
                                            mock_get_release_caa_ids, mock_get_release_group_caa_ids):
        mock_download_user_stats.return_value = [
            ReleaseRecord(
                release_mbid="b757afbf-1b6a-4bd1-9d3f-2ad9cac9c3d6",
                release_name="Release 1",
                listen_count=5,
                artist_name="Artist 1",
                artist_mbids=["b757afbf-1b6a-4bd1-9d3f-2ad9cac9c3d6"]
            )
            for _ in range(10)
        ], 10
        mock_get_release_caa_ids.return_value = {
            "b757afbf-1b6a-4bd1-9d3f-2ad9cac9c3d6": {
                "original_mbid": "b757afbf-1b6a-4bd1-9d3f-2ad9cac9c3d6",
                "caa_id": 6945,
                "caa_release_mbid": "b757afbf-1b6a-4bd1-9d3f-2ad9cac9c3d6",
                "title": "Release 1",
                "artist": "Artist 1"
            }
        }
        mock_get_release_group_caa_ids.return_value = {}
        resp = self.client.get(
            self.custom_url_for('art_api_v1.cover_art_custom_stats',
                                custom_name="designer-top-10",
                                user_name="rob",
                                time_range="week",
                                image_size=500))
        self.assert200(resp)
        self.assertTrue(resp.text.startswith("<svg"))

    @patch.object(CoverArtGenerator, "load_release_group_caa_ids")
    @patch.object(CoverArtGenerator, "load_release_caa_ids")
    @patch.object(CoverArtGenerator, "download_user_stats")
    def test_cover_art_lps_on_the_floor_params(self, mock_download_user_stats,
                                                mock_get_release_caa_ids, mock_get_release_group_caa_ids):
        mock_download_user_stats.return_value = [
            ReleaseRecord(
                release_mbid="b757afbf-1b6a-4bd1-9d3f-2ad9cac9c3d6",
                release_name="Release 1",
                listen_count=5,
                artist_name="Artist 1",
                artist_mbids=["b757afbf-1b6a-4bd1-9d3f-2ad9cac9c3d6"]
            )
            for _ in range(5)
        ], 5
        mock_get_release_caa_ids.return_value = {
            "b757afbf-1b6a-4bd1-9d3f-2ad9cac9c3d6": {
                "original_mbid": "b757afbf-1b6a-4bd1-9d3f-2ad9cac9c3d6",
                "caa_id": 6945,
                "caa_release_mbid": "b757afbf-1b6a-4bd1-9d3f-2ad9cac9c3d6",
                "title": "Release 1",
                "artist": "Artist 1"
            }
        }
        mock_get_release_group_caa_ids.return_value = {}

        resp = self.client.get(
            self.custom_url_for('art_api_v1.cover_art_custom_stats',
                                custom_name="lps-on-the-floor",
                                user_name="rob",
                                time_range="week",
                                image_size=1000),
            query_string={
                "scene": "vinyl",
                "wear_tear": "loved",
                "player_color": "ff0000"
            })
        self.assert200(resp)
        self.assertTrue(resp.text.startswith("<svg"))
        # Correct scene background URL
        self.assertIn("vinyl%20bg.png", resp.text)
        # wear_tear="loved" should use worn 2
        self.assertIn("vinyl%20worn%202.png", resp.text)
        # Player colour overlay URL
        self.assertIn("vinyl%20player%20color.svg", resp.text)
        # feColorMatrix: ff0000 -> r=1.0, g=0.0, b=0.0 mapped via alpha channel
        self.assertIn("0 0 0 1.0 0", resp.text)
        # "loved" must not accidentally serve worn 1
        self.assertNotIn("vinyl%20worn%201.png", resp.text)


    @patch.object(CoverArtGenerator, "load_release_group_caa_ids")
    @patch.object(CoverArtGenerator, "load_release_caa_ids")
    def test_cover_art_grid_post(self, mock_get_release_caa_ids, mock_get_release_group_caa_ids):
        with open("listenbrainz/art/misc/sample_cover_art_grid_post_request.json", "r") as f:
            post_json = f.read()

        mock_get_release_caa_ids.return_value = {
            "be5f714d-02eb-4c89-9a06-5e544f132604": {
                "original_mbid": "be5f714d-02eb-4c89-9a06-5e544f132604",
                "caa_id": 2273480607,
                "caa_release_mbid": "be5f714d-02eb-4c89-9a06-5e544f132604",
                "title": "Tales of the Inexpressible",
                "artist": "Shpongle"
            },
            "4211382c-39e8-4a72-a32d-e4046fd96356": {
                "original_mbid": "4211382c-39e8-4a72-a32d-e4046fd96356",
                "caa_id": 8194366407,
                "caa_release_mbid": "4211382c-39e8-4a72-a32d-e4046fd96356",
                "title": "Extraordinary Ways",
                "artist": "Conjure One"
            },
            "773e54bb-3f43-4813-826c-ca762bfa8318": {
                "original_mbid": "773e54bb-3f43-4813-826c-ca762bfa8318",
                "caa_id": 9660646535,
                "caa_release_mbid": "773e54bb-3f43-4813-826c-ca762bfa8318",
                "title": "That Much Closer to the Sun",
                "artist": "Abakus"
            },
            "10dffffc-c2aa-4ddd-81fd-42b5e125f240": {
                "original_mbid": "10dffffc-c2aa-4ddd-81fd-42b5e125f240",
                "caa_id": 28871824662,
                "caa_release_mbid": "10dffffc-c2aa-4ddd-81fd-42b5e125f240",
                "title": "IV",
                "artist": "dZihan & Kamien"
            },
            "d101e395-0c04-4237-a3d2-167b1d88056c": {
                "original_mbid": "be5f714d-02eb-4c89-9a06-5e544f132604",
                "caa_id": 2273480607,
                "caa_release_mbid": "d101e395-0c04-4237-a3d2-167b1d88056c",
                "title": "Tales of the Inexpressible",
                "artist": "Shpongle"
            },
            "3eee4ed1-b48e-4894-8a05-f535f16a4985": {
                "original_mbid": "3eee4ed1-b48e-4894-8a05-f535f16a4985",
                "caa_id": 31067711419,
                "caa_release_mbid": "3eee4ed1-b48e-4894-8a05-f535f16a4985",
                "title": "Changed for the Better",
                "artist": "Weval"
            },
            "ec782dbe-9204-4ec3-bf50-576c7cf3dfb3": {
                "original_mbid": "ec782dbe-9204-4ec3-bf50-576c7cf3dfb3",
                "caa_id": 31206007614,
                "caa_release_mbid": "ec782dbe-9204-4ec3-bf50-576c7cf3dfb3",
                "title": "Raum",
                "artist": "Tangerine Dream"
            },
            "6d895dfa-8688-4867-9730-2b98050dae04": {
                "original_mbid": "6d895dfa-8688-4867-9730-2b98050dae04",
                "caa_id": None,
                "caa_release_mbid": None,
                "title": None,
                "artist": None
            }
        }

        mock_get_release_group_caa_ids.return_value = {}
        resp = self.client.post(self.custom_url_for('art_api_v1.cover_art_grid_post'), data=post_json,
                                content_type="application/json")
        self.assert200(resp)
        self.assertTrue(resp.text.startswith("<svg"))
        self.assertNotEqual(resp.text.find("2273480607"), -1)

    def _get_lps_on_the_floor(self, mock_download_user_stats, mock_get_release_caa_ids,
                              mock_get_release_group_caa_ids, **query):
        """ Mock the release stats and fetch the lps-on-the-floor art with the given query params. """
        mock_download_user_stats.return_value = [
            ReleaseRecord(
                release_mbid="b757afbf-1b6a-4bd1-9d3f-2ad9cac9c3d6",
                release_name="Release 1",
                listen_count=5,
                artist_name="Artist 1",
                artist_mbids=["b757afbf-1b6a-4bd1-9d3f-2ad9cac9c3d6"]
            )
            for _ in range(5)
        ], 5
        mock_get_release_caa_ids.return_value = {
            "b757afbf-1b6a-4bd1-9d3f-2ad9cac9c3d6": {
                "original_mbid": "b757afbf-1b6a-4bd1-9d3f-2ad9cac9c3d6",
                "caa_id": 6945,
                "caa_release_mbid": "b757afbf-1b6a-4bd1-9d3f-2ad9cac9c3d6",
                "title": "Release 1",
                "artist": "Artist 1"
            }
        }
        mock_get_release_group_caa_ids.return_value = {}
        return self.client.get(
            self.custom_url_for('art_api_v1.cover_art_custom_stats',
                                custom_name="lps-on-the-floor",
                                user_name="rob",
                                time_range="week",
                                image_size=1000),
            query_string=query)

    @patch.object(CoverArtGenerator, "load_release_group_caa_ids")
    @patch.object(CoverArtGenerator, "load_release_caa_ids")
    @patch.object(CoverArtGenerator, "download_user_stats")
    def test_cover_art_lps_on_the_floor_wood_player_overlay_placement(self, mock_download_user_stats,
                                                                      mock_get_release_caa_ids,
                                                                      mock_get_release_group_caa_ids):
        """ Only the wood player-colour overlay needs explicit placement, the other scenes' overlays fill the canvas. """
        for scene in ("wood", "close", "vinyl", "many"):
            resp = self._get_lps_on_the_floor(mock_download_user_stats, mock_get_release_caa_ids,
                                              mock_get_release_group_caa_ids, scene=scene)
            self.assert200(resp)
            if scene == "wood":
                self.assertIn('x="312.68"', resp.text)
            else:
                self.assertNotIn('x="312.68"', resp.text, msg=f"scene={scene}")

    @patch.object(CoverArtGenerator, "load_release_group_caa_ids")
    @patch.object(CoverArtGenerator, "load_release_caa_ids")
    @patch.object(CoverArtGenerator, "download_user_stats")
    def test_cover_art_lps_on_the_floor_viewbox_is_fixed(self, mock_download_user_stats,
                                                         mock_get_release_caa_ids, mock_get_release_group_caa_ids):
        """ The viewBox must stay on the 1000-unit canvas so smaller image sizes scale the scene instead of cropping it. """
        mock_download_user_stats.return_value = [
            ReleaseRecord(
                release_mbid="b757afbf-1b6a-4bd1-9d3f-2ad9cac9c3d6",
                release_name="Release 1",
                listen_count=5,
                artist_name="Artist 1",
                artist_mbids=["b757afbf-1b6a-4bd1-9d3f-2ad9cac9c3d6"]
            )
            for _ in range(5)
        ], 5
        mock_get_release_caa_ids.return_value = {
            "b757afbf-1b6a-4bd1-9d3f-2ad9cac9c3d6": {
                "original_mbid": "b757afbf-1b6a-4bd1-9d3f-2ad9cac9c3d6",
                "caa_id": 6945,
                "caa_release_mbid": "b757afbf-1b6a-4bd1-9d3f-2ad9cac9c3d6",
                "title": "Release 1",
                "artist": "Artist 1"
            }
        }
        mock_get_release_group_caa_ids.return_value = {}

        for image_size in (750, 1000):
            resp = self.client.get(
                self.custom_url_for('art_api_v1.cover_art_custom_stats',
                                    custom_name="lps-on-the-floor",
                                    user_name="rob",
                                    time_range="week",
                                    image_size=image_size),
                query_string={"scene": "wood"})
            self.assert200(resp)
            self.assertIn('viewBox="0 0 1000 1000"', resp.text, msg=f"image_size={image_size}")
            self.assertIn(f'width="{image_size}"', resp.text, msg=f"image_size={image_size}")

    @patch.object(CoverArtGenerator, "load_release_group_caa_ids")
    @patch.object(CoverArtGenerator, "load_release_caa_ids")
    @patch.object(CoverArtGenerator, "download_user_stats")
    def test_cover_art_lps_on_the_floor_cover_counts(self, mock_download_user_stats,
                                                      mock_get_release_caa_ids, mock_get_release_group_caa_ids):
        """ Each scene must place exactly as many covers as it has sleeves (close=8 and many=12 used to crash). """
        expected_counts = {"wood": 5, "vinyl": 5, "close": 8, "many": 12}
        for scene, expected in expected_counts.items():
            resp = self._get_lps_on_the_floor(mock_download_user_stats, mock_get_release_caa_ids,
                                              mock_get_release_group_caa_ids, scene=scene)
            self.assert200(resp)
            self.assertEqual(resp.text.count('transform="'), expected, msg=f"scene={scene}")
            self.assertIn(f"{scene}%20bg.png", resp.text, msg=f"scene={scene}")

    @patch.object(CoverArtGenerator, "load_release_group_caa_ids")
    @patch.object(CoverArtGenerator, "load_release_caa_ids")
    @patch.object(CoverArtGenerator, "download_user_stats")
    def test_cover_art_lps_on_the_floor_wear_tear_options(self, mock_download_user_stats,
                                                           mock_get_release_caa_ids, mock_get_release_group_caa_ids):
        """ The default wear is "used" and "new" must not add any wear layer. """
        resp = self._get_lps_on_the_floor(mock_download_user_stats, mock_get_release_caa_ids,
                                          mock_get_release_group_caa_ids)
        self.assert200(resp)
        self.assertIn("wood%20bg.png", resp.text)
        self.assertIn("wood%20worn%201.png", resp.text)
        self.assertNotIn("wood%20worn%202.png", resp.text)

        resp = self._get_lps_on_the_floor(mock_download_user_stats, mock_get_release_caa_ids,
                                          mock_get_release_group_caa_ids, wear_tear="new")
        self.assert200(resp)
        self.assertIn("wood%20bg.png", resp.text)
        self.assertNotIn("worn", resp.text)

    @patch.object(CoverArtGenerator, "load_release_group_caa_ids")
    @patch.object(CoverArtGenerator, "load_release_caa_ids")
    @patch.object(CoverArtGenerator, "download_user_stats")
    def test_cover_art_lps_on_the_floor_invalid_params_use_defaults(self, mock_download_user_stats,
                                                                     mock_get_release_caa_ids,
                                                                     mock_get_release_group_caa_ids):
        """ Unknown scene or wear_tear and a malformed player_color must fall back to the defaults. """
        resp = self._get_lps_on_the_floor(mock_download_user_stats, mock_get_release_caa_ids,
                                          mock_get_release_group_caa_ids,
                                          scene="bogus", wear_tear="bogus", player_color="zzzzzz")
        self.assert200(resp)
        self.assertEqual(resp.text.count('transform="'), 5)
        self.assertIn("wood%20bg.png", resp.text)
        self.assertIn("wood%20worn%201.png", resp.text)
        # white fallback: r=g=b=1.0
        self.assertIn("0 0 0 1.0 0", resp.text)

    @patch.object(CoverArtGenerator, "load_release_group_caa_ids")
    @patch.object(CoverArtGenerator, "load_release_caa_ids")
    @patch.object(CoverArtGenerator, "download_user_stats")
    def test_cover_art_lps_on_the_floor_player_color_channels(self, mock_download_user_stats,
                                                               mock_get_release_caa_ids,
                                                               mock_get_release_group_caa_ids):
        """ player_color is split into r, g and b channels (0x33, 0x66, 0x99 -> 0.2, 0.4, 0.6). """
        resp = self._get_lps_on_the_floor(mock_download_user_stats, mock_get_release_caa_ids,
                                          mock_get_release_group_caa_ids, player_color="336699")
        self.assert200(resp)
        self.assertIn("0 0 0 0.2 0", resp.text)
        self.assertIn("0 0 0 0.4 0", resp.text)
        self.assertIn("0 0 0 0.6 0", resp.text)
