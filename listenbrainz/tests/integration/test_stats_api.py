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
        """Test to make sure valid response is received
        """
        with open(self.path_to_data_file('artist_statistics.json'), 'r') as f:
            payload = json.load(f)

        db_stats.insert_user_stats(self.user['id'], payload['all_time']['artists'], {}, {}, payload['count'])

        response = self.client.get(url_for('stats_api_v1.get_artist', user_name=self.user['musicbrainz_id']))
        self.assert200(response)
        data = json.loads(response.data)['payload']
        sent_count = payload['count']
        received_count = data['count']
        self.assertEqual(sent_count, received_count)
        sent_total_artist_count = payload['count']
        received_total_artist_count = data['total_artist_count']
        self.assertEqual(sent_total_artist_count, received_total_artist_count)
        sent_artist_list = payload['all_time']['artists']
        received_artist_list = data['artists']
        self.assertListEqual(sent_artist_list, received_artist_list)
        self.assertEqual(data['user_id'], self.user['musicbrainz_id'])

    def test_artist_stat_all_time(self):
        """Test to make sure valid response is received when range is 'all_time'
        """
        with open(self.path_to_data_file('artist_statistics.json'), 'r') as f:
            payload = json.load(f)

        db_stats.insert_user_stats(self.user['id'], payload['all_time']['artists'], {}, {}, payload['count'])

        response = self.client.get(url_for('stats_api_v1.get_artist',
                                           user_name=self.user['musicbrainz_id']), query_string={'range': 'all_time'})
        self.assert200(response)
        data = json.loads(response.data)['payload']
        sent_count = payload['count']
        received_count = data['count']
        self.assertEqual(sent_count, received_count)
        sent_artist_list = payload['all_time']['artists']
        received_artist_list = data['artists']
        self.assertListEqual(sent_artist_list, received_artist_list)
        self.assertEqual(data['range'], 'all_time')
        self.assertEqual(data['user_id'], self.user['musicbrainz_id'])

    def test_artist_stat_invalid_range(self):
        """Test to make sure 400 is received if range argument is invalid
        """
        response = self.client.get(url_for('stats_api_v1.get_artist',
                                           user_name=self.user['musicbrainz_id']), query_string={'range': 'foobar'})
        self.assert400(response)
        self.assertEqual("We currently only support the `all_time` range.", response.json['error'])

    def test_artist_stat_count(self):
        """Test to make sure valid response is received if count argument is passed
        """
        with open(self.path_to_data_file('artist_statistics.json'), 'r') as f:
            payload = json.load(f)

        db_stats.insert_user_stats(self.user['id'], payload['all_time']['artists'], {}, {}, payload['count'])

        response = self.client.get(url_for('stats_api_v1.get_artist',
                                           user_name=self.user['musicbrainz_id']), query_string={'count': 5})
        self.assert200(response)
        data = json.loads(response.data)['payload']
        sent_count = 5
        received_count = data['count']
        self.assertEqual(sent_count, received_count)
        sent_total_artist_count = payload['count']
        received_total_artist_count = data['total_artist_count']
        self.assertEqual(sent_total_artist_count, received_total_artist_count)
        sent_artist_list = payload['all_time']['artists'][:5]
        received_artist_list = data['artists']
        self.assertListEqual(sent_artist_list, received_artist_list)
        self.assertEqual(data['user_id'], self.user['musicbrainz_id'])

    def test_artist_stat_invalid_count(self):
        """Test to make sure 400 response is received if count argument is not of type integer
        """
        response = self.client.get(url_for('stats_api_v1.get_artist',
                                           user_name=self.user['musicbrainz_id']), query_string={'count': 'foobar'})
        self.assert400(response)
        self.assertEqual("'count' should be a non-negative integer", response.json['error'])

    def test_artist_stat_negative_count(self):
        """Test to make sure 400 response is received if count is negative
        """
        response = self.client.get(url_for('stats_api_v1.get_artist',
                                           user_name=self.user['musicbrainz_id']), query_string={'count': -5})
        self.assert400(response)
        self.assertEqual("'count' should be a non-negative integer", response.json['error'])

    def test_artist_stat_offset(self):
        """Test to make sure valid response is received if offset argument is passed

        """
        with open(self.path_to_data_file('artist_statistics.json'), 'r') as f:
            payload = json.load(f)

        db_stats.insert_user_stats(self.user['id'], payload['all_time']['artists'], {}, {}, payload['count'])

        response = self.client.get(url_for('stats_api_v1.get_artist',
                                           user_name=self.user['musicbrainz_id']), query_string={'offset': 5})
        self.assert200(response)
        data = json.loads(response.data)['payload']
        sent_offset = 5
        received_offset = data['offset']
        self.assertEqual(sent_offset, received_offset)
        sent_artist_list = payload['all_time']['artists'][5:]
        received_artist_list = data['artists']
        self.assertListEqual(sent_artist_list, received_artist_list)
        sent_total_artist_count = payload['count']
        received_total_artist_count = data['total_artist_count']
        self.assertEqual(sent_total_artist_count, received_total_artist_count)
        self.assertEqual(data['user_id'], self.user['musicbrainz_id'])

    def test_artist_stat_invalid_offset(self):
        """Test to make sure 400 response is received if offset argument is not of type integer
        """
        response = self.client.get(url_for('stats_api_v1.get_artist',
                                           user_name=self.user['musicbrainz_id']), query_string={'offset': 'foobar'})
        self.assert400(response)
        self.assertEqual("'offset' should be a non-negative integer", response.json['error'])

    def test_artist_stat_negative_offset(self):
        """Test to make sure 400 response is received if offset is negative
        """
        response = self.client.get(url_for('stats_api_v1.get_artist',
                                           user_name=self.user['musicbrainz_id']), query_string={'offset': -5})
        self.assert400(response)
        self.assertEqual("'offset' should be a non-negative integer", response.json['error'])

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
