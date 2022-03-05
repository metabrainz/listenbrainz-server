import json
from copy import deepcopy
from datetime import datetime
from unittest.mock import patch

import listenbrainz.db.stats as db_stats
import listenbrainz.db.user as db_user
import requests_mock

from data.model.common_stat import StatRange
from data.model.user_artist_map import UserArtistMapRecord
from flask import url_for

from data.model.user_daily_activity import DailyActivityRecord
from data.model.user_entity import EntityRecord
from data.model.user_listening_activity import ListeningActivityRecord
from listenbrainz.config import LISTENBRAINZ_LABS_API_URL
from listenbrainz.tests.integration import IntegrationTestCase
from redis import Redis
from flask import current_app


class MockDate(datetime):
    """ Mock class for datetime which returns epoch """
    @classmethod
    def now(cls, tzinfo=None):
        return cls.fromtimestamp(0, tzinfo)


test_entity_params = [
    ("stats_api_v1.get_user_artist", "artists", "total_artist_count"),
    ("stats_api_v1.get_release", "releases", "total_release_count"),
    ("stats_api_v1.get_recording", "recordings", "total_recording_count")
]

test_sitewide_entity_params = [
    ("stats_api_v1.get_sitewide_artist", "artists"),
]


class StatsAPITestCase(IntegrationTestCase):

    def setUp(self):
        super(StatsAPITestCase, self).setUp()
        self.user = db_user.get_or_create(1, 'testuserpleaseignore')
        self.create_user_with_id(db_stats.SITEWIDE_STATS_USER_ID, 2, "listenbrainz-stats-user")

        # Insert user top artists
        with open(self.path_to_data_file('user_top_artists_db_data_for_api_test.json'), 'r') as f:
            self.user_artist_payload = json.load(f)
        db_stats.insert_user_jsonb_data(self.user['id'], 'artists',
                                        StatRange[EntityRecord](**self.user_artist_payload))

        # Insert release data
        with open(self.path_to_data_file('user_top_releases_db_data_for_api_test.json'), 'r') as f:
            self.user_release_payload = json.load(f)
        db_stats.insert_user_jsonb_data(self.user['id'], 'releases',
                                        StatRange[EntityRecord](**self.user_release_payload))

        # Insert recording data
        with open(self.path_to_data_file('user_top_recordings_db_data_for_api_test.json'), 'r') as f:
            self.recording_payload = json.load(f)
        db_stats.insert_user_jsonb_data(self.user['id'], 'recordings',
                                        StatRange[EntityRecord](**self.recording_payload))

        # Insert listening activity data
        with open(self.path_to_data_file('user_listening_activity_db_data_for_api_test.json')) as f:
            self.listening_activity_payload = json.load(f)
        db_stats.insert_user_jsonb_data(self.user['id'], 'listening_activity',
                                        StatRange[ListeningActivityRecord](**self.listening_activity_payload))

        # Insert daily activity data
        with open(self.path_to_data_file('user_daily_activity_db_data_for_api_test.json')) as f:
            data = json.load(f)
        db_stats.insert_user_jsonb_data(self.user['id'], 'daily_activity',
                                        StatRange[DailyActivityRecord](**data))

        # Insert artist map data
        with open(self.path_to_data_file('user_artist_map_db_data_for_api_test.json')) as f:
            self.artist_map_payload = json.load(f)
        db_stats.insert_user_jsonb_data(self.user['id'], 'artist_map',
                                        StatRange[UserArtistMapRecord](**self.artist_map_payload))

        # Insert all_time sitewide top artists
        with open(self.path_to_data_file('sitewide_top_artists_db_data_for_api_test.json'), 'r') as f:
            self.sitewide_artist_payload = json.load(f)
        db_stats.insert_sitewide_jsonb_data('artists', StatRange[EntityRecord](**self.sitewide_artist_payload))

    def tearDown(self):
        r = Redis(host=current_app.config['REDIS_HOST'], port=current_app.config['REDIS_PORT'])
        r.flushall()
        super(StatsAPITestCase, self).tearDown()

    def assertUserStatEqual(self, sent, response, entity, total_count_key, count, offset=0):
        """ Checks the stats response received from the api is valid and then compare the stats payload inserted in db
            with the payload received from the api.

            Many tests insert larger payloads but expect a smaller number of stats to returned so
            this method also accepts a count and offset parameter denoting how many stats and which
            entries to check.
        """
        self.assert200(response)
        received = json.loads(response.data)['payload']
        self.assertEqual(self.user['musicbrainz_id'], received['user_id'])
        self.assertEqual(count, received['count'])
        self.assertEqual(sent['count'], received[total_count_key])
        self.assertEqual(sent['from_ts'], received['from_ts'])
        self.assertEqual(sent['to_ts'], received['to_ts'])
        self.assertEqual(sent['stats_range'], received['range'])
        self.assertListEqual(sent['data'][offset:count + offset], received[entity])

    def test_user_stat_invalid_offset(self):
        """ Test to make sure 400 response is received if offset argument is not a positive integer """
        for (api_name, _, _) in test_entity_params:
            for offset in ["foobar", -5]:
                with self.subTest(api_name=api_name, offset=offset):
                    response = self.client.get(
                        url_for(api_name, user_name=self.user['musicbrainz_id']),
                        query_string={'offset': offset}
                    )
                    self.assert400(response)
                    self.assertEqual("'offset' should be a non-negative integer", response.json['error'])

    def test_user_stat_invalid_count(self):
        """ Test to make sure 400 response is received if count argument is not a positive integer"""
        for (api_name, _, _) in test_entity_params:
            for count in ["foobar", -5]:
                with self.subTest(api_name=api_name, count=count):
                    response = self.client.get(
                        url_for(api_name, user_name=self.user['musicbrainz_id']),
                        query_string={'count': count}
                    )
                    self.assert400(response)
                    self.assertEqual("'count' should be a non-negative integer", response.json['error'])

    def test_user_stat(self):
        """ Test to make sure valid response is received """
        for (api_name, entity, total_count_key) in test_entity_params:
            with self.subTest(api_name=api_name, entity=entity, total_count_key=total_count_key):

                with open(self.path_to_data_file(f"user_top_{entity}_db_data_for_api_test.json"), "r") as f:
                    user_stat_payload = json.load(f)
                db_stats.insert_user_jsonb_data(self.user['id'], entity, StatRange[EntityRecord](**user_stat_payload))

                response = self.client.get(url_for(api_name, user_name=self.user['musicbrainz_id']))
                self.assertUserStatEqual(user_stat_payload, response, entity, total_count_key, 25)

    def test_user_stat_too_many(self):
        """ Test to make sure response received has maximum 100 stats """
        for (api_name, entity, total_count_key) in test_entity_params:
            with self.subTest(api_name=api_name, entity=entity, total_count_key=total_count_key):

                with open(self.path_to_data_file(f'user_top_{entity}_db_data_for_api_test_too_many.json'), 'r') as f:
                    user_stat_payload = json.load(f)
                db_stats.insert_user_jsonb_data(self.user['id'], entity, StatRange[EntityRecord](**user_stat_payload))

                response = self.client.get(
                    url_for(api_name, user_name=self.user['musicbrainz_id']),
                    query_string={'count': 105}
                )
                self.assertUserStatEqual(user_stat_payload, response, entity, total_count_key, 100)

    def test_user_stat_ranges(self):
        """ Test to make sure valid response is received when using stat_range other than all_time """
        for (api_name, entity, total_count_key) in test_entity_params:
            for stat_range in ["week", "month", "year"]:
                with self.subTest(api_name=api_name, entity=entity, total_count_key=total_count_key,
                                  stat_range=stat_range):
                    with open(self.path_to_data_file(f'user_top_{entity}_db_data_for_api_test_{stat_range}.json'), 'r') as f:
                        payload = json.load(f)
                    db_stats.insert_user_jsonb_data(self.user['id'], entity, StatRange[EntityRecord](**payload))

                    response = self.client.get(
                        url_for(api_name, user_name=self.user['musicbrainz_id']),
                        query_string={'range': stat_range}
                    )
                    self.assertUserStatEqual(payload, response, entity, total_count_key, 25)

    def test_user_stat_all_time(self):
        """ Test to make sure valid response is received when using stat_range is all_time """
        for (api_name, entity, total_count_key) in test_entity_params:
            with self.subTest(api_name=api_name, entity=entity, total_count_key=total_count_key):
                with open(self.path_to_data_file(f"user_top_{entity}_db_data_for_api_test.json"), "r") as f:
                    user_stat_payload = json.load(f)
                db_stats.insert_user_jsonb_data(self.user['id'], entity, StatRange[EntityRecord](**user_stat_payload))

                response = self.client.get(
                    url_for(api_name, user_name=self.user['musicbrainz_id']),
                    query_string={'range': 'all_time'}
                )
                self.assertUserStatEqual(user_stat_payload, response, entity, total_count_key, 25)

    def test_user_stat_invalid_range(self):
        """ Test to make sure 400 is received if range argument is invalid """
        for (api_name, _, _) in test_entity_params:
            with self.subTest(api_name=api_name):
                response = self.client.get(
                    url_for(api_name, user_name=self.user['musicbrainz_id']),
                    query_string={'range': 'foobar'}
                )
                self.assert400(response)
                self.assertEqual("Invalid range: foobar", response.json['error'])

    def test_user_stat_count(self):
        """ Test to make sure valid response is received if count argument is passed """
        for (api_name, entity, total_count_key) in test_entity_params:
            with self.subTest(api_name=api_name):
                with open(self.path_to_data_file(f'user_top_{entity}_db_data_for_api_test.json'), 'r') as f:
                    payload = json.load(f)
                db_stats.insert_user_jsonb_data(self.user['id'], entity, StatRange[EntityRecord](**payload))

                response = self.client.get(
                    url_for(api_name, user_name=self.user['musicbrainz_id']),
                    query_string={'count': 5}
                )
                self.assertUserStatEqual(payload, response, entity, total_count_key, 5)

    def test_user_stat_offset(self):
        """ Test to make sure valid response is received if offset argument is passed """
        for (api_name, entity, total_count_key) in test_entity_params:
            with self.subTest(api_name=api_name):
                with open(self.path_to_data_file(f'user_top_{entity}_db_data_for_api_test.json'), 'r') as f:
                    payload = json.load(f)
                db_stats.insert_user_jsonb_data(self.user['id'], entity, StatRange[EntityRecord](**payload))

                response = self.client.get(
                    url_for(api_name, user_name=self.user['musicbrainz_id']),
                    query_string={'offset': 5}
                )
                self.assertUserStatEqual(payload, response, entity, total_count_key, 25, 5)

    def test_user_stat_invalid_user(self):
        """ Test to make sure that the API sends 404 if user does not exist. """
        for (api_name, _, _) in test_entity_params:
            with self.subTest(api_name=api_name):
                response = self.client.get(
                    url_for(api_name, user_name='nouser'),
                    query_string={'range': 'foobar'}
                )
                self.assert404(response)
                self.assertEqual('Cannot find user: nouser', response.json['error'])

    def test_user_stat_not_calculated(self):
        """ Test to make sure that the API sends 204 if statistics for user have not been calculated yet """
        for (api_name, _, _) in test_entity_params:
            with self.subTest(api_name=api_name):
                db_stats.delete_user_stats(self.user['id'])
                response = self.client.get(url_for(api_name, user_name=self.user['musicbrainz_id']))
                self.assertEqual(response.status_code, 204)

    def test_user_range_stat_not_calculated(self):
        """ Test to make sure that the API sends 204 if particular range statistics for user have not been calculated yet """
        for (api_name, _, _) in test_entity_params:
            with self.subTest(api_name=api_name):
                response = self.client.get(
                    url_for(api_name, user_name=self.user['musicbrainz_id']),
                    query_string={'range': 'year'}
                )
                self.assertEqual(response.status_code, 204)

    def test_entity_stat_not_calculated(self):
        """ Test to make sure that the API sends 204 if particular entity
            statistics for user have not been calculated yet
        """
        # Make sure release stats are calculated, but artist stats are not
        db_stats.delete_user_stats(self.user['id'])
        with open(self.path_to_data_file('user_top_releases_db_data_for_api_test.json'), 'r') as f:
            payload = json.load(f)
        db_stats.insert_user_jsonb_data(self.user['id'], 'releases', StatRange[EntityRecord](**payload))

        response = self.client.get(url_for('stats_api_v1.get_user_artist',
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
        db_stats.insert_user_jsonb_data(self.user['id'], 'releases', StatRange[EntityRecord](**payload))

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
        sent_listening_activity = self.listening_activity_payload['data']
        received_listening_activity = data['listening_activity']
        self.assertListEqual(sent_listening_activity, received_listening_activity)
        self.assertEqual(data['user_id'], self.user['musicbrainz_id'])

    def test_listening_activity_stat_all_time(self):
        """ Test to make sure valid response is received when range is 'all_time' """
        response = self.client.get(url_for('stats_api_v1.get_listening_activity',
                                           user_name=self.user['musicbrainz_id']), query_string={'range': 'all_time'})
        self.assert200(response)
        data = json.loads(response.data)['payload']
        sent_listening_activity = self.listening_activity_payload['data']
        received_listening_activity = data['listening_activity']
        self.assertListEqual(sent_listening_activity, received_listening_activity)
        self.assertEqual(data['range'], 'all_time')
        self.assertEqual(data['user_id'], self.user['musicbrainz_id'])

    def test_listening_activity_stat_week(self):
        """ Test to make sure valid response is received when range is 'week' """
        with open(self.path_to_data_file('user_listening_activity_db_data_for_api_test_week.json'), 'r') as f:
            payload = json.load(f)

        db_stats.insert_user_jsonb_data(self.user['id'], 'listening_activity',
                                        StatRange[ListeningActivityRecord](**payload))

        response = self.client.get(url_for('stats_api_v1.get_listening_activity',
                                           user_name=self.user['musicbrainz_id']), query_string={'range': 'week'})
        self.assert200(response)
        data = json.loads(response.data)['payload']
        sent_listening_activity = payload['data']
        received_listening_activity = data['listening_activity']
        self.assertListEqual(sent_listening_activity, received_listening_activity)
        self.assertEqual(data['range'], 'week')
        self.assertEqual(data['user_id'], self.user['musicbrainz_id'])

    def test_listening_activity_stat_month(self):
        """ Test to make sure valid response is received when range is 'month' """
        with open(self.path_to_data_file('user_listening_activity_db_data_for_api_test_month.json'), 'r') as f:
            payload = json.load(f)

        db_stats.insert_user_jsonb_data(self.user['id'], 'listening_activity',
                                        StatRange[ListeningActivityRecord](**payload))

        response = self.client.get(url_for('stats_api_v1.get_listening_activity',
                                           user_name=self.user['musicbrainz_id']), query_string={'range': 'month'})
        self.assert200(response)
        data = json.loads(response.data)['payload']
        sent_listening_activity = payload['data']
        received_listening_activity = data['listening_activity']
        self.assertListEqual(sent_listening_activity, received_listening_activity)
        self.assertEqual(data['range'], 'month')
        self.assertEqual(data['user_id'], self.user['musicbrainz_id'])

    def test_listening_activity_stat_year(self):
        """ Test to make sure valid response is received when range is 'year' """
        with open(self.path_to_data_file('user_listening_activity_db_data_for_api_test_year.json'), 'r') as f:
            payload = json.load(f)

        db_stats.insert_user_jsonb_data(self.user['id'], 'listening_activity',
                                        StatRange[ListeningActivityRecord](**payload))

        response = self.client.get(url_for('stats_api_v1.get_listening_activity',
                                           user_name=self.user['musicbrainz_id']), query_string={'range': 'year'})
        self.assert200(response)
        data = json.loads(response.data)['payload']
        sent_listening_activity = payload['data']
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

        db_stats.insert_user_jsonb_data(self.user['id'], 'daily_activity',
                                        StatRange[DailyActivityRecord](**payload))

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

        db_stats.insert_user_jsonb_data(self.user['id'], 'daily_activity',
                                        StatRange[DailyActivityRecord](**payload))

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

        db_stats.insert_user_jsonb_data(self.user['id'], 'daily_activity',
                                        StatRange[DailyActivityRecord](**payload))

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
        sent_artist_map = self.artist_map_payload['data']
        received_artist_map = data['artist_map']
        self.assertListEqual(sent_artist_map, received_artist_map)
        self.assertEqual(data['range'], 'all_time')
        self.assertEqual(data['user_id'], self.user['musicbrainz_id'])

    @patch('listenbrainz.webserver.views.stats_api.datetime', MockDate)
    def test_artist_map_week_cached(self):
        """ Test to make sure the endpoint returns correct cached response """
        with open(self.path_to_data_file('user_artist_map_db_data_for_api_test_week.json'), 'r') as f:
            payload = json.load(f)

        db_stats.insert_user_jsonb_data(self.user['id'], 'artist_map', StatRange[UserArtistMapRecord](**payload))
        response = self.client.get(url_for('stats_api_v1.get_artist_map',
                                           user_name=self.user['musicbrainz_id']), query_string={'range': 'week'})
        self.assert200(response)
        data = json.loads(response.data)['payload']
        sent_artist_map = payload['data']
        received_artist_map = data['artist_map']
        self.assertListEqual(sent_artist_map, received_artist_map)
        self.assertEqual(data['range'], 'week')
        self.assertEqual(data['user_id'], self.user['musicbrainz_id'])

    @patch('listenbrainz.webserver.views.stats_api.datetime', MockDate)
    def test_artist_map_month_cached(self):
        """ Test to make sure the endpoint returns correct cached response """
        with open(self.path_to_data_file('user_artist_map_db_data_for_api_test_month.json'), 'r') as f:
            payload = json.load(f)

        db_stats.insert_user_jsonb_data(self.user['id'], 'artist_map', StatRange[UserArtistMapRecord](**payload))
        response = self.client.get(url_for('stats_api_v1.get_artist_map',
                                           user_name=self.user['musicbrainz_id']), query_string={'range': 'month'})
        self.assert200(response)
        data = json.loads(response.data)['payload']
        sent_artist_map = payload['data']
        received_artist_map = data['artist_map']
        self.assertListEqual(sent_artist_map, received_artist_map)
        self.assertEqual(data['range'], 'month')
        self.assertEqual(data['user_id'], self.user['musicbrainz_id'])

    @patch('listenbrainz.webserver.views.stats_api.datetime', MockDate)
    def test_artist_map_year_cached(self):
        """ Test to make sure the endpoint returns correct cached response """
        with open(self.path_to_data_file('user_artist_map_db_data_for_api_test_year.json'), 'r') as f:
            payload = json.load(f)

        db_stats.insert_user_jsonb_data(self.user['id'], 'artist_map', StatRange[UserArtistMapRecord](**payload))
        response = self.client.get(url_for('stats_api_v1.get_artist_map',
                                           user_name=self.user['musicbrainz_id']), query_string={'range': 'year'})
        self.assert200(response)
        data = json.loads(response.data)['payload']
        sent_artist_map = payload['data']
        received_artist_map = data['artist_map']
        self.assertListEqual(sent_artist_map, received_artist_map)
        self.assertEqual(data['range'], 'year')
        self.assertEqual(data['user_id'], self.user['musicbrainz_id'])

    @patch('listenbrainz.webserver.views.stats_api._get_country_wise_counts')
    def test_artist_map_not_calculated(self, mock_get_country_wise_counts):
        """ Test to make sure stats are calculated if not present in DB """
        mock_get_country_wise_counts.return_value = [UserArtistMapRecord(
            **country) for country in self.artist_map_payload['data']]

        # Delete stats
        db_stats.delete_user_stats(user_id=self.user['id'])
        # Reinsert artist stats
        db_stats.insert_user_jsonb_data(self.user['id'], 'artists',
                                        StatRange[EntityRecord](**self.user_artist_payload))

        response = self.client.get(url_for('stats_api_v1.get_artist_map',
                                           user_name=self.user['musicbrainz_id']), query_string={'range': 'all_time'})
        self.assert200(response)
        data = json.loads(response.data)['payload']
        sent_artist_map = self.artist_map_payload['data']
        received_artist_map = data['artist_map']
        self.assertListEqual(sent_artist_map, received_artist_map)
        self.assertEqual(data['user_id'], self.user['musicbrainz_id'])
        self.assertGreater(data['last_updated'], 0)
        mock_get_country_wise_counts.assert_called_once()

        # Check if stats have been saved in DB
        data = db_stats.get_user_artist_map(self.user['id'], 'all_time')
        self.assertEqual(data.data.dict()['__root__'], sent_artist_map)

    @patch('listenbrainz.webserver.views.stats_api.db_stats.insert_user_jsonb_data', side_effect=NotImplementedError)
    @patch('listenbrainz.webserver.views.stats_api._get_country_wise_counts')
    def test_artist_map_db_insertion_failed(self, mock_get_country_wise_counts, mock_db_insert):
        """ Test to make sure that stats are calculated returned even if DB insertion fails """
        mock_get_country_wise_counts.return_value = [UserArtistMapRecord(
            **country) for country in self.artist_map_payload['data']]

        response = self.client.get(url_for('stats_api_v1.get_artist_map',
                                           user_name=self.user['musicbrainz_id']),
                                   query_string={'range': 'all_time', 'force_recalculate': 'true'})
        self.assert200(response)
        data = json.loads(response.data)['payload']
        sent_artist_map = self.artist_map_payload['data']
        received_artist_map = data['artist_map']
        self.assertListEqual(sent_artist_map, received_artist_map)
        self.assertEqual(data['user_id'], self.user['musicbrainz_id'])
        self.assertGreater(data['last_updated'], 0)
        mock_get_country_wise_counts.assert_called_once()

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
        """ Test to check if "_get_country_wise_counts" is working correctly """
        # Mock fetching country data from labs.api.listenbrainz.org
        with open(self.path_to_data_file("mbid_country_mapping_result.json")) as f:
            mbid_country_mapping_result = json.load(f)
        mock_requests.post("{}/artist-country-code-from-artist-mbid/json".format(LISTENBRAINZ_LABS_API_URL),
                           json=mbid_country_mapping_result)

        response = self.client.get(url_for('stats_api_v1.get_artist_map',
                                           user_name=self.user['musicbrainz_id']), query_string={'range': 'all_time',
                                                                                                 'force_recalculate': 'true'})
        data = response.json["payload"]
        received = data["artist_map"]
        expected = [
            {
                "country": "GBR",
                'artists': [
                    {
                        'artist_mbid': 'cc197bad-dc9c-440d-a5b5-d52ba2e14234',
                        'artist_name': 'Coldplay',
                        'listen_count': 321
                    }
                ],
                "artist_count": 1,
                "listen_count": 321,
            }
        ]
        self.assertListEqual(expected, received)
        self.assertTrue('count' in mock_requests.request_history[0].qs)

    @requests_mock.Mocker()
    def test_get_country_code_mbid_country_mapping_failure(self, mock_requests):
        """ Test to check if appropriate message is returned if fetching msid_mbid_mapping fails """
        # Mock fetching mapping from "bono"
        with open(self.path_to_data_file("msid_mbid_mapping_result.json")) as f:
            msid_mbid_mapping_result = json.load(f)
        mock_requests.post("{}/artist-credit-from-artist-msid/json".format(LISTENBRAINZ_LABS_API_URL),
                           json=msid_mbid_mapping_result)

        # Mock fetching country data from labs.api.listenbrainz.org
        mock_requests.post("{}/artist-country-code-from-artist-mbid/json".format(LISTENBRAINZ_LABS_API_URL),
                           status_code=500)

        response = self.client.get(url_for('stats_api_v1.get_artist_map',
                                           user_name=self.user['musicbrainz_id']), query_string={'range': 'all_time',
                                                                                                 'force_recalculate': 'true'})
        error_msg = ("An error occurred while calculating artist_map data, "
                     "try setting 'force_recalculate' to 'false' to get a cached copy if available")
        self.assert500(response, message=error_msg)

    def test_get_country_code_no_msids_and_mbids(self):
        """ Test to check if no error is thrown if no msids and mbids are present"""

        # Overwrite the artist stats so that no artist has msids or mbids present
        artist_stats = deepcopy(self.user_artist_payload)
        for artist in artist_stats["data"]:
            artist['artist_mbids'] = []
            artist['artist_msid'] = None
        db_stats.insert_user_jsonb_data(self.user['id'], 'artists',
                                        StatRange[EntityRecord](**artist_stats))
        response = self.client.get(url_for('stats_api_v1.get_artist_map',
                                           user_name=self.user['musicbrainz_id']), query_string={'range': 'all_time',
                                                                                                 'force_recalculate': 'true'})
        self.assert200(response)
        self.assertListEqual([], json.loads(response.data)['payload']['artist_map'])

    def assertSitewideStatEqual(self, sent, response, entity, total_count, count, offset=0):
        """ Checks the stats response received from the api is valid and then compare the stats payload inserted in db
            with the payload received from the api.

            Many tests insert larger payloads but expect a smaller number of stats to returned so
            this method also accepts a count and offset parameter denoting how many stats and which
            entries to check.
        """
        self.assert200(response)
        received = json.loads(response.data)['payload']
        self.assertEqual(total_count, received['count'])
        self.assertEqual(sent['from_ts'], received['from_ts'])
        self.assertEqual(sent['to_ts'], received['to_ts'])
        self.assertEqual(sent['stats_range'], received['range'])
        self.assertListEqual(sent['data'][offset:count + offset], received[entity])

    def test_sitewide_artist_stat(self):
        """ Test to make sure valid response is received """
        for (api_name, entity) in test_sitewide_entity_params:
            with self.subTest(api_name=api_name, entity=entity):

                with open(self.path_to_data_file(f"sitewide_top_{entity}_db_data_for_api_test.json"), "r") as f:
                    sitewide_stat_payload = json.load(f)
                db_stats.insert_sitewide_jsonb_data(entity, StatRange[EntityRecord](**sitewide_stat_payload))

                response = self.client.get(url_for(api_name))
                self.assertSitewideStatEqual(sitewide_stat_payload, response, entity, 60, 25)

    def test_sitewide_artist_stat_too_many(self):
        """ Test to make sure response received has maximum 100 listens """
        for (api_name, entity) in test_sitewide_entity_params:
            with self.subTest(api_name=api_name, entity=entity):

                with open(self.path_to_data_file(f"sitewide_top_{entity}_db_data_for_api_test_too_many.json"), "r") as f:
                    sitewide_stat_payload = json.load(f)
                db_stats.insert_sitewide_jsonb_data(entity, StatRange[EntityRecord](**sitewide_stat_payload))

                response = self.client.get(url_for(api_name), query_string={'count': 101})
                self.assertSitewideStatEqual(sitewide_stat_payload, response, entity, 202, 100)

    def test_sitewide_stat_range(self):
        """ Test to make sure valid response is received when range is not all_time """
        for (api_name, entity) in test_sitewide_entity_params:
            for (stat_range, count) in [("week", 200), ("month", 60), ("year", 60)]:
                with self.subTest(api_name=api_name, entity=entity, stat_range=stat_range):
                    with open(self.path_to_data_file(f'sitewide_top_{entity}_db_data_for_api_test_{stat_range}.json'), 'r') as f:
                        payload = json.load(f)
                    db_stats.insert_sitewide_jsonb_data(entity, StatRange[EntityRecord](**payload))

                    response = self.client.get(url_for(api_name), query_string={'range': stat_range})
                    self.assertSitewideStatEqual(payload, response, entity, count, 25)

    def test_sitewide_artist_stat_invalid_range(self):
        """ Test to make sure 400 is received if range argument is invalid """
        for (api_name, _) in test_sitewide_entity_params:
            with self.subTest(api_name=api_name):
                response = self.client.get(url_for(api_name), query_string={'range': 'foobar'})
                self.assert400(response)
                self.assertEqual("Invalid range: foobar", response.json['error'])

    def test_sitewide_artist_stat_count(self):
        """ Test to make sure valid response is received if count argument is passed """
        for (api_name, entity) in test_sitewide_entity_params:
            with self.subTest(api_name=api_name, entity=entity):
                with open(self.path_to_data_file(f"sitewide_top_{entity}_db_data_for_api_test.json"), "r") as f:
                    sitewide_stat_payload = json.load(f)
                db_stats.insert_sitewide_jsonb_data(entity, StatRange[EntityRecord](**sitewide_stat_payload))

                response = self.client.get(url_for(api_name), query_string={'count': 10})
                self.assertSitewideStatEqual(sitewide_stat_payload, response, entity, 60, 10)

    def test_sitewide_stat_invalid_count(self):
        """ Test to make sure 400 response is received if count is negative or not integer """
        for (api_name, _) in test_sitewide_entity_params:
            for count in [-5, "foobar"]:
                with self.subTest(api_name=api_name, count=count):
                    response = self.client.get(url_for(api_name), query_string={'count': count})
                    self.assert400(response)
                    self.assertEqual("'count' should be a non-negative integer", response.json['error'])

    def test_sitewide_artist_stat_offset(self):
        """ Test to make sure valid response is received if offset argument is passed """
        for (api_name, entity) in test_sitewide_entity_params:
            with self.subTest(api_name=api_name, entity=entity):
                with open(self.path_to_data_file(f"sitewide_top_{entity}_db_data_for_api_test.json"), "r") as f:
                    sitewide_stat_payload = json.load(f)
                db_stats.insert_sitewide_jsonb_data(entity, StatRange[EntityRecord](**sitewide_stat_payload))

                response = self.client.get(url_for(api_name), query_string={'offset': 10})
                self.assertSitewideStatEqual(sitewide_stat_payload, response, entity, 60, 25, 10)

    def test_sitewide_stat_invalid_offset(self):
        """ Test to make sure 400 response is received if offset is negative or not integer """
        for (api_name, _) in test_sitewide_entity_params:
            for offset in [-5, "foobar"]:
                with self.subTest(api_name=api_name, offset=offset):
                    response = self.client.get(url_for(api_name), query_string={'offset': offset})
                    self.assert400(response)
                    self.assertEqual("'offset' should be a non-negative integer", response.json['error'])

    def test_sitewide_stat_not_calculated(self):
        """ Test to make sure that the API sends 204 if statistics have not been calculated yet """
        for (api_name, _) in test_sitewide_entity_params:
            with self.subTest(api_name=api_name):
                db_stats.delete_sitewide_stats()
                response = self.client.get(url_for(api_name))
                self.assertEqual(response.status_code, 204)
