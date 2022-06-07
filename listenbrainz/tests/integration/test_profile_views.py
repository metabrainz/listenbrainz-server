import json
import time

from brainzutils import cache
from flask import url_for, g

import listenbrainz.db.user as db_user
from listenbrainz.listenstore.timescale_listenstore import REDIS_USER_LISTEN_COUNT
from listenbrainz.listenstore.timescale_utils import recalculate_all_user_data
from listenbrainz.tests.integration import IntegrationTestCase


class ProfileViewsTestCase(IntegrationTestCase):
    def setUp(self):
        super().setUp()
        self.user = db_user.get_or_create(1, 'iliekcomputers')
        db_user.agree_to_gdpr(self.user['musicbrainz_id'])
        self.redis = cache._r

    def tearDown(self):
        self.redis.flushall()
        super(ProfileViewsTestCase, self).tearDown()

    def send_listens(self):
        with open(self.path_to_data_file('user_export_test.json')) as f:
            payload = json.load(f)
        response = self.client.post(
            url_for('api_v1.submit_listen'),
            data=json.dumps(payload),
            headers={'Authorization': 'Token {}'.format(self.user['auth_token'])},
            content_type='application/json'
        )
        time.sleep(1)
        recalculate_all_user_data()
        return response

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

        # now export data and check if contains all the listens we just sent
        resp = self.client.post(url_for('profile.export_data'))
        self.assert200(resp)
        data = json.loads(resp.data)
        self.assertEqual(len(data), 3)

    def test_user_page_latest_listen(self):
        resp = self.send_listens()
        self.assert200(resp)

        r = self.client.get(url_for('user.profile', user_name=self.user['musicbrainz_id']))
        self.assert200(r)
        props = json.loads(self.get_context_variable('props'))
        self.assertEqual(props['latest_listen_ts'], 1618500200)

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

        self.assertNotEqual(self.redis.ttl(cache._prep_key(REDIS_USER_LISTEN_COUNT + str(self.user['id']))), 0)

        # check that listens have been successfully submitted
        resp = self.client.get(url_for('api_v1.get_listen_count', user_name=self.user['musicbrainz_id']))
        self.assert200(resp)
        self.assertEqual(json.loads(resp.data)['payload']['count'], 3)

        # now delete all the listens we just sent
        # we do a get request first to put the CSRF token in the flask global context
        # so that we can access it for using in the post request in the next step
        self.client.get(url_for('profile.delete_listens'))
        resp = self.client.post(url_for('profile.delete_listens'), data={'csrf_token': g.csrf_token})
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(resp.location, url_for('user.profile', user_name=self.user['musicbrainz_id']))

        # listen counts are cached for 5 min, so delete key otherwise cached will be returned
        cache.delete(REDIS_USER_LISTEN_COUNT + str(self.user['id']))

        # check that listens have been successfully deleted
        resp = self.client.get(url_for('api_v1.get_listen_count', user_name=self.user['musicbrainz_id']))
        self.assert200(resp)
        self.assertEqual(json.loads(resp.data)['payload']['count'], 0)

        # check that the latest_import timestamp has been reset too
        resp = self.client.get(url_for('api_v1.latest_import', user_name=self.user['musicbrainz_id']))
        self.assert200(resp)
        self.assertEqual(resp.json['latest_import'], 0)
