import json

from flask import url_for

import listenbrainz.db.stats as db_stats
import listenbrainz.db.user as db_user
from listenbrainz.tests.integration import IntegrationTestCase


class APITestCase(IntegrationTestCase):
    def setUp(self):
        super(APITestCase, self).setUp()
        self.user = db_user.get_or_create(1, 'testuserpleaseignore')

    def test_artist(self):
        """Test to make sure valid response is recieved
        """
        with open(self.path_to_data_file('artist_statistics.json'), 'r') as f:
            payload = json.load(f)

        db_stats.insert_user_stats(self.user['id'], payload['all_time']['artists'], {}, {}, payload['count'])

        response = self.client.get(url_for('stats_api_v1.get_artist', user_name=self.user['musicbrainz_id']))
        self.assert200(response)
        data = json.loads(response.data)['payload']
        sent_count = payload['count']
        recieved_count = data['artist']['all_time']['count']
        self.assertEqual(sent_count, recieved_count)
        sent_artist_list = payload['all_time']['artists']
        recieved_artist_list = data['artist']['all_time']['artists']
        self.assertListEqual(sent_artist_list, recieved_artist_list)
        self.assertEqual(data['user_id'], self.user['musicbrainz_id'])

    def test_artist_count(self):
        """Test to make sure valid response is recieved if count argument is passed
        """
        with open(self.path_to_data_file('artist_statistics.json'), 'r') as f:
            payload = json.load(f)

        db_stats.insert_user_stats(self.user['id'], payload['all_time']['artists'], {}, {}, payload['count'])

        response = self.client.get(url_for('stats_api_v1.get_artist',
                                           user_name=self.user['musicbrainz_id']), query_string={'count': 5})
        self.assert200(response)
        data = json.loads(response.data)['payload']
        sent_count = 5
        recieved_count = data['artist']['all_time']['count']
        self.assertEqual(sent_count, recieved_count)
        sent_artist_list = payload['all_time']['artists'][:5]
        recieved_artist_list = data['artist']['all_time']['artists']
        self.assertListEqual(sent_artist_list, recieved_artist_list)
        self.assertEqual(data['user_id'], self.user['musicbrainz_id'])

    def test_artist_stat_invalid_user(self):
        """ Test to make sure that the API sends 404 if user does not exist.
        """

        response = self.client.get(url_for('stats_api_v1.get_artist', user_name='nouser'))
        self.assert404(response)
        self.assertEqual('Cannot find user: nouser', response.json['error'])

    def test_artist_stat_not_calculated(self):
        """ Test to make sure that the API sends 204 if statistics for user have not been calculated yet
        """

        response = self.client.get(url_for('stats_api_v1.get_artist', user_name=self.user['musicbrainz_id']))
        self.assertEqual(response.status_code, 204)
