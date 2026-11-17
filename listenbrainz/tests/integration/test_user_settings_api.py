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

    def test_invalid_flair_prefs(self):
        response = self.client.post(
            self.custom_url_for("user_settings_api_v1.update_flair"),
            json={},
            headers={"Authorization": f"Token {self.user['auth_token']}"}
        )
        self.assert400(response)
        self.assertEqual(response.json["error"], "Missing flair or display_preference field")

        response = self.client.post(
            self.custom_url_for("user_settings_api_v1.update_flair"),
            json={"flair": 123},
            headers={"Authorization": f"Token {self.user['auth_token']}"}
        )
        self.assert400(response)
        self.assertEqual(response.json["error"], "Flair must be a string")

        response = self.client.post(
            self.custom_url_for("user_settings_api_v1.update_flair"),
            json={"flair": "invalid-flair"},
            headers={"Authorization": f"Token {self.user['auth_token']}"}
        )
        self.assert400(response)
        self.assertEqual(response.json["error"], "Invalid flair: invalid-flair")

        response = self.client.post(
            self.custom_url_for("user_settings_api_v1.update_flair"),
            json={"display_preference": 123},
            headers={"Authorization": f"Token {self.user['auth_token']}"}
        )
        self.assert400(response)
        self.assertEqual(response.json["error"], "Display preference must be a string")

        response = self.client.post(
            self.custom_url_for("user_settings_api_v1.update_flair"),
            json={"display_preference": "invalid_preference"},
            headers={"Authorization": f"Token {self.user['auth_token']}"}
        )
        self.assert400(response)
        self.assertEqual(response.json["error"], "Invalid display_preference: invalid_preference")

    def test_valid_flair_prefs(self):
        flair = db_user_setting.get_flair(self.db_conn, self.user["id"])
        self.assertEqual(flair, None)

        response = self.client.post(
            self.custom_url_for("user_settings_api_v1.update_flair"),
            json={"flair": "wave"},
            headers={"Authorization": f"Token {self.user['auth_token']}"}
        )
        self.assert200(response)
        flair = db_user_setting.get_flair(self.db_conn, self.user["id"])
        self.assertEqual(flair, {"flair": "wave", "display_preference": "all"})

        response = self.client.post(
            self.custom_url_for("user_settings_api_v1.update_flair"),
            json={"display_preference": "no_animations"},
            headers={"Authorization": f"Token {self.user['auth_token']}"}
        )
        self.assert200(response)
        flair = db_user_setting.get_flair(self.db_conn, self.user["id"])
        self.assertEqual(flair, {"flair": "wave", "display_preference": "no_animations"})

        response = self.client.post(
            self.custom_url_for("user_settings_api_v1.update_flair"),
            json={"display_preference": "disabled"},
            headers={"Authorization": f"Token {self.user['auth_token']}"}
        )
        self.assert200(response)
        flair = db_user_setting.get_flair(self.db_conn, self.user["id"])
        self.assertEqual(flair, {"flair": "wave", "display_preference": "disabled"})

        response = self.client.post(
            self.custom_url_for("user_settings_api_v1.update_flair"),
            json={"flair": None},
            headers={"Authorization": f"Token {self.user['auth_token']}"}
        )
        self.assert200(response)
        flair = db_user_setting.get_flair(self.db_conn, self.user["id"])
        self.assertEqual(flair, {"flair": None, "display_preference": "disabled"})
