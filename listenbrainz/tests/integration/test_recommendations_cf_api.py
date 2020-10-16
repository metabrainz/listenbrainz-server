import json
import uuid
from flask import url_for, current_app
from redis import Redis

import listenbrainz.db.user as db_user
import listenbrainz.db.recommendations_cf_recording as db_recommendations_cf_recording
from listenbrainz.tests.integration import IntegrationTestCase

from data.model.user_cf_recommendations_recording_message import UserRecommendationsJson


class CFRecommendationsViewsTestCase(IntegrationTestCase):
    def setUp(self):
        super(CFRecommendationsViewsTestCase, self).setUp()

        self.user = db_user.get_or_create(1, 'vansika_1')
        self.user2 = db_user.get_or_create(2, 'vansika_2')
        self.user3 = db_user.get_or_create(3, 'vansika_3')

        # generate test data
        data = {"recording_mbid": []}

        for score in range(1500, 0, -1):
            data["recording_mbid"].append(
                {
                    "recording_mbid": str(uuid.uuid4()),
                    "score": score
                }
            )

        db_recommendations_cf_recording.insert_user_recommendation(
            1,
            UserRecommendationsJson(**{
                'top_artist': data['recording_mbid'],
                'similar_artist': []
            })
        )

        db_recommendations_cf_recording.insert_user_recommendation(
            2,
            UserRecommendationsJson(**{
                'top_artist': [],
                'similar_artist': data['recording_mbid']
            })
        )

        # get recommendations
        self.user_recommendations = db_recommendations_cf_recording.get_user_recommendation(1)
        self.user2_recommendations = db_recommendations_cf_recording.get_user_recommendation(2)

    def tearDown(self):
        r = Redis(host=current_app.config['REDIS_HOST'], port=current_app.config['REDIS_PORT'])
        r.flushall()
        super(CFRecommendationsViewsTestCase, self).tearDown()

    def test_invalid_user(self):
        response = self.client.get(url_for('recommendations_cf_recording_v1.get_recommendations', user_name='invalid_user'))
        self.assert404(response)

    def test_artist_type(self):
        response = self.client.get(url_for('recommendations_cf_recording_v1.get_recommendations',
                                           user_name=self.user['musicbrainz_id']))
        self.assert400(response)

        response = self.client.get(url_for('recommendations_cf_recording_v1.get_recommendations',
                                           user_name=self.user['musicbrainz_id']), query_string={'artist_type': 'invalid_type'})
        self.assert400(response)

    def test_inactive_user(self):
        response = self.client.get(url_for('recommendations_cf_recording_v1.get_recommendations',
                                           user_name=self.user3['musicbrainz_id']), query_string={'artist_type': 'top'})
        self.assertEqual(response.status_code, 204)

    def test_recommendations_not_generated(self):
        response = self.client.get(url_for('recommendations_cf_recording_v1.get_recommendations',
                                           user_name=self.user2['musicbrainz_id']), query_string={'artist_type': 'top'})
        self.assertEqual(response.status_code, 204)

        response = self.client.get(url_for('recommendations_cf_recording_v1.get_recommendations',
                                           user_name=self.user['musicbrainz_id']), query_string={'artist_type': 'similar'})
        self.assertEqual(response.status_code, 204)

    def test_recommendations_without_count(self):
        response = self.client.get(url_for('recommendations_cf_recording_v1.get_recommendations',
                                           user_name=self.user['musicbrainz_id']), query_string={'artist_type': 'top'})
        self.assert200(response)
        data = json.loads(response.data)['payload']

        received_user_name = data['user_name']
        self.assertEqual(received_user_name, self.user['musicbrainz_id'])

        received_count = data['count']
        self.assertEqual(received_count, 25)

        received_offset = data['offset']
        self.assertEqual(received_offset, 0)

        received_type = data['type']
        self.assertEqual(received_type, 'top')

        recieved_entity = data['entity']
        self.assertEqual(recieved_entity, 'recording')

        received_total_count = data['total_mbid_count']
        expected_total_count = len(getattr(self.user_recommendations, 'recording_mbid').dict()['top_artist'])

        received_ts = data['last_updated']
        expected_ts = int(getattr(self.user_recommendations, 'created').timestamp())
        self.assertEqual(received_ts, expected_ts)

        received_top_artist_recommendations = data['mbids']
        expected_top_artist_recommendations = getattr(self.user_recommendations, 'recording_mbid').dict()['top_artist'][:25]
        self.assertEqual(expected_top_artist_recommendations, received_top_artist_recommendations)

    def test_recommendations_with_count(self):
        response = self.client.get(url_for('recommendations_cf_recording_v1.get_recommendations',
                                           user_name=self.user2['musicbrainz_id']),
                                           query_string={'artist_type': 'similar', 'count': 10})
        self.assert200(response)
        data = json.loads(response.data)['payload']

        received_user_name = data['user_name']
        self.assertEqual(received_user_name, self.user2['musicbrainz_id'])

        received_count = data['count']
        self.assertEqual(received_count, 10)

        received_offset = data['offset']
        self.assertEqual(received_offset, 0)

        received_type = data['type']
        self.assertEqual(received_type, 'similar')

        recieved_entity = data['entity']
        self.assertEqual(recieved_entity, 'recording')

        received_total_count = data['total_mbid_count']
        expected_total_count = len(getattr(self.user2_recommendations, 'recording_mbid').dict()['similar_artist'])

        received_ts = data['last_updated']
        expected_ts = int(getattr(self.user2_recommendations, 'created').timestamp())
        self.assertEqual(received_ts, expected_ts)

        received_top_artist_recommendations = data['mbids']
        expected_top_artist_recommendations = getattr(self.user2_recommendations, 'recording_mbid').dict()['similar_artist'][:10]
        self.assertEqual(expected_top_artist_recommendations, received_top_artist_recommendations)

    def test_recommendations_too_many(self):
        response = self.client.get(url_for('recommendations_cf_recording_v1.get_recommendations',
                                           user_name=self.user2['musicbrainz_id']),
                                           query_string={'artist_type': 'similar', 'count': 1500, 'offset': 100})
        self.assert200(response)
        data = json.loads(response.data)['payload']

        received_user_name = data['user_name']
        self.assertEqual(received_user_name, self.user2['musicbrainz_id'])

        received_count = data['count']
        self.assertEqual(received_count, 1000)

        received_offset = data['offset']
        self.assertEqual(received_offset, 100)

        received_type = data['type']
        self.assertEqual(received_type, 'similar')

        recieved_entity = data['entity']
        self.assertEqual(recieved_entity, 'recording')

        received_total_count = data['total_mbid_count']
        expected_total_count = len(getattr(self.user2_recommendations, 'recording_mbid').dict()['similar_artist'])

        received_ts = data['last_updated']
        expected_ts = int(getattr(self.user2_recommendations, 'created').timestamp())
        self.assertEqual(received_ts, expected_ts)

        received_top_artist_recommendations = data['mbids']
        expected_top_artist_recommendations = getattr(self.user2_recommendations, 'recording_mbid').dict()['similar_artist'][100:1100]
        self.assertEqual(expected_top_artist_recommendations, received_top_artist_recommendations)

    def test_recommendations_with_offset(self):
        response = self.client.get(url_for('recommendations_cf_recording_v1.get_recommendations',
                                           user_name=self.user['musicbrainz_id']),
                                           query_string={'artist_type': 'top', 'offset': 10})

        self.assert200(response)
        data = json.loads(response.data)['payload']

        received_user_name = data['user_name']
        self.assertEqual(received_user_name, self.user['musicbrainz_id'])

        received_count = data['count']
        self.assertEqual(received_count, 25)

        received_offset = data['offset']
        self.assertEqual(received_offset, 10)

        received_type = data['type']
        self.assertEqual(received_type, 'top')

        recieved_entity = data['entity']
        self.assertEqual(recieved_entity, 'recording')

        received_total_count = data['total_mbid_count']
        expected_total_count = len(getattr(self.user_recommendations, 'recording_mbid').dict()['top_artist'])

        received_ts = data['last_updated']
        expected_ts = int(getattr(self.user_recommendations, 'created').timestamp())
        self.assertEqual(received_ts, expected_ts)

        received_top_artist_recommendations = data['mbids']
        expected_top_artist_recommendations = getattr(self.user_recommendations, 'recording_mbid').dict()['top_artist'][10:35]
        self.assertEqual(expected_top_artist_recommendations, received_top_artist_recommendations)
