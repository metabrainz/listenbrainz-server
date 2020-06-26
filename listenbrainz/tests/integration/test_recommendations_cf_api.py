import json
from flask import url_for, current_app
from redis import Redis

import listenbrainz.db.user as db_user
import listenbrainz.db.recommendations_cf_recording as db_recommendations_cf_recording
from listenbrainz.tests.integration import IntegrationTestCase

class CFRecommendationsViewsTestCase(IntegrationTestCase):
    def setUp(self):
        super(CFRecommendationsViewsTestCase, self).setUp()

        self.user = db_user.get_or_create(1, 'vansika_1')
        self.user2 = db_user.get_or_create(2, 'vansika_2')
        self.user3 = db_user.get_or_create(3, 'vansika_3')
        # insert recommendations
        with open(self.path_to_data_file('cf_recommendations_db_data_for_api_test_recording.json'), 'r') as f:
            self.payload = json.load(f)

        db_recommendations_cf_recording.insert_user_recommendation(1, self.payload['recording_mbid'], [])
        db_recommendations_cf_recording.insert_user_recommendation(2, [], self.payload['recording_mbid'])

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
                                           user_name=self.user['musicbrainz_id']), query_string={'type': 'invalid_type'})
        self.assert400(response)

    def test_inactive_user(self):
        response = self.client.get(url_for('recommendations_cf_recording_v1.get_recommendations',
                                           user_name=self.user3['musicbrainz_id']), query_string={'type': 'top'})
        self.assertEqual(response.status_code, 204)


    def test_recommendations_not_generated(self):
        response = self.client.get(url_for('recommendations_cf_recording_v1.get_recommendations',
                                           user_name=self.user2['musicbrainz_id']), query_string={'type': 'top'})
        self.assertEqual(response.status_code, 204)

        response = self.client.get(url_for('recommendations_cf_recording_v1.get_recommendations',
                                           user_name=self.user['musicbrainz_id']), query_string={'type': 'similar'})
        self.assertEqual(response.status_code, 204)

    def test_recommendations_without_count(self):
        response = self.client.get(url_for('recommendations_cf_recording_v1.get_recommendations',
                                           user_name=self.user['musicbrainz_id']), query_string={'type': 'top'})
        self.assert200(response)
        data = json.loads(response.data)['payload']

        received_user_name = data['user_name']
        self.assertEqual(received_user_name, self.user['musicbrainz_id'])

        received_count = data['count']
        self.assertEqual(received_count, 25)

        received_total_count = data['total_recording_mbids_count']
        expected_total_count = len(self.user_recommendations['recording_mbid']['top_artist'])

        received_ts = data['last_updated']
        expected_ts = int(self.user_recommendations['created'].timestamp())
        self.assertEqual(received_ts, expected_ts)

        received_top_artist_recommendations = data['top_artist']['recording_mbid']
        expected_top_artist_recommendations = self.user_recommendations['recording_mbid']['top_artist'][:25]
        self.assertEqual(expected_top_artist_recommendations, received_top_artist_recommendations)

    def test_recommendations_with_count(self):
        response = self.client.get(url_for('recommendations_cf_recording_v1.get_recommendations',
                                           user_name=self.user2['musicbrainz_id']), query_string={'type': 'similar', 'count': 10})
        self.assert200(response)
        data = json.loads(response.data)['payload']

        received_user_name = data['user_name']
        self.assertEqual(received_user_name, self.user2['musicbrainz_id'])

        received_count = data['count']
        self.assertEqual(received_count, 10)

        received_total_count = data['total_recording_mbids_count']
        expected_total_count = len(self.user_recommendations['recording_mbid']['similar_artist'])

        received_ts = data['last_updated']
        expected_ts = int(self.user2_recommendations['created'].timestamp())
        self.assertEqual(received_ts, expected_ts)

        received_top_artist_recommendations = data['similar_artist']['recording_mbid']
        expected_top_artist_recommendations = self.user2_recommendations['recording_mbid']['similar_artist'][:10]
        self.assertEqual(expected_top_artist_recommendations, received_top_artist_recommendations)

    def test_recommendations_too_many(self):
        response = self.client.get(url_for('recommendations_cf_recording_v1.get_recommendations',
                                           user_name=self.user2['musicbrainz_id']), query_string={'type': 'similar', 'count': 108})
        self.assert200(response)
        data = json.loads(response.data)['payload']

        received_user_name = data['user_name']
        self.assertEqual(received_user_name, self.user2['musicbrainz_id'])

        received_count = data['count']
        self.assertEqual(received_count, 100)

        received_total_count = data['total_recording_mbids_count']
        expected_total_count = len(self.user_recommendations['recording_mbid']['similar_artist'])

        received_ts = data['last_updated']
        expected_ts = int(self.user2_recommendations['created'].timestamp())
        self.assertEqual(received_ts, expected_ts)

        received_top_artist_recommendations = data['similar_artist']['recording_mbid']
        expected_top_artist_recommendations = self.user2_recommendations['recording_mbid']['similar_artist'][:100]
        self.assertEqual(expected_top_artist_recommendations, received_top_artist_recommendations)
