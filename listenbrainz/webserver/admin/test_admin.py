import listenbrainz.db.user as db_user
from listenbrainz.tests.integration import IntegrationTestCase


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
