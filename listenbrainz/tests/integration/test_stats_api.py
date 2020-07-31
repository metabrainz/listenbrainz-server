import json
from datetime import datetime
from unittest.mock import patch

import listenbrainz.db.stats as db_stats
import listenbrainz.db.user as db_user
import requests_mock
from data.model.user_artist_map import (UserArtistMapRecord,
                                        UserArtistMapStatJson)
from data.model.user_artist_stat import UserArtistStatJson
from data.model.user_daily_activity import UserDailyActivityStatJson
from data.model.user_listening_activity import UserListeningActivityStatJson
from data.model.user_recording_stat import UserRecordingStatJson
from data.model.user_release_stat import UserReleaseStatJson
from flask import current_app, url_for
from listenbrainz.tests.integration import IntegrationTestCase
from listenbrainz.webserver.views.stats_api import _get_country_codes
from redis import Redis


class MockDate(datetime):
    """ Mock class for datetime which returns epoch """
    @classmethod
    def now(cls):
        return cls.fromtimestamp(0)


class StatsAPITestCase(IntegrationTestCase):
    def setUp(self):
        super(StatsAPITestCase, self).setUp()
        self.user = db_user.get_or_create(1, 'testuserpleaseignore')

        # Insert artist data
        with open(self.path_to_data_file('user_top_artists_db_data_for_api_test.json'), 'r') as f:
            self.artist_payload = json.load(f)
        db_stats.insert_user_artists(self.user['id'], UserArtistStatJson(**{'all_time': self.artist_payload}))

        # Insert release data
        with open(self.path_to_data_file('user_top_releases_db_data_for_api_test.json'), 'r') as f:
            self.release_payload = json.load(f)
        db_stats.insert_user_releases(self.user['id'], UserReleaseStatJson(**{'all_time': self.release_payload}))

        # Insert recording data
        with open(self.path_to_data_file('user_top_recordings_db_data_for_api_test.json'), 'r') as f:
            self.recording_payload = json.load(f)
        db_stats.insert_user_recordings(self.user['id'], UserRecordingStatJson(**{'all_time': self.recording_payload}))

        # Insert listening activity data
        with open(self.path_to_data_file('user_listening_activity_db_data_for_api_test.json')) as f:
            self.listening_activity_payload = json.load(f)
        db_stats.insert_user_listening_activity(self.user['id'], UserListeningActivityStatJson(
            **{'all_time': self.listening_activity_payload}))

        # Insert daily activity data
        with open(self.path_to_data_file('user_daily_activity_db_data_for_api_test.json')) as f:
            self.daily_activity_payload = json.load(f)
        db_stats.insert_user_daily_activity(self.user['id'], UserDailyActivityStatJson(
            **{'all_time': self.daily_activity_payload}))

        # Insert artist map data
        with open(self.path_to_data_file('user_artist_map_db_data_for_api_test.json')) as f:
            self.artist_map_payload = json.load(f)
        db_stats.insert_user_artist_map(self.user['id'], UserArtistMapStatJson(
            **{'all_time': self.artist_map_payload}))

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

        db_stats.insert_user_artists(self.user['id'], UserArtistStatJson(**{'all_time': payload}))

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
        with open(self.path_to_data_file('user_top_artists_db_data_for_api_test_week.json'), 'r') as f:
            payload = json.load(f)

        db_stats.insert_user_artists(self.user['id'], UserArtistStatJson(**{'week': payload}))

        response = self.client.get(url_for('stats_api_v1.get_artist',
                                           user_name=self.user['musicbrainz_id']), query_string={'range': 'week'})
        self.assert200(response)
        data = json.loads(response.data)['payload']
        received_count = data['count']
        self.assertEqual(24, received_count)
        sent_artist_list = payload['artists'][:25]
        received_artist_list = data['artists']
        self.assertListEqual(sent_artist_list, received_artist_list)
        self.assertEqual(data['range'], 'week')
        self.assertEqual(data['user_id'], self.user['musicbrainz_id'])

    def test_artist_stat_month(self):
        """ Test to make sure valid response is received when range is 'month' """
        with open(self.path_to_data_file('user_top_artists_db_data_for_api_test_month.json'), 'r') as f:
            payload = json.load(f)

        db_stats.insert_user_artists(self.user['id'], UserArtistStatJson(**{'month': payload}))

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
        with open(self.path_to_data_file('user_top_artists_db_data_for_api_test_year.json'), 'r') as f:
            payload = json.load(f)

        db_stats.insert_user_artists(self.user['id'], UserArtistStatJson(**{'year': payload}))

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

        db_stats.insert_user_artists(self.user['id'], UserArtistStatJson(**{'all_time': payload}))

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

        db_stats.insert_user_artists(self.user['id'], UserArtistStatJson(**{'all_time': payload}))

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

        db_stats.insert_user_releases(self.user['id'], UserReleaseStatJson(**{'all_time': payload}))

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
        with open(self.path_to_data_file('user_top_releases_db_data_for_api_test_week.json'), 'r') as f:
            payload = json.load(f)

        db_stats.insert_user_releases(self.user['id'], UserReleaseStatJson(**{'week': payload}))

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
        with open(self.path_to_data_file('user_top_releases_db_data_for_api_test_month.json'), 'r') as f:
            payload = json.load(f)

        db_stats.insert_user_releases(self.user['id'], UserReleaseStatJson(**{'month': payload}))

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
        with open(self.path_to_data_file('user_top_releases_db_data_for_api_test_year.json'), 'r') as f:
            payload = json.load(f)

        db_stats.insert_user_releases(self.user['id'], UserReleaseStatJson(**{'year': payload}))

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

        db_stats.insert_user_releases(self.user['id'], UserReleaseStatJson(**{'all_time': payload}))

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

        db_stats.insert_user_releases(self.user['id'], UserReleaseStatJson(**{'all_time': payload}))

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

    def test_recording_stat(self):
        """ Test to make sure valid response is received """
        response = self.client.get(url_for('stats_api_v1.get_recording', user_name=self.user['musicbrainz_id']))
        self.assert200(response)
        data = json.loads(response.data)['payload']
        received_count = data['count']

        self.assertEqual(25, received_count)
        sent_total_recording_count = self.recording_payload['count']
        received_total_recording_count = data['total_recording_count']
        self.assertEqual(sent_total_recording_count, received_total_recording_count)
        sent_from = self.recording_payload['from_ts']
        received_from = data['from_ts']
        self.assertEqual(sent_from, received_from)
        sent_to = self.recording_payload['to_ts']
        received_to = data['to_ts']
        self.assertEqual(sent_to, received_to)
        sent_recording_list = self.recording_payload['recordings'][:25]
        received_recording_list = data['recordings']
        self.assertListEqual(sent_recording_list, received_recording_list)
        self.assertEqual(data['user_id'], self.user['musicbrainz_id'])

    def test_recording_stat_too_many(self):
        """ Test to make sure response received has maximum 100 listens """
        with open(self.path_to_data_file('user_top_recordings_db_data_for_api_test_too_many.json'), 'r') as f:
            payload = json.load(f)

        db_stats.insert_user_recordings(self.user['id'], UserRecordingStatJson(**{'all_time': payload}))

        response = self.client.get(url_for('stats_api_v1.get_recording',
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
        sent_recording_list = payload['recordings'][:100]
        received_recording_list = data['recordings']
        self.assertListEqual(sent_recording_list, received_recording_list)
        self.assertEqual(data['user_id'], self.user['musicbrainz_id'])

    def test_recording_stat_all_time(self):
        """ Test to make sure valid response is received when range is 'all_time' """
        response = self.client.get(url_for('stats_api_v1.get_recording',
                                           user_name=self.user['musicbrainz_id']), query_string={'range': 'all_time'})
        self.assert200(response)
        data = json.loads(response.data)['payload']
        received_count = data['count']
        self.assertEqual(25, received_count)
        sent_recording_list = self.recording_payload['recordings'][:25]
        received_recording_list = data['recordings']
        self.assertListEqual(sent_recording_list, received_recording_list)
        self.assertEqual(data['range'], 'all_time')
        self.assertEqual(data['user_id'], self.user['musicbrainz_id'])

    def test_recording_stat_week(self):
        """ Test to make sure valid response is received when range is 'week' """
        with open(self.path_to_data_file('user_top_recordings_db_data_for_api_test_week.json'), 'r') as f:
            payload = json.load(f)

        db_stats.insert_user_recordings(self.user['id'], UserRecordingStatJson(**{'week': payload}))

        response = self.client.get(url_for('stats_api_v1.get_recording',
                                           user_name=self.user['musicbrainz_id']), query_string={'range': 'week'})
        self.assert200(response)
        data = json.loads(response.data)['payload']
        received_count = data['count']
        self.assertEqual(25, received_count)
        sent_recording_list = payload['recordings'][:25]
        received_recording_list = data['recordings']
        self.assertListEqual(sent_recording_list, received_recording_list)
        self.assertEqual(data['range'], 'week')
        self.assertEqual(data['user_id'], self.user['musicbrainz_id'])

    def test_recording_stat_month(self):
        """ Test to make sure valid response is received when range is 'month' """
        with open(self.path_to_data_file('user_top_recordings_db_data_for_api_test_month.json'), 'r') as f:
            payload = json.load(f)

        db_stats.insert_user_recordings(self.user['id'], UserRecordingStatJson(**{'month': payload}))

        response = self.client.get(url_for('stats_api_v1.get_recording',
                                           user_name=self.user['musicbrainz_id']), query_string={'range': 'month'})
        self.assert200(response)
        data = json.loads(response.data)['payload']
        received_count = data['count']
        self.assertEqual(25, received_count)
        sent_recording_list = payload['recordings'][:25]
        received_recording_list = data['recordings']
        self.assertListEqual(sent_recording_list, received_recording_list)
        self.assertEqual(data['range'], 'month')
        self.assertEqual(data['user_id'], self.user['musicbrainz_id'])

    def test_recording_stat_year(self):
        """ Test to make sure valid response is received when range is 'year' """
        with open(self.path_to_data_file('user_top_recordings_db_data_for_api_test_year.json'), 'r') as f:
            payload = json.load(f)

        db_stats.insert_user_recordings(self.user['id'], UserRecordingStatJson(**{'year': payload}))

        response = self.client.get(url_for('stats_api_v1.get_recording',
                                           user_name=self.user['musicbrainz_id']), query_string={'range': 'year'})
        self.assert200(response)
        data = json.loads(response.data)['payload']
        received_count = data['count']
        self.assertEqual(25, received_count)
        sent_recording_list = payload['recordings'][:25]
        received_recording_list = data['recordings']
        self.assertListEqual(sent_recording_list, received_recording_list)
        self.assertEqual(data['range'], 'year')
        self.assertEqual(data['user_id'], self.user['musicbrainz_id'])

    def test_recording_stat_invalid_range(self):
        """ Test to make sure 400 is received if range argument is invalid """
        response = self.client.get(url_for('stats_api_v1.get_recording',
                                           user_name=self.user['musicbrainz_id']), query_string={'range': 'foobar'})
        self.assert400(response)
        self.assertEqual("Invalid range: foobar", response.json['error'])

    def test_recording_stat_count(self):
        """ Test to make sure valid response is received if count argument is passed """
        with open(self.path_to_data_file('user_top_recordings_db_data_for_api_test.json'), 'r') as f:
            payload = json.load(f)

        db_stats.insert_user_recordings(self.user['id'], UserRecordingStatJson(**{'all_time': payload}))

        response = self.client.get(url_for('stats_api_v1.get_recording',
                                           user_name=self.user['musicbrainz_id']), query_string={'count': 5})
        self.assert200(response)
        data = json.loads(response.data)['payload']
        sent_count = 5
        received_count = data['count']
        self.assertEqual(sent_count, received_count)
        sent_total_recording_count = payload['count']
        received_total_recording_count = data['total_recording_count']
        self.assertEqual(sent_total_recording_count, received_total_recording_count)
        sent_recording_list = payload['recordings'][:5]
        received_recording_list = data['recordings']
        self.assertListEqual(sent_recording_list, received_recording_list)
        self.assertEqual(data['user_id'], self.user['musicbrainz_id'])

    def test_recording_stat_invalid_count(self):
        """ Test to make sure 400 response is received if count argument is not of type integer """
        response = self.client.get(url_for('stats_api_v1.get_recording',
                                           user_name=self.user['musicbrainz_id']), query_string={'count': 'foobar'})
        self.assert400(response)
        self.assertEqual("'count' should be a non-negative integer", response.json['error'])

    def test_recording_stat_negative_count(self):
        """ Test to make sure 400 response is received if count is negative """
        response = self.client.get(url_for('stats_api_v1.get_recording',
                                           user_name=self.user['musicbrainz_id']), query_string={'count': -5})
        self.assert400(response)
        self.assertEqual("'count' should be a non-negative integer", response.json['error'])

    def test_recording_stat_offset(self):
        """ Test to make sure valid response is received if offset argument is passed """
        with open(self.path_to_data_file('user_top_recordings_db_data_for_api_test.json'), 'r') as f:
            payload = json.load(f)

        db_stats.insert_user_recordings(self.user['id'], UserRecordingStatJson(**{'all_time': payload}))

        response = self.client.get(url_for('stats_api_v1.get_recording',
                                           user_name=self.user['musicbrainz_id']), query_string={'offset': 5})
        self.assert200(response)
        data = json.loads(response.data)['payload']
        sent_offset = 5
        received_offset = data['offset']
        self.assertEqual(sent_offset, received_offset)
        sent_recording_list = payload['recordings'][5:30]
        received_recording_list = data['recordings']
        self.assertListEqual(sent_recording_list, received_recording_list)
        sent_total_recording_count = payload['count']
        received_total_recording_count = data['total_recording_count']
        self.assertEqual(sent_total_recording_count, received_total_recording_count)
        self.assertEqual(data['user_id'], self.user['musicbrainz_id'])

    def test_recording_stat_invalid_offset(self):
        """ Test to make sure 400 response is received if offset argument is not of type integer """
        response = self.client.get(url_for('stats_api_v1.get_recording',
                                           user_name=self.user['musicbrainz_id']), query_string={'offset': 'foobar'})
        self.assert400(response)
        self.assertEqual("'offset' should be a non-negative integer", response.json['error'])

    def test_recording_stat_negative_offset(self):
        """ Test to make sure 400 response is received if offset is negative """
        response = self.client.get(url_for('stats_api_v1.get_recording',
                                           user_name=self.user['musicbrainz_id']), query_string={'offset': -5})
        self.assert400(response)
        self.assertEqual("'offset' should be a non-negative integer", response.json['error'])

    def test_recording_stat_invalid_user(self):
        """ Test to make sure that the API sends 404 if user does not exist. """
        response = self.client.get(url_for('stats_api_v1.get_recording', user_name='nouser'))
        self.assert404(response)
        self.assertEqual('Cannot find user: nouser', response.json['error'])

    def test_recording_stat_not_calculated(self):
        """ Test to make sure that the API sends 204 if statistics for user have not been calculated yet """
        db_stats.delete_user_stats(self.user['id'])
        response = self.client.get(url_for('stats_api_v1.get_recording', user_name=self.user['musicbrainz_id']))
        self.assertEqual(response.status_code, 204)

    def test_recording_range_stat_not_calculated(self):
        """ Test to make sure that the API sends 204 if particular range statistics for user have not been calculated yet """
        response = self.client.get(url_for('stats_api_v1.get_recording',
                                           user_name=self.user['musicbrainz_id']), query_string={'range': 'year'})
        self.assertEqual(response.status_code, 204)

    def test_entity_stat_not_calculated(self):
        """ Test to make sure that the API sends 204 if particular entity
            statistics for user have not been calculated yet
        """
        # Make sure release stats are calculated, but artist stats are not
        db_stats.delete_user_stats(self.user['id'])
        with open(self.path_to_data_file('user_top_releases_db_data_for_api_test.json'), 'r') as f:
            payload = json.load(f)
        db_stats.insert_user_releases(self.user['id'], UserReleaseStatJson(**{'all_time': payload}))

        response = self.client.get(url_for('stats_api_v1.get_artist',
                                           user_name=self.user['musicbrainz_id']), query_string={'range': 'year'})
        self.assertEqual(response.status_code, 204)

    def test_entity_range_stat_not_calculated(self):
        """ Test to make sure that the API sends 204 if particular entity time
            range statistics for user have not been calculated yet
        """
        # Make sure release stats are calculated, but artist stats are not
        db_stats.delete_user_stats(self.user['id'])
        with open(self.path_to_data_file('user_top_releases_db_data_for_api_test.json'), 'r') as f:
            payload = json.load(f)
        db_stats.insert_user_releases(self.user['id'], UserReleaseStatJson(**{'all_time': payload}))

        response = self.client.get(url_for('stats_api_v1.get_release',
                                           user_name=self.user['musicbrainz_id']), query_string={'range': 'year'})
        self.assertEqual(response.status_code, 204)

    def test_listening_activity_stat(self):
        """ Test to make sure valid response is received """
        response = self.client.get(url_for('stats_api_v1.get_listening_activity', user_name=self.user['musicbrainz_id']))
        self.assert200(response)
        data = json.loads(response.data)['payload']

        sent_from = self.listening_activity_payload['from_ts']
        received_from = data['from_ts']
        self.assertEqual(sent_from, received_from)
        sent_to = self.listening_activity_payload['to_ts']
        received_to = data['to_ts']
        self.assertEqual(sent_to, received_to)
        sent_listening_activity = self.listening_activity_payload['listening_activity']
        received_listening_activity = data['listening_activity']
        self.assertListEqual(sent_listening_activity, received_listening_activity)
        self.assertEqual(data['user_id'], self.user['musicbrainz_id'])

    def test_listening_activity_stat_all_time(self):
        """ Test to make sure valid response is received when range is 'all_time' """
        response = self.client.get(url_for('stats_api_v1.get_listening_activity',
                                           user_name=self.user['musicbrainz_id']), query_string={'range': 'all_time'})
        self.assert200(response)
        data = json.loads(response.data)['payload']
        sent_listening_activity = self.listening_activity_payload['listening_activity']
        received_listening_activity = data['listening_activity']
        self.assertListEqual(sent_listening_activity, received_listening_activity)
        self.assertEqual(data['range'], 'all_time')
        self.assertEqual(data['user_id'], self.user['musicbrainz_id'])

    def test_listening_activity_stat_week(self):
        """ Test to make sure valid response is received when range is 'week' """
        with open(self.path_to_data_file('user_listening_activity_db_data_for_api_test_week.json'), 'r') as f:
            payload = json.load(f)

        db_stats.insert_user_listening_activity(self.user['id'], UserListeningActivityStatJson(**{'week': payload}))

        response = self.client.get(url_for('stats_api_v1.get_listening_activity',
                                           user_name=self.user['musicbrainz_id']), query_string={'range': 'week'})
        self.assert200(response)
        data = json.loads(response.data)['payload']
        sent_listening_activity = payload['listening_activity']
        received_listening_activity = data['listening_activity']
        self.assertListEqual(sent_listening_activity, received_listening_activity)
        self.assertEqual(data['range'], 'week')
        self.assertEqual(data['user_id'], self.user['musicbrainz_id'])

    def test_listening_activity_stat_month(self):
        """ Test to make sure valid response is received when range is 'month' """
        with open(self.path_to_data_file('user_listening_activity_db_data_for_api_test_month.json'), 'r') as f:
            payload = json.load(f)

        db_stats.insert_user_listening_activity(self.user['id'], UserListeningActivityStatJson(**{'month': payload}))

        response = self.client.get(url_for('stats_api_v1.get_listening_activity',
                                           user_name=self.user['musicbrainz_id']), query_string={'range': 'month'})
        self.assert200(response)
        data = json.loads(response.data)['payload']
        sent_listening_activity = payload['listening_activity']
        received_listening_activity = data['listening_activity']
        self.assertListEqual(sent_listening_activity, received_listening_activity)
        self.assertEqual(data['range'], 'month')
        self.assertEqual(data['user_id'], self.user['musicbrainz_id'])

    def test_listening_activity_stat_year(self):
        """ Test to make sure valid response is received when range is 'year' """
        with open(self.path_to_data_file('user_listening_activity_db_data_for_api_test_year.json'), 'r') as f:
            payload = json.load(f)

        db_stats.insert_user_listening_activity(self.user['id'], UserListeningActivityStatJson(**{'year': payload}))

        response = self.client.get(url_for('stats_api_v1.get_listening_activity',
                                           user_name=self.user['musicbrainz_id']), query_string={'range': 'year'})
        self.assert200(response)
        data = json.loads(response.data)['payload']
        sent_listening_activity = payload['listening_activity']
        received_listening_activity = data['listening_activity']
        self.assertListEqual(sent_listening_activity, received_listening_activity)
        self.assertEqual(data['range'], 'year')
        self.assertEqual(data['user_id'], self.user['musicbrainz_id'])

    def test_listening_activity_stat_invalid_user(self):
        """ Test to make sure that the API sends 404 if user does not exist. """
        response = self.client.get(url_for('stats_api_v1.get_listening_activity', user_name='nouser'))
        self.assert404(response)
        self.assertEqual('Cannot find user: nouser', response.json['error'])

    def test_listening_activity_stat_not_calculated(self):
        """ Test to make sure that the API sends 204 if statistics for user have not been calculated yet """
        db_stats.delete_user_stats(self.user['id'])
        response = self.client.get(url_for('stats_api_v1.get_listening_activity', user_name=self.user['musicbrainz_id']))
        self.assertEqual(response.status_code, 204)

    def test_listening_activity_range_stat_not_calculated(self):
        """ Test to make sure that the API sends 204 if particular range statistics for user have not been calculated yet """
        response = self.client.get(url_for('stats_api_v1.get_listening_activity',
                                           user_name=self.user['musicbrainz_id']), query_string={'range': 'year'})
        self.assertEqual(response.status_code, 204)

    def test_listening_activity_stat_invalid_range(self):
        """ Test to make sure 400 is received if range argument is invalid """
        response = self.client.get(url_for('stats_api_v1.get_listening_activity',
                                           user_name=self.user['musicbrainz_id']), query_string={'range': 'foobar'})
        self.assert400(response)
        self.assertEqual("Invalid range: foobar", response.json['error'])

    def test_daily_activity_stat(self):
        """ Test to make sure valid response is received """
        response = self.client.get(url_for('stats_api_v1.get_daily_activity', user_name=self.user['musicbrainz_id']))
        self.assert200(response)

        with open(self.path_to_data_file('user_daily_activity_api_output.json')) as f:
            expected = json.load(f)["payload"]

        received = json.loads(response.data)["payload"]
        self.assertDictEqual(expected["daily_activity"], received["daily_activity"])

    def test_daily_activity_stat_all_time(self):
        """ Test to make sure valid response is received when range is 'all_time' """
        response = self.client.get(url_for('stats_api_v1.get_daily_activity',
                                           user_name=self.user['musicbrainz_id']), query_string={'range': 'all_time'})
        self.assert200(response)

        with open(self.path_to_data_file('user_daily_activity_api_output.json')) as f:
            expected = json.load(f)["payload"]

        received = json.loads(response.data)["payload"]
        self.assertDictEqual(expected["daily_activity"], received["daily_activity"])
        self.assertEqual(received["range"], "all_time")

    def test_daily_activity_stat_week(self):
        """ Test to make sure valid response is received when range is 'week' """
        with open(self.path_to_data_file('user_daily_activity_db_data_for_api_test_week.json'), 'r') as f:
            payload = json.load(f)

        db_stats.insert_user_daily_activity(self.user['id'], UserDailyActivityStatJson(**{'week': payload}))

        response = self.client.get(url_for('stats_api_v1.get_daily_activity',
                                           user_name=self.user['musicbrainz_id']), query_string={'range': 'week'})
        self.assert200(response)

        with open(self.path_to_data_file('user_daily_activity_api_output_week.json')) as f:
            expected = json.load(f)["payload"]

        received = json.loads(response.data)["payload"]
        self.assertDictEqual(expected["daily_activity"], received["daily_activity"])
        self.assertEqual(received["range"], "week")

    def test_daily_activity_stat_month(self):
        """ Test to make sure valid response is received when range is 'month' """
        with open(self.path_to_data_file('user_daily_activity_db_data_for_api_test_month.json'), 'r') as f:
            payload = json.load(f)

        db_stats.insert_user_daily_activity(self.user['id'], UserDailyActivityStatJson(**{'month': payload}))

        response = self.client.get(url_for('stats_api_v1.get_daily_activity',
                                           user_name=self.user['musicbrainz_id']), query_string={'range': 'month'})
        self.assert200(response)

        with open(self.path_to_data_file('user_daily_activity_api_output_month.json')) as f:
            expected = json.load(f)["payload"]

        received = json.loads(response.data)["payload"]
        self.assertDictEqual(expected["daily_activity"], received["daily_activity"])
        self.assertEqual(received["range"], "month")

    def test_daily_activity_stat_year(self):
        """ Test to make sure valid response is received when range is 'year' """
        with open(self.path_to_data_file('user_daily_activity_db_data_for_api_test_year.json'), 'r') as f:
            payload = json.load(f)

        db_stats.insert_user_daily_activity(self.user['id'], UserDailyActivityStatJson(**{'year': payload}))

        response = self.client.get(url_for('stats_api_v1.get_daily_activity',
                                           user_name=self.user['musicbrainz_id']), query_string={'range': 'year'})
        self.assert200(response)

        with open(self.path_to_data_file('user_daily_activity_api_output_year.json')) as f:
            expected = json.load(f)["payload"]

        received = json.loads(response.data)["payload"]
        self.assertDictEqual(expected["daily_activity"], received["daily_activity"])
        self.assertEqual(received["range"], "year")

    def test_daily_activity_stat_invalid_user(self):
        """ Test to make sure that the API sends 404 if user does not exist. """
        response = self.client.get(url_for('stats_api_v1.get_daily_activity', user_name='nouser'))
        self.assert404(response)
        self.assertEqual('Cannot find user: nouser', response.json['error'])

    def test_daily_activity_stat_not_calculated(self):
        """ Test to make sure that the API sends 204 if statistics for user have not been calculated yet """
        db_stats.delete_user_stats(self.user['id'])
        response = self.client.get(url_for('stats_api_v1.get_daily_activity', user_name=self.user['musicbrainz_id']))
        self.assertEqual(response.status_code, 204)

    def test_daily_activity_range_stat_not_calculated(self):
        """ Test to make sure that the API sends 204 if particular range statistics for user have not been calculated yet """
        response = self.client.get(url_for('stats_api_v1.get_daily_activity',
                                           user_name=self.user['musicbrainz_id']), query_string={'range': 'year'})
        self.assertEqual(response.status_code, 204)

    def test_daily_activity_stat_invalid_range(self):
        """ Test to make sure 400 is received if range argument is invalid """
        response = self.client.get(url_for('stats_api_v1.get_daily_activity',
                                           user_name=self.user['musicbrainz_id']), query_string={'range': 'foobar'})
        self.assert400(response)
        self.assertEqual("Invalid range: foobar", response.json['error'])

    @patch('listenbrainz.webserver.views.stats_api.datetime', MockDate)
    def test_artist_map_all_time_cached(self):
        """ Test to make sure the endpoint returns correct cached response """
        response = self.client.get(url_for('stats_api_v1.get_artist_map',
                                           user_name=self.user['musicbrainz_id']), query_string={'range': 'all_time'})
        self.assert200(response)
        data = json.loads(response.data)['payload']
        sent_artist_map = self.artist_map_payload['artist_map']
        received_artist_map = data['artist_map']
        self.assertListEqual(sent_artist_map, received_artist_map)
        self.assertEqual(data['range'], 'all_time')
        self.assertEqual(data['user_id'], self.user['musicbrainz_id'])

    @patch('listenbrainz.webserver.views.stats_api.datetime', MockDate)
    def test_artist_map_week_cached(self):
        """ Test to make sure the endpoint returns correct cached response """
        with open(self.path_to_data_file('user_artist_map_db_data_for_api_test_week.json'), 'r') as f:
            payload = json.load(f)

        db_stats.insert_user_artist_map(self.user['id'], UserArtistMapStatJson(**{'week': payload}))
        response = self.client.get(url_for('stats_api_v1.get_artist_map',
                                           user_name=self.user['musicbrainz_id']), query_string={'range': 'week'})
        self.assert200(response)
        data = json.loads(response.data)['payload']
        sent_artist_map = payload['artist_map']
        received_artist_map = data['artist_map']
        self.assertListEqual(sent_artist_map, received_artist_map)
        self.assertEqual(data['range'], 'week')
        self.assertEqual(data['user_id'], self.user['musicbrainz_id'])

    @patch('listenbrainz.webserver.views.stats_api.datetime', MockDate)
    def test_artist_map_month_cached(self):
        """ Test to make sure the endpoint returns correct cached response """
        with open(self.path_to_data_file('user_artist_map_db_data_for_api_test_month.json'), 'r') as f:
            payload = json.load(f)

        db_stats.insert_user_artist_map(self.user['id'], UserArtistMapStatJson(**{'month': payload}))
        response = self.client.get(url_for('stats_api_v1.get_artist_map',
                                           user_name=self.user['musicbrainz_id']), query_string={'range': 'month'})
        self.assert200(response)
        data = json.loads(response.data)['payload']
        sent_artist_map = payload['artist_map']
        received_artist_map = data['artist_map']
        self.assertListEqual(sent_artist_map, received_artist_map)
        self.assertEqual(data['range'], 'month')
        self.assertEqual(data['user_id'], self.user['musicbrainz_id'])

    @patch('listenbrainz.webserver.views.stats_api.datetime', MockDate)
    def test_artist_map_year_cached(self):
        """ Test to make sure the endpoint returns correct cached response """
        with open(self.path_to_data_file('user_artist_map_db_data_for_api_test_year.json'), 'r') as f:
            payload = json.load(f)

        db_stats.insert_user_artist_map(self.user['id'], UserArtistMapStatJson(**{'year': payload}))
        response = self.client.get(url_for('stats_api_v1.get_artist_map',
                                           user_name=self.user['musicbrainz_id']), query_string={'range': 'year'})
        self.assert200(response)
        data = json.loads(response.data)['payload']
        sent_artist_map = payload['artist_map']
        received_artist_map = data['artist_map']
        self.assertListEqual(sent_artist_map, received_artist_map)
        self.assertEqual(data['range'], 'year')
        self.assertEqual(data['user_id'], self.user['musicbrainz_id'])

    @patch('listenbrainz.webserver.views.stats_api._get_country_codes')
    def test_artist_map_not_calculated(self, mock_get_country_codes):
        """ Test to make sure stats are calculated if not present in DB """
        mock_get_country_codes.return_value = [UserArtistMapRecord(
            **country) for country in self.artist_map_payload["artist_map"]]

        # Delete stats
        db_stats.delete_user_stats(user_id=self.user['id'])
        # Reinsert artist stats
        db_stats.insert_user_artists(self.user['id'], UserArtistStatJson(**{'all_time': self.artist_payload}))

        response = self.client.get(url_for('stats_api_v1.get_artist_map',
                                           user_name=self.user['musicbrainz_id']), query_string={'range': 'all_time'})
        self.assert200(response)
        data = json.loads(response.data)['payload']
        sent_artist_map = self.artist_map_payload['artist_map']
        received_artist_map = data['artist_map']
        self.assertListEqual(sent_artist_map, received_artist_map)
        self.assertEqual(data['user_id'], self.user['musicbrainz_id'])
        self.assertGreater(data['last_updated'], 0)
        mock_get_country_codes.assert_called_once()

        # Check if stats have been saved in DB
        data = db_stats.get_user_artist_map(self.user['id'], 'all_time')
        self.assertEqual(data.all_time.dict()['artist_map'], sent_artist_map)

    def test_artist_map_not_calculated_artist_stat_not_present(self):
        """ Test to make sure that if artist stats and artist_map stats both are missing from DB, we return 204 """

        # Delete stats
        db_stats.delete_user_stats(user_id=self.user['id'])

        response = self.client.get(url_for('stats_api_v1.get_artist_map',
                                           user_name=self.user['musicbrainz_id']), query_string={'range': 'all_time'})
        self.assertEqual(response.status_code, 204)

    def test_artist_map_stat_invalid_user(self):
        """ Test to make sure that the API sends 404 if user does not exist. """
        response = self.client.get(url_for('stats_api_v1.get_artist_map', user_name='nouser'))
        self.assert404(response)
        self.assertEqual('Cannot find user: nouser', response.json['error'])

    def test_artist_map_stat_invalid_range(self):
        """ Test to make sure 400 is received if range argument is invalid """
        response = self.client.get(url_for('stats_api_v1.get_artist_map',
                                           user_name=self.user['musicbrainz_id']), query_string={'range': 'foobar'})
        self.assert400(response)
        self.assertEqual("Invalid range: foobar", response.json['error'])

    def test_artist_map_stat_invalid_force_recalculate(self):
        """ Test to make sure 400 is received if force_recalculate argument is invalid """
        response = self.client.get(url_for('stats_api_v1.get_artist_map',
                                           user_name=self.user['musicbrainz_id']), query_string={'force_recalculate': 'foobar'})
        self.assert400(response)
        self.assertEqual("Invalid value of force_recalculate: foobar", response.json['error'])

    @requests_mock.Mocker()
    def test_get_country_code(self, mock_requests):
        """ Test to check if "_get_country_codes" is working correctly """
        # Mock fetching mapping from "bono"
        with open(self.path_to_data_file("msid_mbid_mapping_result.json")) as f:
            msid_mbid_mapping_result = json.load(f)
        mock_requests.post("http://bono.metabrainz.org:8000/artist-msid-lookup/json", json=msid_mbid_mapping_result)

        # Mock fetching country data from labs.api.listenbrainz.org
        with open(self.path_to_data_file("mbid_country_mapping_result.json")) as f:
            mbid_country_mapping_result = json.load(f)
        mock_requests.post("https://labs.api.listenbrainz.org/artist-country-code-from-artist-mbid/json",
                           json=mbid_country_mapping_result)

        received = [entry.dict() for entry in _get_country_codes(['a', 'b'], ['c', 'd'])]
        expected = [
            {
                "country": "GBR",
                "artist_count": 4
            }
        ]
        self.assertListEqual(expected, received)

    @requests_mock.Mocker()
    def test_get_country_code_msid_mbid_mapping_failure(self, mock_requests):
        """ Test to check if appropriate message is returned if fetching msid_mbid_mapping fails """
        # Mock fetching mapping from "bono"
        mock_requests.post("http://bono.metabrainz.org:8000/artist-msid-lookup/json", status_code=500)

        # Mock fetching country data from labs.api.listenbrainz.org
        with open(self.path_to_data_file("mbid_country_mapping_result.json")) as f:
            mbid_country_mapping_result = json.load(f)
        mock_requests.post("https://labs.api.listenbrainz.org/artist-country-code-from-artist-mbid/json",
                           json=mbid_country_mapping_result)

        response = self.client.get(url_for('stats_api_v1.get_artist_map',
                                           user_name=self.user['musicbrainz_id']), query_string={'range': 'all_time',
                                                                                                 'force_recalculate': 'true'})
        error_msg = ("An error occurred while calculating artist_map data, "
                     "try setting 'force_recalculate' to 'false' to get a cached copy if available")
        self.assert500(response, message=error_msg)
