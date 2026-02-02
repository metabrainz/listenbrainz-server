from listenbrainz.tests.integration import ListenAPIIntegrationTestCase
from listenbrainz.db import user as db_user
from listenbrainz.db import user_setting as db_user_setting


class UserSettingsAPITestCase(ListenAPIIntegrationTestCase):

    def setUp(self):
        super(UserSettingsAPITestCase, self).setUp()
        self.user = db_user.get_or_create(self.db_conn, 271, 'unfriendly neighborhood spider-man')

    def test_validates_auth_header(self):
        """ Test the preferences endpoints validate auth header """
        response = self.client.post(self.custom_url_for("user_settings_api_v1.reset_timezone"), json={})
        self.assert401(response)

        response = self.client.post(self.custom_url_for("user_settings_api_v1.update_troi_prefs"), json={})
        self.assert401(response)

        response = self.client.post(
            self.custom_url_for("user_settings_api_v1.reset_timezone"),
            json={},
            headers={"Authorization": "Token invalid"}
        )
        self.assert401(response)

        response = self.client.post(
            self.custom_url_for("user_settings_api_v1.update_troi_prefs"),
            json={},
            headers={"Authorization": "Token invalid"}
        )
        self.assert401(response)

    def test_invalid_update_timezone(self):
        response = self.client.post(
            self.custom_url_for("user_settings_api_v1.reset_timezone"),
            json={},
            headers={"Authorization": f"Token {self.user['auth_token']}"}
        )
        self.assert400(response)
        self.assertEqual(response.json["error"], "JSON document must contain zonename")

        response = self.client.post(
            self.custom_url_for("user_settings_api_v1.reset_timezone"),
            json={"zonename": "invalid time zone"},
            headers={"Authorization": f"Token {self.user['auth_token']}"}
        )
        self.assert500(response)
        self.assertEqual(response.json["error"], "Something went wrong! Unable to update timezone right now.")

    def test_valid_update_timezone(self):
        tz = db_user_setting.get(self.db_conn, self.user["id"])
        self.assertEqual(tz["timezone_name"], "UTC")

        response = self.client.post(
            self.custom_url_for("user_settings_api_v1.reset_timezone"),
            json={"zonename": "Europe/Madrid"},
            headers={"Authorization": f"Token {self.user['auth_token']}"}
        )
        self.assert200(response)

        tz = db_user_setting.get(self.db_conn, self.user["id"])
        self.assertEqual(tz["timezone_name"], "Europe/Madrid")

    def test_invalid_troi_prefs(self):
        response = self.client.post(
            self.custom_url_for("user_settings_api_v1.update_troi_prefs"),
            json={},
            headers={"Authorization": f"Token {self.user['auth_token']}"}
        )
        self.assert400(response)
        self.assertEqual(response.json["error"], "JSON document must contain export_to_spotify key")

        response = self.client.post(
            self.custom_url_for("user_settings_api_v1.update_troi_prefs"),
            json={"export_to_spotify": "on"},
            headers={"Authorization": f"Token {self.user['auth_token']}"}
        )
        self.assert400(response)
        self.assertEqual(response.json["error"], "export_to_spotify key in the JSON document must be a boolean")

    def test_valid_troi_prefs(self):
        prefs = db_user_setting.get_troi_prefs(self.db_conn, self.user["id"])
        self.assertEqual(prefs, None)

        response = self.client.post(
            self.custom_url_for("user_settings_api_v1.update_troi_prefs"),
            json={"export_to_spotify": True},
            headers={"Authorization": f"Token {self.user['auth_token']}"}
        )
        self.assert200(response)

        prefs = db_user_setting.get_troi_prefs(self.db_conn, self.user["id"])
        self.assertEqual(prefs, {"troi": {"export_to_spotify": True}})

    def test_invalid_brainzplayer_prefs(self):
        response = self.client.post(
            self.custom_url_for("user_settings_api_v1.update_brainzplayer_prefs"),
            json={"fnord": True},
            headers={"Authorization": f"Token {self.user['auth_token']}"}
        )
        self.assert400(response)
        self.assertEqual(
            response.json["error"],
            "Invalid preferences in the JSON: Additional properties are not allowed ('fnord' was unexpected)"
        )

        response = self.client.post(
            self.custom_url_for("user_settings_api_v1.update_brainzplayer_prefs"),
            json={"youtubeEnabled": "yes"},
            headers={"Authorization": f"Token {self.user['auth_token']}"}
        )
        self.assert400(response)
        self.assertEqual(response.json["error"], "Invalid preferences in the JSON: 'yes' is not of type 'boolean'")

    def test_valid_brainzplayer_prefs(self):
        prefs = db_user_setting.get_brainzplayer_prefs(self.db_conn, self.user["id"])
        self.assertEqual(prefs, None)

        response = self.client.post(
            self.custom_url_for("user_settings_api_v1.update_brainzplayer_prefs"),
            json={"youtubeEnabled": False, "spotifyEnabled": True},
            headers={"Authorization": f"Token {self.user['auth_token']}"}
        )
        self.assert200(response)

        prefs = db_user_setting.get_brainzplayer_prefs(self.db_conn, self.user["id"])
        self.assertEqual(prefs, {"brainzplayer": {"youtubeEnabled": False, "spotifyEnabled": True}})
