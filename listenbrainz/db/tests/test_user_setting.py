import listenbrainz.db.user_setting as db_setting
import listenbrainz.db.user as db_user

from listenbrainz.db.testing import DatabaseTestCase


class UserSettingTestCase(DatabaseTestCase):
    def setUp(self):
        DatabaseTestCase.setUp(self)
        self.user = db_user.get_or_create(self.db_conn, 1, "user_setting_user")

    def test_set_timezone(self):
        # test if timezone is not null
        test_zonename = 'America/New_York'
        db_setting.set_timezone(self.db_conn, self.user['id'], test_zonename)
        result = db_setting.get(self.db_conn, self.user['id'])
        self.assertEqual(result['timezone_name'], test_zonename)

        # test if timezone is null
        test_zonename = None
        db_setting.set_timezone(self.db_conn, self.user['id'], test_zonename)
        result = db_setting.get(self.db_conn, self.user['id'])
        self.assertEqual(result['timezone_name'], 'UTC')

    def test_datetime_format_prefs(self):
        # no settings row yet: a complete default is returned, not None
        self.assertEqual(
            db_setting.get_datetime_format_prefs(self.db_conn, self.user['id']),
            {"datetime_format": {"dateFormat": "auto", "timeFormat": "auto"}}
        )

        db_setting.update_datetime_format_prefs(
            self.db_conn, self.user['id'], '{"dateFormat": "YMD", "timeFormat": "24h"}'
        )
        result = db_setting.get_datetime_format_prefs(self.db_conn, self.user['id'])
        self.assertEqual(result, {"datetime_format": {"dateFormat": "YMD", "timeFormat": "24h"}})

        # saving again replaces the previous value, and keys that are not given fall back to the defaults
        db_setting.update_datetime_format_prefs(self.db_conn, self.user['id'], '{"timeFormat": "12h"}')
        result = db_setting.get_datetime_format_prefs(self.db_conn, self.user['id'])
        self.assertEqual(result, {"datetime_format": {"dateFormat": "auto", "timeFormat": "12h"}})

    def test_datetime_format_defaults_when_row_exists_without_value(self):
        # the user has a settings row (timezone) but has never configured the date and time format
        db_setting.set_timezone(self.db_conn, self.user['id'], 'America/New_York')
        result = db_setting.get_datetime_format_prefs(self.db_conn, self.user['id'])
        self.assertEqual(result, {"datetime_format": {"dateFormat": "auto", "timeFormat": "auto"}})

    def test_datetime_format_does_not_touch_other_settings(self):
        db_setting.set_timezone(self.db_conn, self.user['id'], 'America/New_York')
        db_setting.update_datetime_format_prefs(self.db_conn, self.user['id'], '{"dateFormat": "DMY"}')
        result = db_setting.get(self.db_conn, self.user['id'])
        self.assertEqual(result['timezone_name'], 'America/New_York')
