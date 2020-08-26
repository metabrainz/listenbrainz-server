import json
from flask import url_for, current_app
from redis import Redis

import listenbrainz.db.user as db_user
import listenbrainz.db.missing_musicbrainz_data as db_missing_musicbrainz_data
from data.model.user_missing_musicbrainz_data import UserMissingMusicBrainzDataJson
from listenbrainz.tests.integration import IntegrationTestCase


class MissingMusicBrainzDataViewsTestCase(IntegrationTestCase):
    def setUp(self):
        super(MissingMusicBrainzDataViewsTestCase, self).setUp()

        self.user = db_user.get_or_create(1, 'vansika_1')
        self.user2 = db_user.get_or_create(2, 'vansika_2')

        with open(self.path_to_data_file('missing_musicbrainz_data.json'), 'r') as f:
            missing_musicbrainz_data = json.load(f)

        db_missing_musicbrainz_data.insert_user_missing_musicbrainz_data(
            user_id=self.user['id'],
            missing_musicbrainz_data=UserMissingMusicBrainzDataJson(**{'missing_musicbrainz_data': missing_musicbrainz_data}),
            source='cf'
        )

        self.data = db_missing_musicbrainz_data.get_user_missing_musicbrainz_data(user_id=self.user['id'], source='cf')

    def tearDown(self):
        r = Redis(host=current_app.config['REDIS_HOST'], port=current_app.config['REDIS_PORT'])
        r.flushall()
        super(MissingMusicBrainzDataViewsTestCase, self).tearDown()

    def test_invalid_user(self):
        response = self.client.get(url_for('missing_musicbrainz_data_v1.get_missing_musicbrainz_data',
                                           user_name='invalid_user'))
        self.assert404(response)

    def test_user_musicbrainz_data_not_calculated(self):
        response = self.client.get(url_for('missing_musicbrainz_data_v1.get_missing_musicbrainz_data',
                                           user_name=self.user2['musicbrainz_id']))
        self.assertEqual(response.status_code, 204)

    def test_missing_musicbrainz_data_without_count(self):
        response = self.client.get(url_for('missing_musicbrainz_data_v1.get_missing_musicbrainz_data',
                                           user_name=self.user['musicbrainz_id']))
        self.assert200(response)
        data = json.loads(response.data)['payload']

        received_user_name = data['user_name']
        self.assertEqual(received_user_name, self.user['musicbrainz_id'])

        received_count = data['count']
        self.assertEqual(received_count, 25)

        received_offset = data['offset']
        self.assertEqual(received_offset, 0)

        received_total_count = data['total_data_count']
        expected_total_count = len(getattr(self.data, 'data').dict()['missing_musicbrainz_data'])

        received_ts = data['last_updated']
        expected_ts = int(getattr(self.data, 'created').timestamp())
        self.assertEqual(received_ts, expected_ts)

        received_data = data['data']
        expected_data = getattr(self.data, 'data').dict()['missing_musicbrainz_data'][:25]
        self.assertEqual(expected_data, received_data)

    def test_missing_musicbrainz_data_with_count(self):
        response = self.client.get(url_for('missing_musicbrainz_data_v1.get_missing_musicbrainz_data',
                                           user_name=self.user['musicbrainz_id']),
                                   query_string={'count': 10})
        self.assert200(response)
        data = json.loads(response.data)['payload']

        received_user_name = data['user_name']
        self.assertEqual(received_user_name, self.user['musicbrainz_id'])

        received_count = data['count']
        self.assertEqual(received_count, 10)

        received_offset = data['offset']
        self.assertEqual(received_offset, 0)

        received_total_count = data['total_data_count']
        expected_total_count = len(getattr(self.data, 'data').dict()['missing_musicbrainz_data'])
        self.assertEqual(received_total_count, expected_total_count)

        received_ts = data['last_updated']
        expected_ts = int(getattr(self.data, 'created').timestamp())
        self.assertEqual(received_ts, expected_ts)

        received_data = data['data']
        expected_data = getattr(self.data, 'data').dict()['missing_musicbrainz_data'][:10]
        self.assertEqual(expected_data, received_data)

    def test_missing_musicbrainz_data_too_many(self):
        response = self.client.get(url_for('missing_musicbrainz_data_v1.get_missing_musicbrainz_data',
                                           user_name=self.user['musicbrainz_id']),
                                   query_string={'count': 108})
        self.assert200(response)
        data = json.loads(response.data)['payload']

        received_user_name = data['user_name']
        self.assertEqual(received_user_name, self.user['musicbrainz_id'])

        received_count = data['count']
        self.assertEqual(received_count, 100)

        received_offset = data['offset']
        self.assertEqual(received_offset, 0)

        received_total_count = data['total_data_count']
        expected_total_count = len(getattr(self.data, 'data').dict()['missing_musicbrainz_data'])
        self.assertEqual(received_total_count, expected_total_count)

        received_ts = data['last_updated']
        expected_ts = int(getattr(self.data, 'created').timestamp())
        self.assertEqual(received_ts, expected_ts)

        received_data = data['data']
        expected_data = getattr(self.data, 'data').dict()['missing_musicbrainz_data'][:100]
        self.assertEqual(expected_data, received_data)

    def test_missing_musicbrainz_data_with_offset(self):
        response = self.client.get(url_for('missing_musicbrainz_data_v1.get_missing_musicbrainz_data',
                                           user_name=self.user['musicbrainz_id']),
                                   query_string={'offset': 10})

        self.assert200(response)
        data = json.loads(response.data)['payload']

        received_user_name = data['user_name']
        self.assertEqual(received_user_name, self.user['musicbrainz_id'])

        received_count = data['count']
        self.assertEqual(received_count, 15)

        received_offset = data['offset']
        self.assertEqual(received_offset, 10)

        received_total_count = data['total_data_count']
        expected_total_count = len(getattr(self.data, 'data').dict()['missing_musicbrainz_data'])
        self.assertEqual(received_total_count, expected_total_count)

        received_ts = data['last_updated']
        expected_ts = int(getattr(self.data, 'created').timestamp())
        self.assertEqual(received_ts, expected_ts)

        received_data = data['data']
        expected_data = getattr(self.data, 'data').dict()['missing_musicbrainz_data'][10:25]
        self.assertEqual(expected_data, received_data)
