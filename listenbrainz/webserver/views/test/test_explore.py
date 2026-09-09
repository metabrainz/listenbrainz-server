import datetime
from unittest import mock
from unittest.mock import patch

from listenbrainz.tests.integration import IntegrationTestCase
from listenbrainz.webserver.views.explore import process_genre_explorer_data


class ExploreViewsTestCase(IntegrationTestCase):

    def test_hue_sound(self):
        resp = self.client.get(self.custom_url_for('explore.index', path="huesound"))
        self.assert200(resp)

    def test_similar_users(self):
        resp = self.client.get(self.custom_url_for('explore.index', path="similar-users"))
        self.assert200(resp)

    def test_fresh_releases(self):
        resp = self.client.get(self.custom_url_for('explore.index', path="fresh-releases"))
        self.assert200(resp)

    @patch('listenbrainz.db.fresh_releases.get_sitewide_fresh_releases', side_effect=[([], 0), ([], 0), ([], 0)])
    def test_fresh_releases_api(self, mock_fresh):
        resp = self.client.get(self.custom_url_for('explore_api_v1.get_fresh_releases'))
        self.assert200(resp)
        mock_fresh.assert_called_with(mock.ANY, datetime.date.today(), 14, 'release_date', True, True)

        resp = self.client.get(self.custom_url_for('explore_api_v1.get_fresh_releases', release_date="2022-01-01", days=5))
        self.assert200(resp)
        mock_fresh.assert_called_with(mock.ANY, datetime.date(year=2022, month=1, day=1), 5, 'release_date', True, True)

        resp = self.client.get(self.custom_url_for('explore_api_v1.get_fresh_releases', sort="artist_credit_name", past=False))
        self.assert200(resp)
        mock_fresh.assert_called_with(mock.ANY, datetime.date.today(), 14, 'artist_credit_name', False, True)

    def test_lb_radio(self):
        resp = self.client.get(self.custom_url_for('explore.index', path="lb-radio"))
        self.assert200(resp)

    def test_process_genre_explorer_data(self):
        data = [
            {"genre": "rock", "genre_gid": "rock-id", "subgenre": "alternative", "subgenre_gid": "alt-id"},
            {"genre": "rock", "genre_gid": "rock-id", "subgenre": "blues rock", "subgenre_gid": "blues-id"},
            {"genre": "music", "genre_gid": "music-id", "subgenre": "rock", "subgenre_gid": "rock-id"},
        ]

        genre, children, parents, siblings = process_genre_explorer_data(data, "rock")

        self.assertEqual(genre, {"id": "rock-id", "name": "rock"})
        self.assertEqual(children, [
            {"id": "alt-id", "name": "alternative"},
            {"id": "blues-id", "name": "blues rock"},
        ])
        self.assertEqual(parents, {
            "nodes": [{"id": "music-id", "name": "music"}],
            "edges": [{"source": "music-id", "target": "rock-id"}],
        })
        self.assertEqual(siblings, [])

    @patch('listenbrainz.webserver.views.explore.get_tag_hierarchy_data')
    def test_genre_explorer(self, mock_get_tag_hierarchy_data):
        mock_get_tag_hierarchy_data.return_value = [
            {"genre": "music", "genre_gid": "music-id", "subgenre": "rock", "subgenre_gid": "rock-id"},
            {"genre": "rock", "genre_gid": "rock-id", "subgenre": None, "subgenre_gid": None},
        ]

        response = self.client.post(
            self.custom_url_for('explore.genre_explorer', genre_name='rock')
        )

        self.assert200(response)
        self.assertEqual(response.json["genre"], {"id": "rock-id", "name": "rock"})
        self.assertEqual(response.json["parents"]["nodes"], [{"id": "music-id", "name": "music"}])

    @patch('listenbrainz.webserver.views.explore.get_tag_hierarchy_data')
    def test_genre_explorer_handles_loading_error(self, mock_get_tag_hierarchy_data):
        mock_get_tag_hierarchy_data.side_effect = RuntimeError("MusicBrainz unavailable")

        response = self.client.post(
            self.custom_url_for('explore.genre_explorer', genre_name='rock')
        )

        self.assert500(response)
        self.assertEqual(response.json, {"error": "Failed to load genre explorer data"})
