import listenbrainz.db.user as db_user
from listenbrainz.tests.integration import IntegrationTestCase
from listenbrainz.webserver import redis_connection


class AdminTestCase(IntegrationTestCase):

    def setUp(self):
        IntegrationTestCase.setUp(self)
        self.authorized_user = db_user.get_or_create(self.db_conn, 1, 'iliekcomputers')
        db_user.agree_to_gdpr(self.db_conn, self.authorized_user['musicbrainz_id'])
        self.unauthorized_user = db_user.get_or_create(self.db_conn, 2, 'blahblahblah')
        db_user.agree_to_gdpr(self.db_conn, self.unauthorized_user['musicbrainz_id'])

    def test_admin_views_when_not_logged_in(self):
        r = self.client.get('/admin', follow_redirects=True)
        self.assert200(r)
        self.assertNotIn('BDFL Zone', r.data.decode('utf-8'))
        # Check if the user is redirected to the login page
        self.assertEqual(r.request.path, self.custom_url_for('login.index'))

    def test_admin_views_when_authorized_logged_in(self):
        self.app.config['ADMINS'] = [self.authorized_user['musicbrainz_id']]
        self.temporary_login(self.authorized_user['login_id'])
        # flask-admin seems to do a few redirects before going to the actual
        # final web page, so we have to follow redirects
        r = self.client.get('/admin', follow_redirects=True)
        self.assert200(r)
        self.assertIn('BDFL Zone', r.data.decode('utf-8'))

    def test_admin_views_when_unauthorized_logged_in(self):
        self.app.config['ADMINS'] = [self.authorized_user['musicbrainz_id']]
        self.temporary_login(self.unauthorized_user['login_id'])
        r = self.client.get('/admin', follow_redirects=True)
        self.assert200(r)
        self.assertNotIn('BDFL Zone', r.data.decode('utf-8'))
        # Check if the user is redirected to the their dashboard
        self.assertEqual(r.request.path, self.custom_url_for('index.index_pages', path=""))

    def test_admin_flash_messages_can_be_added_and_displayed(self):
        self.app.config['ADMINS'] = [self.authorized_user['musicbrainz_id']]
        self.temporary_login(self.authorized_user['login_id'])

        r = self.client.post(
            '/admin/flash_messages/add',
            data={'level': 'warning', 'message': 'Scheduled maintenance soon.'},
            follow_redirects=True,
        )
        self.assert200(r)

        messages = redis_connection._redis.get_admin_flash_messages()
        self.assertEqual(1, len(messages))
        self.assertEqual('warning', messages[0]['level'])
        self.assertEqual('Scheduled maintenance soon.', messages[0]['message'])

        r = self.client.get('/')
        self.assert200(r)
        self.assertIn('Scheduled maintenance soon.', r.data.decode('utf-8'))

    def test_admin_flash_messages_can_be_removed(self):
        self.app.config['ADMINS'] = [self.authorized_user['musicbrainz_id']]
        self.temporary_login(self.authorized_user['login_id'])
        message = redis_connection._redis.add_admin_flash_message('error', 'Something is down.')

        r = self.client.post(
            f'/admin/flash_messages/delete/{message["id"]}',
            follow_redirects=True,
        )
        self.assert200(r)

        messages = redis_connection._redis.get_admin_flash_messages()
        self.assertEqual([], messages)

    def test_admin_flash_messages_can_be_modified(self):
        self.app.config['ADMINS'] = [self.authorized_user['musicbrainz_id']]
        self.temporary_login(self.authorized_user['login_id'])
        message = redis_connection._redis.add_admin_flash_message('info', 'Old alert text.')

        r = self.client.post(
            f'/admin/flash_messages/edit/{message["id"]}',
            data={'level': 'error', 'message': 'New alert text.'},
            follow_redirects=True,
        )
        self.assert200(r)

        messages = redis_connection._redis.get_admin_flash_messages()
        self.assertEqual(1, len(messages))
        self.assertEqual(message['id'], messages[0]['id'])
        self.assertEqual('error', messages[0]['level'])
        self.assertEqual('New alert text.', messages[0]['message'])
        self.assertIn('updated', messages[0])
