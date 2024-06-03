import json
from listenbrainz.tests.integration import ListenAPIIntegrationTestCase


class AtomFeedsTestCase(ListenAPIIntegrationTestCase):
    def test_user_listens_feed(self):
        with open(self.path_to_data_file('single_more_than_one_listen.json'), 'r') as f:
            payload = json.load(f)
        response = self.send_data(payload)
        self.assert400(response)
        self.assertEqual(response.json['code'], 400)
        response = self.client.get('/atom/user/testuserpleaseignore/listens')
        self.assertEqual(response.status_code, 200)