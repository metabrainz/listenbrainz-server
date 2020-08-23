import json
import time

from flask import url_for, current_app
from redis import Redis

import listenbrainz.db.user as db_user
from listenbrainz.tests.integration import IntegrationTestCase


class ProfileViewsTestCase(IntegrationTestCase):
    def setUp(self):
        super().setUp()
        self.user = db_user.get_or_create(1, 'iliekcomputers')
        db_user.agree_to_gdpr(self.user['musicbrainz_id'])

    def tearDown(self):
        r = Redis(host=current_app.config['REDIS_HOST'], port=current_app.config['REDIS_PORT'])
        r.flushall()
        super(ProfileViewsTestCase, self).tearDown()

    def send_listens(self):
        with open(self.path_to_data_file('user_export_test.json')) as f:
            payload = json.load(f)
        return self.client.post(
            url_for('api_v1.submit_listen'),
            data=json.dumps(payload),
            headers={'Authorization': 'Token {}'.format(self.user['auth_token'])},
            content_type='application/json'
        )

    def test_export(self):
        """
        Test for the user export of ListenBrainz data.
        """
        # test get requests to export view first
        self.temporary_login(self.user['login_id'])
        resp = self.client.get(url_for('profile.export_data'))
        self.assert200(resp)

        # send three listens for the user
        resp = self.send_listens()
        self.assert200(resp)

        time.sleep(2)

        # now export data and check if contains all the listens we just sent
        resp = self.client.post(url_for('profile.export_data'))
        self.assert200(resp)
        data = json.loads(resp.data)
        self.assertEqual(len(data), 3)

    def test_user_page_latest_listen(self):
        resp = self.send_listens()
        self.assert200(resp)

        time.sleep(1)

        r = self.client.get(url_for('user.profile', user_name=self.user['musicbrainz_id']))
        self.assert200(r)
        props = json.loads(self.get_context_variable('props'))
        self.assertEqual(props['latest_listen_ts'], 2)

    def test_delete_listens(self):
        """
        Test delete listens for a user
        """
        # test get requests to delete-listens view first
        self.temporary_login(self.user['login_id'])
        resp = self.client.get(url_for('profile.delete_listens'))
        self.assert200(resp)

        # send three listens for the user
        resp = self.send_listens()
        self.assert200(resp)

        time.sleep(2)

        # set the latest_import ts to a non-default value, so that we can check it was
        # reset later
        val = int(time.time())
        resp = self.client.post(
            url_for('api_v1.latest_import'),
            data=json.dumps({'ts': val}),
            headers={'Authorization': 'Token {}'.format(self.user['auth_token'])},
            content_type='application/json',
        )
        self.assert200(resp)
        resp = self.client.get(url_for('api_v1.latest_import', user_name=self.user['musicbrainz_id']))
        self.assert200(resp)
        self.assertEqual(resp.json['latest_import'], val)

        # check that listens have been successfully submitted
        resp = self.client.get(url_for('api_v1.get_listen_count', user_name=self.user['musicbrainz_id']))
        self.assert200(resp)
        self.assertEqual(json.loads(resp.data)['payload']['count'], 3)

        # now delete all the listens we just sent
        resp = self.client.post(url_for('profile.delete_listens'), data={'token': self.user['auth_token']})
        self.assertRedirects(resp, url_for('user.profile', user_name=self.user['musicbrainz_id']))

        time.sleep(2)

        # check that listens have been successfully deleted
        resp = self.client.get(url_for('api_v1.get_listen_count', user_name=self.user['musicbrainz_id']))
        self.assert200(resp)
        self.assertEqual(json.loads(resp.data)['payload']['count'], 0)

        # check that the latest_import timestamp has been reset too
        resp = self.client.get(url_for('api_v1.latest_import', user_name=self.user['musicbrainz_id']))
        self.assert200(resp)
        self.assertEqual(resp.json['latest_import'], 0)
