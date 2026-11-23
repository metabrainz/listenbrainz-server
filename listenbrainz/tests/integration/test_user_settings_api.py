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

    def test_brainzplayer_notifications_pref(self):
        response = self.client.post(
            self.custom_url_for("user_settings_api_v1.update_brainzplayer_prefs"),
            json={"notificationsEnabled": False},
            headers={"Authorization": f"Token {self.user['auth_token']}"}
        )
        self.assert200(response)

        prefs = db_user_setting.get_brainzplayer_prefs(self.db_conn, self.user["id"])
        self.assertEqual(prefs, {"brainzplayer": {"notificationsEnabled": False}})

    def test_datetime_format_validates_auth_header(self):
        response = self.client.post(self.custom_url_for("user_settings_api_v1.update_datetime_format_prefs"), json={})
        self.assert401(response)

        response = self.client.post(
            self.custom_url_for("user_settings_api_v1.update_datetime_format_prefs"),
            json={},
            headers={"Authorization": "Token invalid"}
        )
        self.assert401(response)

    def test_invalid_datetime_format_prefs(self):
        response = self.client.post(
            self.custom_url_for("user_settings_api_v1.update_datetime_format_prefs"),
            json={"fnord": True},
            headers={"Authorization": f"Token {self.user['auth_token']}"}
        )
        self.assert400(response)
        self.assertEqual(
            response.json["error"],
            "Invalid preferences in the JSON: Additional properties are not allowed ('fnord' was unexpected)"
        )

        response = self.client.post(
            self.custom_url_for("user_settings_api_v1.update_datetime_format_prefs"),
            json={"dateFormat": "DD/MM/YY"},
            headers={"Authorization": f"Token {self.user['auth_token']}"}
        )
        self.assert400(response)

        response = self.client.post(
            self.custom_url_for("user_settings_api_v1.update_datetime_format_prefs"),
            json={"timeFormat": "13h"},
            headers={"Authorization": f"Token {self.user['auth_token']}"}
        )
        self.assert400(response)

        # nothing should have been saved, so the user still has the defaults
        self.assertEqual(
            db_user_setting.get_datetime_format_prefs(self.db_conn, self.user["id"]),
            {"datetime_format": {"dateFormat": "auto", "timeFormat": "auto"}}
        )

    def test_valid_datetime_format_prefs(self):
        self.assertEqual(
            db_user_setting.get_datetime_format_prefs(self.db_conn, self.user["id"]),
            {"datetime_format": {"dateFormat": "auto", "timeFormat": "auto"}}
        )

        response = self.client.post(
            self.custom_url_for("user_settings_api_v1.update_datetime_format_prefs"),
            json={"dateFormat": "DMY", "timeFormat": "24h"},
            headers={"Authorization": f"Token {self.user['auth_token']}"}
        )
        self.assert200(response)

        prefs = db_user_setting.get_datetime_format_prefs(self.db_conn, self.user["id"])
        self.assertEqual(prefs, {"datetime_format": {"dateFormat": "DMY", "timeFormat": "24h"}})

    def test_datetime_format_rejects_malformed_bodies(self):
        url = self.custom_url_for("user_settings_api_v1.update_datetime_format_prefs")
        headers = {"Authorization": f"Token {self.user['auth_token']}"}

        # not valid JSON at all
        response = self.client.post(url, data="{not json", headers=headers)
        self.assert400(response)
        self.assertTrue(response.json["error"].startswith("Invalid JSON"))

        # valid JSON, but not an object, the wrong type for a field, or a key we do not accept
        # (including a user_id, so there is no way to name another user in the request)
        for body in ["[]", "null", '"auto"', '{"dateFormat": null}', '{"timeFormat": ["24h"]}',
                     '{"user_id": 1, "dateFormat": "auto"}']:
            with self.subTest(body=body):
                response = self.client.post(url, data=body, headers=headers)
                self.assert400(response)
                self.assertTrue(response.json["error"].startswith("Invalid preferences in the JSON"))

        # none of the rejected requests saved anything
        self.assertEqual(
            db_user_setting.get_datetime_format_prefs(self.db_conn, self.user["id"]),
            {"datetime_format": {"dateFormat": "auto", "timeFormat": "auto"}}
        )

    def test_datetime_format_empty_object_means_defaults(self):
        response = self.client.post(
            self.custom_url_for("user_settings_api_v1.update_datetime_format_prefs"),
            json={},
            headers={"Authorization": f"Token {self.user['auth_token']}"}
        )
        self.assert200(response)
        self.assertEqual(
            db_user_setting.get_datetime_format_prefs(self.db_conn, self.user["id"]),
            {"datetime_format": {"dateFormat": "auto", "timeFormat": "auto"}}
        )

    def test_datetime_format_users_are_independent(self):
        url = self.custom_url_for("user_settings_api_v1.update_datetime_format_prefs")
        other_user = db_user.get_or_create(self.db_conn, 272, "another unfriendly neighborhood spider-man")

        # the first user saves a format, the other user is not affected
        response = self.client.post(
            url,
            json={"dateFormat": "YMD"},
            headers={"Authorization": f"Token {self.user['auth_token']}"}
        )
        self.assert200(response)
        self.assertEqual(
            db_user_setting.get_datetime_format_prefs(self.db_conn, other_user["id"]),
            {"datetime_format": {"dateFormat": "auto", "timeFormat": "auto"}}
        )

        # the other user saves a different one, the first user keeps theirs
        response = self.client.post(
            url,
            json={"timeFormat": "12h"},
            headers={"Authorization": f"Token {other_user['auth_token']}"}
        )
        self.assert200(response)
        self.assertEqual(
            db_user_setting.get_datetime_format_prefs(self.db_conn, self.user["id"]),
            {"datetime_format": {"dateFormat": "YMD", "timeFormat": "auto"}}
        )
        self.assertEqual(
            db_user_setting.get_datetime_format_prefs(self.db_conn, other_user["id"]),
            {"datetime_format": {"dateFormat": "auto", "timeFormat": "12h"}}
        )