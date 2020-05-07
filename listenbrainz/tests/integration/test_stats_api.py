import json

from flask import url_for

import listenbrainz.db.stats as db_stats
import listenbrainz.db.user as db_user
from listenbrainz.tests.integration import IntegrationTestCase


class StatsAPITestCase(IntegrationTestCase):
    def setUp(self):
        super(StatsAPITestCase, self).setUp()
        self.user = db_user.get_or_create(1, 'testuserpleaseignore')

    def test_artist_stat(self):
        """Test to make sure valid response is recieved
        """
        with open(self.path_to_data_file('artist_statistics.json'), 'r') as f:
            payload = json.load(f)

        db_stats.insert_user_stats(self.user['id'], payload['all_time']['artists'], {}, {}, payload['count'])

        response = self.client.get(url_for('stats_api_v1.get_artist', user_name=self.user['musicbrainz_id']))
        self.assert200(response)
        data = json.loads(response.data)['payload']
        sent_count = payload['count']
        recieved_count = data['count']
        self.assertEqual(sent_count, recieved_count)
        sent_artist_list = payload['all_time']['artists']
        recieved_artist_list = data['artists']
        self.assertListEqual(sent_artist_list, recieved_artist_list)
        self.assertEqual(data['user_id'], self.user['musicbrainz_id'])

    def test_artist_stat_all_time(self):
        """Test to make sure valid response is recieved when range is 'all_time'
        """
        with open(self.path_to_data_file('artist_statistics.json'), 'r') as f:
            payload = json.load(f)

        db_stats.insert_user_stats(self.user['id'], payload['all_time']['artists'], {}, {}, payload['count'])

        response = self.client.get(url_for('stats_api_v1.get_artist',
                                           user_name=self.user['musicbrainz_id']), query_string={'range': 'all_time'})
        self.assert200(response)
        data = json.loads(response.data)['payload']
        sent_count = payload['count']
        recieved_count = data['count']
        self.assertEqual(sent_count, recieved_count)
        sent_artist_list = payload['all_time']['artists']
        recieved_artist_list = data['artists']
        self.assertListEqual(sent_artist_list, recieved_artist_list)
        self.assertEqual(data['range'], 'all_time')
        self.assertEqual(data['user_id'], self.user['musicbrainz_id'])

    def test_artist_stat_invalid_range(self):
        """Test to make sure 400 is recieved if range argument is invalid
        """
        response = self.client.get(url_for('stats_api_v1.get_artist',
                                           user_name=self.user['musicbrainz_id']), query_string={'range': 'foobar'})
        self.assert400(response)
        self.assertEqual("Bad request, 'range' should have value 'all_time'", response.json['error'])

    def test_artist_stat_count(self):
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
        recieved_count = data['count']
        self.assertEqual(sent_count, recieved_count)
        sent_artist_list = payload['all_time']['artists'][:5]
        recieved_artist_list = data['artists']
        self.assertListEqual(sent_artist_list, recieved_artist_list)
        self.assertEqual(data['user_id'], self.user['musicbrainz_id'])

    def test_artist_stat_invalid_count(self):
        """Test to make sure 400 response is recieved if count argument is not of type integer
        """
        response = self.client.get(url_for('stats_api_v1.get_artist',
                                           user_name=self.user['musicbrainz_id']), query_string={'count': 'foobar'})
        self.assert400(response)
        self.assertEqual("Bad request, 'count' should be a positive integer", response.json['error'])

    def test_artist_stat_negative_count(self):
        """Test to make sure 400 response is recieved if count is negative
        """
        response = self.client.get(url_for('stats_api_v1.get_artist',
                                           user_name=self.user['musicbrainz_id']), query_string={'count': -5})
        self.assert400(response)
        self.assertEqual("Bad request, 'count' should be a positive integer", response.json['error'])

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
