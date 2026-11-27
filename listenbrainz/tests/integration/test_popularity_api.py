from unittest.mock import patch

from listenbrainz.tests.integration import IntegrationTestCase


class PopularityAPITestCase(IntegrationTestCase):

    def setUp(self):
        super(PopularityAPITestCase, self).setUp()
        self.valid_mbid_1 = "13dd61c7-ce73-4e97-9f0c-9f0e53144411"
        self.valid_mbid_2 = "22ad712e-ce73-4e97-9f0c-9f0e53144411"

    @patch("listenbrainz.webserver.views.popularity_api.popularity.get_counts")
    def test_popularity_endpoints_success(self, mock_get_counts):
        mock_get_counts.return_value = ([], None)

        endpoints = [
            ("popularity_api_v1.popularity_recording", "recording_mbids"),
            ("popularity_api_v1.popularity_artist", "artist_mbids"),
            ("popularity_api_v1.popularity_release", "release_mbids"),
            ("popularity_api_v1.popularity_release_group", "release_group_mbids"),
        ]

        for endpoint, key in endpoints:
            url = self.custom_url_for(endpoint)
            payload = {key: [self.valid_mbid_1, self.valid_mbid_2]}
            response = self.client.post(url, json=payload)
            self.assert200(response)

    def test_popularity_endpoints_missing_key(self):
        endpoints = [
            ("popularity_api_v1.popularity_recording", "recording_mbids"),
            ("popularity_api_v1.popularity_artist", "artist_mbids"),
            ("popularity_api_v1.popularity_release", "release_mbids"),
            ("popularity_api_v1.popularity_release_group", "release_group_mbids"),
        ]

        for endpoint, key in endpoints:
            url = self.custom_url_for(endpoint)
            response = self.client.post(url, json={})
            self.assert400(response)
            self.assertIn(f"{key} JSON element must be present and contain a list of {key}", response.json["error"])

    def test_popularity_endpoints_invalid_type(self):
        endpoints = [
            ("popularity_api_v1.popularity_recording", "recording_mbids"),
            ("popularity_api_v1.popularity_artist", "artist_mbids"),
            ("popularity_api_v1.popularity_release", "release_mbids"),
            ("popularity_api_v1.popularity_release_group", "release_group_mbids"),
        ]

        invalid_values = [
            123,
            True,
            "not_a_list",
            {"key": "value"},
            None,
        ]

        for endpoint, key in endpoints:
            url = self.custom_url_for(endpoint)
            for val in invalid_values:
                response = self.client.post(url, json={key: val})
                self.assert400(response)
                self.assertIn(f"{key} JSON element must be present and contain a list of {key}", response.json["error"])

    def test_popularity_endpoints_empty_list(self):
        endpoints = [
            ("popularity_api_v1.popularity_recording", "recording_mbids", "recording"),
            ("popularity_api_v1.popularity_artist", "artist_mbids", "artist"),
            ("popularity_api_v1.popularity_release", "release_mbids", "release"),
            ("popularity_api_v1.popularity_release_group", "release_group_mbids", "release_group"),
        ]

        for endpoint, key, entity in endpoints:
            url = self.custom_url_for(endpoint)
            response = self.client.post(url, json={key: []})
            self.assert400(response)
            self.assertIn(f"At least one valid {entity}_mbid must be present.", response.json["error"])

    def test_popularity_endpoints_invalid_uuid(self):
        endpoints = [
            ("popularity_api_v1.popularity_recording", "recording_mbids", "recording"),
            ("popularity_api_v1.popularity_artist", "artist_mbids", "artist"),
            ("popularity_api_v1.popularity_release", "release_mbids", "release"),
            ("popularity_api_v1.popularity_release_group", "release_group_mbids", "release_group"),
        ]

        for endpoint, key, entity in endpoints:
            url = self.custom_url_for(endpoint)
            response = self.client.post(url, json={key: ["invalid-uuid"]})
            self.assert400(response)
            self.assertIn(f"{entity}_mbid invalid-uuid is not valid.", response.json["error"])
