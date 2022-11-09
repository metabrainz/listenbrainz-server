import json
from unittest import mock
from unittest.mock import patch

from flask import url_for
from flask_login import login_required
from requests.exceptions import HTTPError
from werkzeug.exceptions import BadRequest, InternalServerError, NotFound

import listenbrainz.db.user as db_user
import listenbrainz.webserver.login
from listenbrainz.tests.integration import IntegrationTestCase
from listenbrainz.art.cover_art_generator import CoverArtGenerator


class ArtViewsTestCase(IntegrationTestCase):

    def test_index(self):
        resp = self.client.get(url_for('art.index'))
        self.assert200(resp)

    def test_cover_art_grid_stats(self):
        with patch.object(CoverArtGenerator, 'get_caa_id') as mock_get_caa_id:
            mock_get_caa_id.return_value = 6945
            resp = self.client.get(
                url_for('art_api_v1.cover_art_grid_stats',
                        user_name="rob",
                        time_range="week",
                        dimension=4,
                        layout=0,
                        image_size=500))
            self.assert200(resp)
            assert resp.text.startswith("<svg")

            # Make sure we find the caa_id in the output SVG
            self.assertNotEqual(resp.text.find("6945"), -1)

    def test_cover_art_custom_artist_stats(self):
        with patch.object(CoverArtGenerator, 'get_caa_id') as mock_get_caa_id:
            mock_get_caa_id.return_value = 6945
            resp = self.client.get(
                url_for('art_api_v1.cover_art_custom_stats',
                        custom_name="designer-top-5",
                        user_name="rob",
                        time_range="week",
                        image_size=500))
            self.assert200(resp)
            assert resp.text.startswith("<svg")
            self.assertNotEqual(resp.text.find("ROB"), -1)

    def test_cover_art_custom_release_stats(self):
        with patch.object(CoverArtGenerator, 'get_caa_id') as mock_get_caa_id:
            mock_get_caa_id.return_value = 6945
            resp = self.client.get(
                url_for('art_api_v1.cover_art_custom_stats',
                        custom_name="designer-top-10",
                        user_name="rob",
                        time_range="week",
                        image_size=500))
            self.assert200(resp)
            assert resp.text.startswith("<svg")
            self.assertNotEqual(resp.text.find("ROB"), -1)

    def test_cover_art_grid_post(self):
        with open("listenbrainz/art/misc/sample_cover_art_grid_post_request.json", "r") as f:
            post_json = f.read()

        with patch.object(CoverArtGenerator, 'get_caa_id') as mock_get_caa_id:
            mock_get_caa_id.return_value = 6945
            resp = self.client.post(url_for('art_api_v1.cover_art_grid_post'), data=post_json, content_type="application/json")
            self.assert200(resp)
            assert resp.text.startswith("<svg")
            self.assertNotEqual(resp.text.find("6945"), -1)
