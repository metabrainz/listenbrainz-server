import json
from copy import deepcopy
from datetime import datetime
from unittest.mock import patch

import requests
import orjson
from brainzutils.ratelimit import set_rate_limits

import listenbrainz.db.stats as db_stats
import listenbrainz.db.user as db_user
import requests_mock

from data.model.user_artist_map import UserArtistMapRecord

from listenbrainz.config import LISTENBRAINZ_LABS_API_URL
from listenbrainz.db import couchdb
from listenbrainz.spark.handlers import handle_entity_listener
from listenbrainz.tests.integration import IntegrationTestCase


class MockDate(datetime):
    """ Mock class for datetime which returns epoch """

    @classmethod
    def now(cls, tzinfo=None):
        return cls.fromtimestamp(0)


class StatsAPITestCase(IntegrationTestCase):

    @classmethod
    def setUpClass(cls) -> None:
        super(StatsAPITestCase, cls).setUpClass()

        stats = ["artists", "releases", "recordings", "release_groups", "daily_activity", "listening_activity",
                 "artist_map"]
        ranges = ["week", "month", "year", "all_time"]
        for stat in stats:
            for range_ in ranges:
                couchdb.create_database(f"{stat}_{range_}_20220718")

        # we do not clear the couchdb databases after each test. user stats keep working because
        # the user id changes for each test. for sitewide stats this is not the case as the user id
        # is always fixed so to ensure the payload is only inserted once, keep it in setUpClass
        # otherwise we will get an error.
        with open(cls.path_to_data_file('sitewide_top_artists_db_data_for_api_test.json'), 'r') as f:
            cls.sitewide_artist_payload = json.load(f)
        db_stats.insert_sitewide_stats('artists', 'all_time', 0, 5, cls.sitewide_artist_payload)

    def setUp(self):
        self.maxDiff = None
        set_rate_limits(5000, 50000, 10)

        # app context
        super(StatsAPITestCase, self).setUp()
        self.app.config["DEBUG"] = True
        self.user = db_user.get_or_create(self.db_conn, 1, 'testuserpleaseignore')
        self.another_user = db_user.get_or_create(self.db_conn, 1999, 'another_user')
        self.no_stat_user = db_user.get_or_create(self.db_conn, 222222, 'nostatuser')

        with open(self.path_to_data_file('user_top_artists_db_data_for_api_test.json'), 'r') as f:
            self.user_artist_payload = json.load(f)
            self.user_artist_payload[0]["user_id"] = self.user["id"]
        database = 'artists_all_time_20220718'
        db_stats.insert(database, 0, 5, self.user_artist_payload)

        # Insert release data
        with open(self.path_to_data_file('user_top_releases_db_data_for_api_test.json'), 'r') as f:
            self.user_release_payload = json.load(f)
            self.user_release_payload[0]["user_id"] = self.user["id"]
        database = 'releases_all_time_20220718'
        db_stats.insert(database, 0, 5, self.user_release_payload)

        # Insert release data
        with open(self.path_to_data_file('user_top_release_groups_db_data_for_api_test.json'), 'r') as f:
            self.user_release_group_payload = json.load(f)
            self.user_release_group_payload[0]["user_id"] = self.user["id"]
        database = 'release_groups_all_time_20220718'
        db_stats.insert(database, 0, 5, self.user_release_group_payload)

        # Insert recording data
        with open(self.path_to_data_file('user_top_recordings_db_data_for_api_test.json'), 'r') as f:
            self.recording_payload = json.load(f)
            self.recording_payload[0]["user_id"] = self.user["id"]
        database = 'recordings_all_time_20220718'
        db_stats.insert(database, 0, 5, self.recording_payload)

        # Insert listening activity data
        with open(self.path_to_data_file('user_listening_activity_db_data_for_api_test.json')) as f:
            self.listening_activity_payload = json.load(f)
            self.listening_activity_payload[0]["user_id"] = self.user["id"]
        database = 'listening_activity_all_time_20220718'
        db_stats.insert(database, 0, 5, self.listening_activity_payload)

        # Insert daily activity data
        with open(self.path_to_data_file('user_daily_activity_db_data_for_api_test.json')) as f:
            self.daily_activity_payload = json.load(f)
            self.daily_activity_payload[0]["user_id"] = self.user["id"]
        database = 'daily_activity_all_time_20220718'
        db_stats.insert(database, 0, 5, self.daily_activity_payload)

        # Insert artist map data
        with open(self.path_to_data_file('user_artist_map_db_data_for_api_test.json')) as f:
            self.artist_map_payload = json.load(f)
            self.artist_map_payload[0]["user_id"] = self.user["id"]
        database = 'artist_map_all_time_20220718'
        db_stats.insert(database, 0, 5, self.artist_map_payload)

        self.create_user_with_id(db_stats.SITEWIDE_STATS_USER_ID, 2, "listenbrainz-stats-user")

        self.entity_endpoints = {
            "artists": {
                "endpoint": "stats_api_v1.get_artist",
                "total_count_key": "total_artist_count",
                "payload": self.user_artist_payload
            },
            "releases": {
                "endpoint": "stats_api_v1.get_release",
                "total_count_key": "total_release_count",
                "payload": self.user_release_payload
            },
            "release_groups": {
                "endpoint": "stats_api_v1.get_release_group",
                "total_count_key": "total_release_group_count",
                "payload": self.user_release_group_payload
            },
            "recordings": {
                "endpoint": "stats_api_v1.get_recording",
                "total_count_key": "total_recording_count",
                "payload": self.recording_payload
            }
        }

        self.non_entity_endpoints = {
            "listening_activity": {
                "endpoint": "stats_api_v1.get_listening_activity",
                "payload": self.listening_activity_payload
            },
            "daily_activity": {
                "endpoint": "stats_api_v1.get_daily_activity",
                "payload": self.daily_activity_payload
            },
            "artist_map": {
                "endpoint": "stats_api_v1.get_artist_map",
                "payload": self.artist_map_payload
            }
        }

        self.all_endpoints = self.entity_endpoints | self.non_entity_endpoints

        self.sitewide_entity_endpoints = {
            "artists": {
                "endpoint": "stats_api_v1.get_sitewide_artist",
                "payload": self.sitewide_artist_payload
            }
        }

    @classmethod
    def tearDownClass(cls) -> None:
        base_url = couchdb.get_base_url()
        databases_url = f"{base_url}/_all_dbs"
        response = requests.get(databases_url)
        all_databases = response.json()

        for database in all_databases:
            if database == "_users":
                continue
            databases_url = f"{base_url}/{database}"
            requests.delete(databases_url)
        super(StatsAPITestCase, cls).tearDownClass()

    def test_query_params_validation(self):
        """ Test to make sure the query params sent to stats' api are validated and appropriate error
         message is given for invalid params """
        for stat_type in self.all_endpoints:
            url = self.all_endpoints[stat_type]["endpoint"]
            user_name = self.user['musicbrainz_id']
            endpoint_user_url = self.custom_url_for(url, user_name=user_name)

            with self.subTest(f"test 400 is received for invalid range query param on endpoint : {url}", url=url):
                response = self.client.get(endpoint_user_url, query_string={'range': 'foobar'})
                self.assert400(response)
                self.assertEqual("Invalid range: foobar", response.json['error'])

            with self.subTest(f"test that the API sends 404 if user does not exist on endpoint : {url}", url=url):
                response = self.client.get(self.custom_url_for(url, user_name='nouser'))
                self.assert404(response)
                self.assertEqual('Cannot find user: nouser', response.json['error'])

            with self.subTest(f"test to make sure that the API sends 204 if statistics for user have not"
                              f" been calculated yet on endpoint: {url}", url=url):
                response = self.client.get(self.custom_url_for(url, user_name=self.no_stat_user['musicbrainz_id']))
                self.assertEqual(response.status_code, 204)

            if stat_type in self.non_entity_endpoints:
                continue

            with self.subTest(f"test 400 is received if offset is not an integer on endpoint : {url}", url=url):
                response = self.client.get(endpoint_user_url, query_string={'offset': 'foobar'})
                self.assert400(response)
                self.assertEqual("'offset' should be a non-negative integer", response.json['error'])

            with self.subTest(f"test 400 is received if offset is a negative integer on endpoint : {url}", url=url):
                response = self.client.get(endpoint_user_url, query_string={'offset': -5})
                self.assert400(response)
                self.assertEqual("'offset' should be a non-negative integer", response.json['error'])

            with self.subTest(f"test 400 is received if count is not an integer on endpoint : {url}", url=url):
                response = self.client.get(endpoint_user_url, query_string={'count': 'foobar'})
                self.assert400(response)
                self.assertEqual("'count' should be a non-negative integer", response.json['error'])

            with self.subTest(f"test 400 is received if count is a negative integer on endpoint : {url}", url=url):
                response = self.client.get(endpoint_user_url, query_string={'count': -5})
                self.assert400(response)
                self.assertEqual("'count' should be a non-negative integer", response.json['error'])

    def assertUserStatEqual(self, request, response, entity, stats_range, total_count_key, count, offset=0,
                            user_name=None):
        """ Checks the stats response received from the api is valid and then compare the stats payload inserted in db
            with the payload received from the api.
            Many tests insert larger payloads but expect a smaller number of stats to returned so
            this method also accepts a count and offset parameter denoting how many stats and which
            entries to check.
        """
        self.assert200(response)

        sent = request[0]
        received = orjson.loads(response.data)['payload']

        if not user_name:
            user_name = self.user['musicbrainz_id']

        self.assertEqual(user_name, received['user_id'])
        self.assertEqual(count, received['count'])
        self.assertEqual(sent['count'], received[total_count_key])
        self.assertEqual(sent['from_ts'], received['from_ts'])
        self.assertEqual(sent['to_ts'], received['to_ts'])
        self.assertEqual(stats_range, received['range'])
        self.assertListEqual(sent['data'][offset:count + offset], received[entity])

    def assertSitewideStatEqual(self, sent, response, entity, stats_range, count, offset: int = 0):
        self.assert200(response)

        received = orjson.loads(response.data)['payload']

        singular_entity = entity[:-1] if entity.endswith('s') else entity
        self.assertEqual(sent[f'total_{singular_entity}_count'], received[f'total_{singular_entity}_count'])
        self.assertEqual(count, received['count'])
        self.assertEqual(sent['from_ts'], received['from_ts'])
        self.assertEqual(sent['to_ts'], received['to_ts'])
        self.assertEqual(stats_range, received['range'])
        self.assertListEqual(sent['data'][offset:count + offset], received[entity])

    def assertListeningActivityEqual(self, request, response):
        self.assert200(response)
        received = json.loads(response.data)['payload']
        sent = request[0]

        self.assertEqual(sent['from_ts'], received['from_ts'])
        self.assertEqual(sent['to_ts'], received['to_ts'])
        self.assertEqual(sent['data'], received['listening_activity'])
        self.assertEqual(self.user['musicbrainz_id'], received['user_id'])

    def assertArtistMapEqual(self, request, response):
        self.assert200(response)
        received = json.loads(response.data)['payload']
        sent = request[0]

        self.assertEqual(sent['from_ts'], received['from_ts'])
        self.assertEqual(sent['to_ts'], received['to_ts'])
        self.assertEqual(sent['data'], received['artist_map'])
        self.assertEqual(self.user['musicbrainz_id'], received['user_id'])

    def assertDailyActivityEqual(self, sent, response):
        self.assert200(response)
        received = json.loads(response.data)['payload']
        self.assertEqual(0, received['from_ts'])
        self.assertEqual(5, received['to_ts'])
        self.assertEqual(sent['range'], received['range'])
        self.assertCountEqual(sent['daily_activity'], received['daily_activity'])
        self.assertEqual(self.user['musicbrainz_id'], received['user_id'])

    def test_user_entity_stat(self):
        """ Test to make sure valid response is received """
        for entity in self.entity_endpoints:
            endpoint = self.entity_endpoints[entity]["endpoint"]
            total_count_key = self.entity_endpoints[entity]["total_count_key"]
            payload = self.entity_endpoints[entity]["payload"]
            with self.subTest(f"test api returns valid response for {entity} stats", entity=entity):
                response = self.client.get(self.custom_url_for(endpoint, user_name=self.user['musicbrainz_id']))
                self.assertUserStatEqual(payload, response, entity, "all_time", total_count_key, 25)

            with self.subTest(f"test api returns valid response for {entity} stats when using offset", entity=entity):
                response = self.client.get(self.custom_url_for(endpoint, user_name=self.user['musicbrainz_id']),
                                           query_string={'offset': 5})
                self.assertUserStatEqual(payload, response, entity, "all_time", total_count_key, 25, 5)

            with self.subTest(f"test api returns valid response for {entity} stats when using count", entity=entity):
                response = self.client.get(self.custom_url_for(endpoint, user_name=self.user['musicbrainz_id']),
                                           query_string={'count': 5})
                self.assertUserStatEqual(payload, response, entity, "all_time", total_count_key, 5)

            # use different user for these subtest because otherwise need to update document
            # in existing database whose data may be needed in other tests.
            with self.subTest(f"test api returns at most 1000 stats in a response for {entity}", entity=entity):
                with open(self.path_to_data_file(f'user_top_{entity}_db_data_for_api_test_too_many.json'), 'r') as f:
                    payload = json.load(f)
                    payload[0]["user_id"] = self.another_user["id"]
                db_stats.insert(f"{entity}_all_time_20220718", 0, 5, payload)
                response = self.client.get(self.custom_url_for(endpoint, user_name=self.another_user['musicbrainz_id']),
                                           query_string={'count': 100})
                self.assertUserStatEqual(payload, response, entity, "all_time", total_count_key, 100,
                                         user_name=self.another_user['musicbrainz_id'])

            for range_ in ["week", "month", "year"]:
                with self.subTest(f"test api returns valid stats response for {range_} {entity}", entity=entity,
                                  range_=range_):
                    with open(self.path_to_data_file(f'user_top_{entity}_db_data_for_api_test_{range_}.json'),
                              'r') as f:
                        payload = json.load(f)
                        payload[0]["user_id"] = self.user["id"]
                    db_stats.insert(f"{entity}_{range_}_20220718", 0, 5, payload)
                    response = self.client.get(self.custom_url_for(endpoint, user_name=self.user['musicbrainz_id']),
                                               query_string={'range': range_})
                    self.assertUserStatEqual(payload, response, entity, range_, total_count_key, payload[0]['count'])

    def test_listening_activity_stat(self):
        endpoint = self.non_entity_endpoints["listening_activity"]["endpoint"]
        with self.subTest(f"test valid response is received for listening_activity stats"):
            payload = self.non_entity_endpoints["listening_activity"]["payload"]
            response = self.client.get(self.custom_url_for(endpoint, user_name=self.user['musicbrainz_id']))
            self.assertListeningActivityEqual(payload, response)

        for range_ in ["week", "month", "year"]:
            with self.subTest(f"test valid response is received for {range_} listening_activity stats", range_=range_):
                with open(self.path_to_data_file(f'user_listening_activity_db_data_for_api_test_{range_}.json'),
                          'r') as f:
                    payload = json.load(f)
                    payload[0]["user_id"] = self.user["id"]
                db_stats.insert(f"listening_activity_{range_}_20220718", 0, 5, payload)
                response = self.client.get(self.custom_url_for(endpoint, user_name=self.user['musicbrainz_id']),
                                           query_string={'range': range_})
                self.assertListeningActivityEqual(payload, response)

    def test_daily_activity_stat(self):
        endpoint = self.non_entity_endpoints["daily_activity"]["endpoint"]
        with self.subTest(f"test valid response is received for daily_activity stats"):
            response = self.client.get(self.custom_url_for(endpoint, user_name=self.user['musicbrainz_id']))
            with open(self.path_to_data_file('user_daily_activity_api_output.json')) as f:
                expected = json.load(f)["payload"]
                expected["user_id"] = self.user["id"]
            self.assertDailyActivityEqual(expected, response)

        for range_ in ["week", "month", "year"]:
            with self.subTest(f"test valid response is received for {range_} daily_activity stats", range_=range_):
                with open(self.path_to_data_file(f'user_daily_activity_db_data_for_api_test_{range_}.json'), 'r') as f:
                    payload = json.load(f)
                    payload[0]["user_id"] = self.user["id"]
                db_stats.insert(f"daily_activity_{range_}_20220718", 0, 5, payload)
                response = self.client.get(self.custom_url_for(endpoint, user_name=self.user['musicbrainz_id']),
                                           query_string={'range': range_})
                with open(self.path_to_data_file(f'user_daily_activity_api_output_{range_}.json')) as f:
                    expected = json.load(f)["payload"]
                    expected["user_id"] = self.user["id"]
                self.assertDailyActivityEqual(expected, response)

    @patch('listenbrainz.webserver.views.stats_api.datetime', MockDate)
    def test_artist_map_stat(self):
        endpoint = self.non_entity_endpoints["artist_map"]["endpoint"]
        with self.subTest(f"test valid response is received for artist_map stats"):
            response = self.client.get(self.custom_url_for(endpoint, user_name=self.user['musicbrainz_id']))
            payload = self.non_entity_endpoints["artist_map"]["payload"]
            self.assertArtistMapEqual(payload, response)

        for range_ in ["week", "month", "year"]:
            with self.subTest(f"test valid response is received for {range_} artist_map stats", range_=range_):
                with open(self.path_to_data_file(f'user_artist_map_db_data_for_api_test_{range_}.json'), 'r') as f:
                    payload = json.load(f)
                    payload[0]["user_id"] = self.user["id"]
                db_stats.insert(f"artist_map_{range_}_20220718", 0, 5, payload)
                response = self.client.get(self.custom_url_for(endpoint, user_name=self.user['musicbrainz_id']),
                                           query_string={'range': range_})
                self.assertArtistMapEqual(payload, response)

    def test_sitewide_entity_stat(self):
        for entity in self.sitewide_entity_endpoints:
            endpoint = self.sitewide_entity_endpoints[entity]["endpoint"]
            payload = self.sitewide_entity_endpoints[entity]["payload"]
            with self.subTest(f"test api returns valid response for {entity} stats", entity=entity):
                response = self.client.get(self.custom_url_for(endpoint))
                self.assertSitewideStatEqual(payload, response, entity, "all_time", 25)

            with self.subTest(f"test api returns valid response for {entity} stats when using offset", entity=entity):
                response = self.client.get(self.custom_url_for(endpoint), query_string={'offset': 5})
                self.assertSitewideStatEqual(payload, response, entity, "all_time", 25, 5)

            with self.subTest(f"test api returns valid response for {entity} stats when using count", entity=entity):
                response = self.client.get(self.custom_url_for(endpoint), query_string={'count': 5})
                self.assertSitewideStatEqual(payload, response, entity, "all_time", 5)

            for range_ in ["week", "month", "year"]:
                with self.subTest(f"test api returns valid stats response for {range_} {entity}", entity=entity,
                                  range_=range_):
                    with open(self.path_to_data_file(f'sitewide_top_{entity}_db_data_for_api_test_{range_}.json'),
                              'r') as f:
                        payload = json.load(f)
                    db_stats.insert_sitewide_stats(entity, range_, 0, 5, payload)
                    response = self.client.get(self.custom_url_for(endpoint), query_string={'range': range_})
                    self.assertSitewideStatEqual(payload, response, entity, range_, 25)

            with self.subTest(f"test api returns 204 if stat not calculated"):
                response = self.client.get(self.custom_url_for(endpoint), query_string={'range': 'this_week'})
                self.assertEqual(response.status_code, 204)

            # week data file has 200 items in it so using it for this test
            with self.subTest(f"test api returns at most 100 stats in a response for {entity}", entity=entity):
                with open(self.path_to_data_file(f'sitewide_top_{entity}_db_data_for_api_test_week.json'), 'r') as f:
                    payload = json.load(f)
                db_stats.insert_sitewide_stats(entity, "week", 0, 5, payload)
                response = self.client.get(self.custom_url_for(endpoint), query_string={'count': 200, 'range': 'week'})
                self.assertSitewideStatEqual(payload, response, entity, "week", 200)

    def _setup_listener_stats(self, file) -> dict:
        with open(self.path_to_data_file(file), "r") as f:
            data = json.load(f)
        couchdb.create_database(data["database"])

        for entity in data["data"]:
            for listener in entity["listeners"]:
                if listener["user_id"] == 1:
                    listener["user_id"] = self.user["id"]
                elif listener["user_id"] == 2:
                    listener["user_id"] = self.another_user["id"]

        handle_entity_listener(data)

        return data

    def test_artist_listeners_stats(self):
        data = self._setup_listener_stats("artists_listeners_db_data_for_api_test.json")

        response = self.client.get(self.custom_url_for("stats_api_v1.get_artist_listeners",
                                                       artist_mbid="056e4f3e-d505-4dad-8ec1-d04f521cbb56"))
        self.assert200(response)
        self.assertEqual(response.json["payload"], {
            "artist_mbid": "056e4f3e-d505-4dad-8ec1-d04f521cbb56",
            "artist_name": "Daft Punk",
            "listeners": [
                {
                    "listen_count": 5,
                    "user_name": self.another_user["musicbrainz_id"]
                },
                {
                    "listen_count": 3,
                    "user_name": self.user["musicbrainz_id"]
                }
            ],
            "total_listen_count": 8,
            "stats_range": "all_time",
            "from_ts": data["from_ts"],
            "last_updated": response.json["payload"]["last_updated"],
            "to_ts": data["to_ts"],
        })

    def test_release_group_listeners_stats(self):
        data = self._setup_listener_stats("release_groups_listeners_db_data_for_api_test.json")

        response = self.client.get(self.custom_url_for("stats_api_v1.get_release_group_listeners",
                                                       release_group_mbid="f53bf269-4601-35a4-8aa7-ed54a1d58eed"))
        self.assert200(response)
        self.assertEqual(response.json["payload"], {
            "total_listen_count": 7,
            "listeners": [
                {
                    "user_name": self.user["musicbrainz_id"],
                    "listen_count": 4
                },
                {
                    "user_name": self.another_user["musicbrainz_id"],
                    "listen_count": 3
                }
            ],
            "release_group_mbid": "f53bf269-4601-35a4-8aa7-ed54a1d58eed",
            "release_group_name": "Mickey Mouse Operation",
            "artist_name": "Little People",
            "caa_id": 27037140096,
            "caa_release_mbid": "85655611-5af0-436c-b00f-6609afa502ff",
            "artist_mbids": [
                "78c94cba-761f-4212-8508-a24bda2e57dc"
            ],
            "from_ts": data["from_ts"],
            "stats_range": "all_time",
            "last_updated": response.json["payload"]["last_updated"],
            "to_ts": data["to_ts"],
        })

    def test_entity_listeners_stats(self):
        response = self.client.get(
            self.custom_url_for("stats_api_v1.get_artist_listeners", artist_mbid="056e4f3e-d505-4dad-8ec1-d04f521cbb56",
                                range="this_week"))
        self.assertStatus(response, 204)

        response = self.client.get(self.custom_url_for("stats_api_v1.get_release_group_listeners",
                                                       release_group_mbid="f53bf269-4601-35a4-8aa7-ed54a1d58eed",
                                                       range="this_week"))
        self.assertStatus(response, 204)

        response = self.client.get(
            self.custom_url_for("stats_api_v1.get_artist_listeners", artist_mbid="056e4f3e-d505-4dad-8ec1-d04f521cbb56",
                                range="foobar"))
        self.assert400(response)

        response = self.client.get(self.custom_url_for("stats_api_v1.get_release_group_listeners",
                                                       release_group_mbid="f53bf269-4601-35a4-8aa7-ed54a1d58eed",
                                                       range="foobar"))
        self.assert400(response)
