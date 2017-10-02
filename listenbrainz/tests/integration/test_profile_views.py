import json
import time

from flask import url_for

import listenbrainz.db.user as db_user
from listenbrainz.tests.integration import IntegrationTestCase


class ProfileViewsTestCase(IntegrationTestCase):
    def setUp(self):
        super().setUp()
        self.user = db_user.get_or_create('iliekcomputers')

    def test_export(self):
        """
        Test for the user export of ListenBrainz data.
        """
        # test get requests to export view first
        self.temporary_login(self.user['id'])
        resp = self.client.get(url_for('profile.export_data'))
        self.assert200(resp)

        # send two listens for the user
        resp = self.send_listens()
        self.assert200(resp)

        time.sleep(2)

        # now export data and check if contains all the listens we just sent
        resp = self.client.post(url_for('profile.export_data'))
        self.assert200(resp)
        data = json.loads(resp.data)
        self.assertEqual(len(data), 3)