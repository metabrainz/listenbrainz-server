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
