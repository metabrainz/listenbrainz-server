import json

from flask import url_for, current_app
from redis import Redis

import listenbrainz.db.stats as db_stats
import listenbrainz.db.user as db_user
from listenbrainz.tests.integration import IntegrationTestCase


class StatsAPITestCase(IntegrationTestCase):
    def setUp(self):
        super(StatsAPITestCase, self).setUp()
        self.user = db_user.get_or_create(1, 'testuserpleaseignore')

        # Insert artist data
        with open(self.path_to_data_file('user_top_artists_db_data_for_api_test.json'), 'r') as f:
            self.artist_payload = json.load(f)
        db_stats.insert_user_artists(self.user['id'], {'all_time': self.artist_payload})

        # Insert release data
        with open(self.path_to_data_file('user_top_releases_db_data_for_api_test.json'), 'r') as f:
            self.release_payload = json.load(f)
        db_stats.insert_user_releases(self.user['id'], {'all_time': self.release_payload})

    def tearDown(self):
        r = Redis(host=current_app.config['REDIS_HOST'], port=current_app.config['REDIS_PORT'])
        r.flushall()
        super(StatsAPITestCase, self).tearDown()

    def test_artist_stat(self):
        """ Test to make sure valid response is received """
        response = self.client.get(url_for('stats_api_v1.get_artist', user_name=self.user['musicbrainz_id']))
        self.assert200(response)
        data = json.loads(response.data)['payload']
        received_count = data['count']

        self.assertEqual(25, received_count)
        sent_total_artist_count = self.artist_payload['count']
        received_total_artist_count = data['total_artist_count']
        self.assertEqual(sent_total_artist_count, received_total_artist_count)
        sent_from = self.artist_payload['from_ts']
        received_from = data['from_ts']
        self.assertEqual(sent_from, received_from)
        sent_to = self.artist_payload['to_ts']
        received_to = data['to_ts']
        self.assertEqual(sent_to, received_to)
        sent_artist_list = self.artist_payload['artists'][:25]
        received_artist_list = data['artists']
        self.assertListEqual(sent_artist_list, received_artist_list)
        self.assertEqual(data['user_id'], self.user['musicbrainz_id'])

    def test_artist_stat_too_many(self):
        """ Test to make sure response received has maximum 100 listens """
        with open(self.path_to_data_file('user_top_artists_db_data_for_api_test_too_many.json'), 'r') as f:
            payload = json.load(f)

        db_stats.insert_user_artists(self.user['id'], {'all_time': payload})

        response = self.client.get(url_for('stats_api_v1.get_artist',
                                           user_name=self.user['musicbrainz_id']), query_string={'count': 105})
        self.assert200(response)
        data = json.loads(response.data)['payload']
        received_count = data['count']
        self.assertEqual(100, received_count)
        sent_from = payload['from_ts']
        received_from = data['from_ts']
        self.assertEqual(sent_from, received_from)
        sent_to = payload['to_ts']
        received_to = data['to_ts']
        self.assertEqual(sent_to, received_to)
        sent_artist_list = payload['artists'][:100]
        received_artist_list = data['artists']
        self.assertListEqual(sent_artist_list, received_artist_list)
        self.assertEqual(data['user_id'], self.user['musicbrainz_id'])

    def test_artist_stat_all_time(self):
        """ Test to make sure valid response is received when range is 'all_time' """
        response = self.client.get(url_for('stats_api_v1.get_artist',
                                           user_name=self.user['musicbrainz_id']), query_string={'range': 'all_time'})
        self.assert200(response)
        data = json.loads(response.data)['payload']
        received_count = data['count']
        self.assertEqual(25, received_count)
        sent_artist_list = self.artist_payload['artists'][:25]
        received_artist_list = data['artists']
        self.assertListEqual(sent_artist_list, received_artist_list)
        self.assertEqual(data['range'], 'all_time')
        self.assertEqual(data['user_id'], self.user['musicbrainz_id'])

    def test_artist_stat_week(self):
        """ Test to make sure valid response is received when range is 'week' """
        with open(self.path_to_data_file('user_top_artists_db_data_for_api_test.json'), 'r') as f:
            payload = json.load(f)

        payload['range'] = 'week'
        db_stats.insert_user_artists(self.user['id'], {'week': payload})

        response = self.client.get(url_for('stats_api_v1.get_artist',
                                           user_name=self.user['musicbrainz_id']), query_string={'range': 'week'})
        self.assert200(response)
        data = json.loads(response.data)['payload']
        received_count = data['count']
        self.assertEqual(25, received_count)
        sent_artist_list = payload['artists'][:25]
        received_artist_list = data['artists']
        self.assertListEqual(sent_artist_list, received_artist_list)
        self.assertEqual(data['range'], 'week')
        self.assertEqual(data['user_id'], self.user['musicbrainz_id'])

    def test_artist_stat_month(self):
        """ Test to make sure valid response is received when range is 'month' """
        with open(self.path_to_data_file('user_top_artists_db_data_for_api_test.json'), 'r') as f:
            payload = json.load(f)

        db_stats.insert_user_artists(self.user['id'], {'month': payload})

        response = self.client.get(url_for('stats_api_v1.get_artist',
                                           user_name=self.user['musicbrainz_id']), query_string={'range': 'month'})
        self.assert200(response)
        data = json.loads(response.data)['payload']
        received_count = data['count']
        self.assertEqual(25, received_count)
        sent_artist_list = payload['artists'][:25]
        received_artist_list = data['artists']
        self.assertListEqual(sent_artist_list, received_artist_list)
        self.assertEqual(data['range'], 'month')
        self.assertEqual(data['user_id'], self.user['musicbrainz_id'])

    def test_artist_stat_year(self):
        """ Test to make sure valid response is received when range is 'year' """
        with open(self.path_to_data_file('user_top_artists_db_data_for_api_test.json'), 'r') as f:
            payload = json.load(f)

        db_stats.insert_user_artists(self.user['id'], {'year': payload})

        response = self.client.get(url_for('stats_api_v1.get_artist',
                                           user_name=self.user['musicbrainz_id']), query_string={'range': 'year'})
        self.assert200(response)
        data = json.loads(response.data)['payload']
        received_count = data['count']
        self.assertEqual(25, received_count)
        sent_artist_list = payload['artists'][:25]
        received_artist_list = data['artists']
        self.assertListEqual(sent_artist_list, received_artist_list)
        self.assertEqual(data['range'], 'year')
        self.assertEqual(data['user_id'], self.user['musicbrainz_id'])

    def test_artist_stat_invalid_range(self):
        """ Test to make sure 400 is received if range argument is invalid """
        response = self.client.get(url_for('stats_api_v1.get_artist',
                                           user_name=self.user['musicbrainz_id']), query_string={'range': 'foobar'})
        self.assert400(response)
        self.assertEqual("Invalid range: foobar", response.json['error'])

    def test_artist_stat_count(self):
        """ Test to make sure valid response is received if count argument is passed """
        with open(self.path_to_data_file('user_top_artists_db_data_for_api_test.json'), 'r') as f:
            payload = json.load(f)

        db_stats.insert_user_artists(self.user['id'], {'all_time': payload})

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
        sent_artist_list = payload['artists'][:5]
        received_artist_list = data['artists']
        self.assertListEqual(sent_artist_list, received_artist_list)
        self.assertEqual(data['user_id'], self.user['musicbrainz_id'])

    def test_artist_stat_invalid_count(self):
        """ Test to make sure 400 response is received if count argument is not of type integer """
        response = self.client.get(url_for('stats_api_v1.get_artist',
                                           user_name=self.user['musicbrainz_id']), query_string={'count': 'foobar'})
        self.assert400(response)
        self.assertEqual("'count' should be a non-negative integer", response.json['error'])

    def test_artist_stat_negative_count(self):
        """ Test to make sure 400 response is received if count is negative """
        response = self.client.get(url_for('stats_api_v1.get_artist',
                                           user_name=self.user['musicbrainz_id']), query_string={'count': -5})
        self.assert400(response)
        self.assertEqual("'count' should be a non-negative integer", response.json['error'])

    def test_artist_stat_offset(self):
        """ Test to make sure valid response is received if offset argument is passed """
        with open(self.path_to_data_file('user_top_artists_db_data_for_api_test.json'), 'r') as f:
            payload = json.load(f)

        db_stats.insert_user_artists(self.user['id'], {'all_time': payload})

        response = self.client.get(url_for('stats_api_v1.get_artist',
                                           user_name=self.user['musicbrainz_id']), query_string={'offset': 5})
        self.assert200(response)
        data = json.loads(response.data)['payload']
        sent_offset = 5
        received_offset = data['offset']
        self.assertEqual(sent_offset, received_offset)
        sent_artist_list = payload['artists'][5:30]
        received_artist_list = data['artists']
        self.assertListEqual(sent_artist_list, received_artist_list)
        sent_total_artist_count = payload['count']
        received_total_artist_count = data['total_artist_count']
        self.assertEqual(sent_total_artist_count, received_total_artist_count)
        self.assertEqual(data['user_id'], self.user['musicbrainz_id'])

    def test_artist_stat_invalid_offset(self):
        """ Test to make sure 400 response is received if offset argument is not of type integer """
        response = self.client.get(url_for('stats_api_v1.get_artist',
                                           user_name=self.user['musicbrainz_id']), query_string={'offset': 'foobar'})
        self.assert400(response)
        self.assertEqual("'offset' should be a non-negative integer", response.json['error'])

    def test_artist_stat_negative_offset(self):
        """ Test to make sure 400 response is received if offset is negative """
        response = self.client.get(url_for('stats_api_v1.get_artist',
                                           user_name=self.user['musicbrainz_id']), query_string={'offset': -5})
        self.assert400(response)
        self.assertEqual("'offset' should be a non-negative integer", response.json['error'])

    def test_artist_stat_invalid_user(self):
        """ Test to make sure that the API sends 404 if user does not exist. """
        response = self.client.get(url_for('stats_api_v1.get_artist', user_name='nouser'))
        self.assert404(response)
        self.assertEqual('Cannot find user: nouser', response.json['error'])

    def test_artist_stat_not_calculated(self):
        """ Test to make sure that the API sends 204 if statistics for user have not been calculated yet """
        db_stats.delete_user_stats(self.user['id'])
        response = self.client.get(url_for('stats_api_v1.get_artist', user_name=self.user['musicbrainz_id']))
        self.assertEqual(response.status_code, 204)

    def test_artist_range_stat_not_calculated(self):
        """ Test to make sure that the API sends 204 if particular range statistics for user have not been calculated yet """
        response = self.client.get(url_for('stats_api_v1.get_artist',
                                           user_name=self.user['musicbrainz_id']), query_string={'range': 'year'})
        self.assertEqual(response.status_code, 204)

    def test_release_stat(self):
        """ Test to make sure valid response is received """
        response = self.client.get(url_for('stats_api_v1.get_release', user_name=self.user['musicbrainz_id']))
        self.assert200(response)
        data = json.loads(response.data)['payload']
        received_count = data['count']

        self.assertEqual(25, received_count)
        sent_total_release_count = self.release_payload['count']
        received_total_release_count = data['total_release_count']
        self.assertEqual(sent_total_release_count, received_total_release_count)
        sent_from = self.release_payload['from_ts']
        received_from = data['from_ts']
        self.assertEqual(sent_from, received_from)
        sent_to = self.release_payload['to_ts']
        received_to = data['to_ts']
        self.assertEqual(sent_to, received_to)
        sent_release_list = self.release_payload['releases'][:25]
        received_release_list = data['releases']
        self.assertListEqual(sent_release_list, received_release_list)
        self.assertEqual(data['user_id'], self.user['musicbrainz_id'])

    def test_release_stat_too_many(self):
        """ Test to make sure response received has maximum 100 listens """
        with open(self.path_to_data_file('user_top_releases_db_data_for_api_test_too_many.json'), 'r') as f:
            payload = json.load(f)

        db_stats.insert_user_releases(self.user['id'], {'all_time': payload})

        response = self.client.get(url_for('stats_api_v1.get_release',
                                           user_name=self.user['musicbrainz_id']), query_string={'count': 105})
        self.assert200(response)
        data = json.loads(response.data)['payload']
        received_count = data['count']
        self.assertEqual(100, received_count)
        sent_from = payload['from_ts']
        received_from = data['from_ts']
        self.assertEqual(sent_from, received_from)
        sent_to = payload['to_ts']
        received_to = data['to_ts']
        self.assertEqual(sent_to, received_to)
        sent_release_list = payload['releases'][:100]
        received_release_list = data['releases']
        self.assertListEqual(sent_release_list, received_release_list)
        self.assertEqual(data['user_id'], self.user['musicbrainz_id'])

    def test_release_stat_all_time(self):
        """ Test to make sure valid response is received when range is 'all_time' """
        response = self.client.get(url_for('stats_api_v1.get_release',
                                           user_name=self.user['musicbrainz_id']), query_string={'range': 'all_time'})
        self.assert200(response)
        data = json.loads(response.data)['payload']
        received_count = data['count']
        self.assertEqual(25, received_count)
        sent_release_list = self.release_payload['releases'][:25]
        received_release_list = data['releases']
        self.assertListEqual(sent_release_list, received_release_list)
        self.assertEqual(data['range'], 'all_time')
        self.assertEqual(data['user_id'], self.user['musicbrainz_id'])

    def test_release_stat_week(self):
        """ Test to make sure valid response is received when range is 'week' """
        with open(self.path_to_data_file('user_top_releases_db_data_for_api_test.json'), 'r') as f:
            payload = json.load(f)

        payload['range'] = 'week'
        db_stats.insert_user_releases(self.user['id'], {'week': payload})

        response = self.client.get(url_for('stats_api_v1.get_release',
                                           user_name=self.user['musicbrainz_id']), query_string={'range': 'week'})
        self.assert200(response)
        data = json.loads(response.data)['payload']
        received_count = data['count']
        self.assertEqual(25, received_count)
        sent_release_list = payload['releases'][:25]
        received_release_list = data['releases']
        self.assertListEqual(sent_release_list, received_release_list)
        self.assertEqual(data['range'], 'week')
        self.assertEqual(data['user_id'], self.user['musicbrainz_id'])

    def test_release_stat_month(self):
        """ Test to make sure valid response is received when range is 'month' """
        with open(self.path_to_data_file('user_top_releases_db_data_for_api_test.json'), 'r') as f:
            payload = json.load(f)

        db_stats.insert_user_releases(self.user['id'], {'month': payload})

        response = self.client.get(url_for('stats_api_v1.get_release',
                                           user_name=self.user['musicbrainz_id']), query_string={'range': 'month'})
        self.assert200(response)
        data = json.loads(response.data)['payload']
        received_count = data['count']
        self.assertEqual(25, received_count)
        sent_release_list = payload['releases'][:25]
        received_release_list = data['releases']
        self.assertListEqual(sent_release_list, received_release_list)
        self.assertEqual(data['range'], 'month')
        self.assertEqual(data['user_id'], self.user['musicbrainz_id'])

    def test_release_stat_year(self):
        """ Test to make sure valid response is received when range is 'year' """
        with open(self.path_to_data_file('user_top_releases_db_data_for_api_test.json'), 'r') as f:
            payload = json.load(f)

        db_stats.insert_user_releases(self.user['id'], {'year': payload})

        response = self.client.get(url_for('stats_api_v1.get_release',
                                           user_name=self.user['musicbrainz_id']), query_string={'range': 'year'})
        self.assert200(response)
        data = json.loads(response.data)['payload']
        received_count = data['count']
        self.assertEqual(25, received_count)
        sent_release_list = payload['releases'][:25]
        received_release_list = data['releases']
        self.assertListEqual(sent_release_list, received_release_list)
        self.assertEqual(data['range'], 'year')
        self.assertEqual(data['user_id'], self.user['musicbrainz_id'])

    def test_release_stat_invalid_range(self):
        """ Test to make sure 400 is received if range argument is invalid """
        response = self.client.get(url_for('stats_api_v1.get_release',
                                           user_name=self.user['musicbrainz_id']), query_string={'range': 'foobar'})
        self.assert400(response)
        self.assertEqual("Invalid range: foobar", response.json['error'])

    def test_release_stat_count(self):
        """ Test to make sure valid response is received if count argument is passed """
        with open(self.path_to_data_file('user_top_releases_db_data_for_api_test.json'), 'r') as f:
            payload = json.load(f)

        db_stats.insert_user_releases(self.user['id'], {'all_time': payload})

        response = self.client.get(url_for('stats_api_v1.get_release',
                                           user_name=self.user['musicbrainz_id']), query_string={'count': 5})
        self.assert200(response)
        data = json.loads(response.data)['payload']
        sent_count = 5
        received_count = data['count']
        self.assertEqual(sent_count, received_count)
        sent_total_release_count = payload['count']
        received_total_release_count = data['total_release_count']
        self.assertEqual(sent_total_release_count, received_total_release_count)
        sent_release_list = payload['releases'][:5]
        received_release_list = data['releases']
        self.assertListEqual(sent_release_list, received_release_list)
        self.assertEqual(data['user_id'], self.user['musicbrainz_id'])

    def test_release_stat_invalid_count(self):
        """ Test to make sure 400 response is received if count argument is not of type integer """
        response = self.client.get(url_for('stats_api_v1.get_release',
                                           user_name=self.user['musicbrainz_id']), query_string={'count': 'foobar'})
        self.assert400(response)
        self.assertEqual("'count' should be a non-negative integer", response.json['error'])

    def test_release_stat_negative_count(self):
        """ Test to make sure 400 response is received if count is negative """
        response = self.client.get(url_for('stats_api_v1.get_release',
                                           user_name=self.user['musicbrainz_id']), query_string={'count': -5})
        self.assert400(response)
        self.assertEqual("'count' should be a non-negative integer", response.json['error'])

    def test_release_stat_offset(self):
        """ Test to make sure valid response is received if offset argument is passed """
        with open(self.path_to_data_file('user_top_releases_db_data_for_api_test.json'), 'r') as f:
            payload = json.load(f)

        db_stats.insert_user_releases(self.user['id'], {'all_time': payload})

        response = self.client.get(url_for('stats_api_v1.get_release',
                                           user_name=self.user['musicbrainz_id']), query_string={'offset': 5})
        self.assert200(response)
        data = json.loads(response.data)['payload']
        sent_offset = 5
        received_offset = data['offset']
        self.assertEqual(sent_offset, received_offset)
        sent_release_list = payload['releases'][5:30]
        received_release_list = data['releases']
        self.assertListEqual(sent_release_list, received_release_list)
        sent_total_release_count = payload['count']
        received_total_release_count = data['total_release_count']
        self.assertEqual(sent_total_release_count, received_total_release_count)
        self.assertEqual(data['user_id'], self.user['musicbrainz_id'])

    def test_release_stat_invalid_offset(self):
        """ Test to make sure 400 response is received if offset argument is not of type integer """
        response = self.client.get(url_for('stats_api_v1.get_release',
                                           user_name=self.user['musicbrainz_id']), query_string={'offset': 'foobar'})
        self.assert400(response)
        self.assertEqual("'offset' should be a non-negative integer", response.json['error'])

    def test_release_stat_negative_offset(self):
        """ Test to make sure 400 response is received if offset is negative """
        response = self.client.get(url_for('stats_api_v1.get_release',
                                           user_name=self.user['musicbrainz_id']), query_string={'offset': -5})
        self.assert400(response)
        self.assertEqual("'offset' should be a non-negative integer", response.json['error'])

    def test_release_stat_invalid_user(self):
        """ Test to make sure that the API sends 404 if user does not exist. """
        response = self.client.get(url_for('stats_api_v1.get_release', user_name='nouser'))
        self.assert404(response)
        self.assertEqual('Cannot find user: nouser', response.json['error'])

    def test_release_stat_not_calculated(self):
        """ Test to make sure that the API sends 204 if statistics for user have not been calculated yet """
        db_stats.delete_user_stats(self.user['id'])
        response = self.client.get(url_for('stats_api_v1.get_release', user_name=self.user['musicbrainz_id']))
        self.assertEqual(response.status_code, 204)

    def test_release_range_stat_not_calculated(self):
        """ Test to make sure that the API sends 204 if particular range statistics for user have not been calculated yet """
        response = self.client.get(url_for('stats_api_v1.get_release',
                                           user_name=self.user['musicbrainz_id']), query_string={'range': 'year'})
        self.assertEqual(response.status_code, 204)
