import uuid
from unittest import mock

import orjson
import listenbrainz.db.user as db_user
from datetime import datetime

from unittest.mock import patch
from flask import render_template, url_for

from listenbrainz.tests.integration import NonAPIIntegrationTestCase
from listenbrainz.webserver.login import User
from listenbrainz.webserver.views import recommendations_cf_recording
import listenbrainz.db.recommendations_cf_recording as db_recommendations_cf_recording
from data.model.user_cf_recommendations_recording_message import (UserRecommendationsJson,
                                                                  UserRecommendationsData)


class CFRecommendationsViewsTestCase(NonAPIIntegrationTestCase):
    def setUp(self):
        self.server_url = "https://labs.api.listenbrainz.org/recording-mbid-lookup/json"
        super(CFRecommendationsViewsTestCase, self).setUp()
        self.user = db_user.get_or_create(self.db_conn, 1, 'vansika')
        db_user.agree_to_gdpr(self.db_conn, self.user['musicbrainz_id'])
        self.user2 = db_user.get_or_create(self.db_conn, 2, 'vansika_1')
        self.user3 = db_user.get_or_create(self.db_conn, 3, 'vansika_2')

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
            self.db_conn,
            self.user2["id"],
            UserRecommendationsJson(**{
                'raw': data['recording_mbid']
            })
        )

        db_recommendations_cf_recording.insert_user_recommendation(
            self.db_conn,
            self.user3["id"],
            UserRecommendationsJson(**{
                'raw': [],
            })
        )

    def test_info_invalid_user(self):
        response = self.client.post(url_for('recommendations_cf_recording.info', user_name="invalid"))
        self.assert404(response)

    @patch('listenbrainz.webserver.views.recommendations_cf_recording._get_user')
    def test_info_valid_user(self, mock_user):
        mock_user.return_value = User.from_dbrow(self.user)
        response = self.client.post(url_for('recommendations_cf_recording.info', user_name="vansika"))
        self.assert200(response)
        self.assertEqual(response.json, {
            "user": {
                "id": mock_user.return_value.id,
                "name": 'vansika',
            }
        })

    def test_raw_invalid_user(self):
        response = self.client.post(url_for('recommendations_cf_recording.raw', user_name="invalid"))
        self.assert404(response)

    def test_get_props_missing_user_from_rec_db(self):
        user = User.from_dbrow(self.user)
        props = recommendations_cf_recording._get_props(active_section='raw', user=user)
        self.assertEqual(props['user']['id'], user.id)
        self.assertEqual(props['user']['name'], user.musicbrainz_id)

    def test_get_props_missing_rec_raw(self):
        user = User.from_dbrow(self.user2)
        props = recommendations_cf_recording._get_props(active_section='raw', user=user)
        self.assertEqual(props['user']['id'], user.id)
        self.assertEqual(props['user']['name'], user.musicbrainz_id)

    @patch('listenbrainz.webserver.views.recommendations_cf_recording.db_recommendations_cf_recording.get_user_recommendation')
    @patch('listenbrainz.webserver.views.recommendations_cf_recording._get_playable_recommendations_list')
    def test_get_props_empty_repsonce_raw(self, mock_get_recommendations, mock_get_rec):
        user = User.from_dbrow(self.user2)

        mock_get_rec.return_value = UserRecommendationsData(**{
            'recording_mbid': {
                'raw': [{
                    'recording_mbid': "af5a56f4-1f83-4681-b319-70a734d0d047",
                    'score': 0.4
                }]
            },
            'created': datetime.utcnow(),
            'user_id': self.user["id"]
        })
        mock_get_recommendations.return_value = []

        props = recommendations_cf_recording._get_props(active_section='raw', user=user)
        self.assertEqual(props['user']['id'], user.id)
        self.assertEqual(props['user']['name'], user.musicbrainz_id)
        error_msg = "An error occurred while processing your request. Check back later!"
        self.assertEqual(props['errorMsg'], error_msg)

    @patch('listenbrainz.webserver.views.recommendations_cf_recording.db_recommendations_cf_recording.get_user_recommendation')
    @patch('listenbrainz.webserver.views.recommendations_cf_recording._get_playable_recommendations_list')
    def test_get_props(self, mock_get_recommendations, mock_get_rec):
        # active_section = 'raw'
        user = User.from_dbrow(self.user2)
        created = datetime.utcnow()

        mock_get_rec.return_value = UserRecommendationsData(**{
            'recording_mbid': {
                'raw': [{
                    'recording_mbid': "9f5a56f4-1f83-4681-b319-70a734d0d047",
                    'score': 0.9
                }]
            },
            'created': datetime.utcnow(),
            'user_id': self.user["id"]
        })

        recommendations = [{
            'listened_at': 0,
            'track_metadata': {
                'artist_name': "Ultravox",
                'track_name': "Serenade (special remix)",
                'release_name': "Quartet",
                'additional_info': {
                    'recording_mbid': "af5a56f4-1f83-4681-b319-70a734d0d047",
                    'artist_mbids': ["6a70b322-9aa9-41b3-9dce-824733633a1c"]
                }
            }
        }]
        mock_get_recommendations.return_value = recommendations

        props = recommendations_cf_recording._get_props(active_section='raw', user=user)

        expected_props = {
            "user": {
                "id": self.user2["id"],
                "name": 'vansika_1',
            },
            "recommendations": recommendations,
        }
        self.assertEqual(expected_props['user'], props['user'])
        self.assertEqual(expected_props['recommendations'], props['recommendations'])

    @patch('listenbrainz.webserver.views.recommendations_cf_recording.load_recordings_from_mbids')
    def test_get_playable_recommendations_list(self, mock_load):
        mbids_and_ratings = [
            {
                'recording_mbid': "03f1b16a-af43-4cd7-b22c-d2991bf011a3",
                'score': 6.88,
                'latest_listened_at': "2021-12-17T05:32:11.000Z"
            },
            {
                'recording_mbid': "2c8412f0-9353-48a2-aedb-1ad8dac9498f",
                'score': 9.0,
                'latest_listened_at': "2022-10-13T15:12:23.000Z"
            }
        ]

        mock_load.return_value = {
            "03f1b16a-af43-4cd7-b22c-d2991bf011a3": {
                "artist_mbids": ["63aa26c3-d59b-4da4-84ac-716b54f1ef4d"],
                "artist_credit_id": 571280,
                "release_mbid": "5da4af04-d796-4d07-801d-a878e83dea48",
                "release": "Random Is Resistance",
                "recording_mbid": "03f1b16a-af43-4cd7-b22c-d2991bf011a3",
                "artist": "Rotersand",
                "title": "One More Hour",
                "caa_id": 25414187159,
                "caa_release_mbid": "c51e3d19-8080-4faa-9f5d-3e8714343543"
            },
            "2c8412f0-9353-48a2-aedb-1ad8dac9498f": {
                "artist_mbids": ["63aa26c3-d59b-4da4-84ac-716b54f1ef4d"],
                "artist_credit_id": 571280,
                "artist": "Tame Impala",
                "release_mbid": "27280632-fa33-3801-a5b1-081ed0b65bb3",
                "release": "Year Zero",
                "recording_mbid": "2c8412f0-9353-48a2-aedb-1ad8dac9498f",
                "title": "Sun’s Coming Up",
                "caa_id": 33734215643,
                "caa_release_mbid": "169d9fb9-bc65-423b-9c44-2d177a329b48"
            }
        }

        received_recommendations = recommendations_cf_recording._get_playable_recommendations_list(mbids_and_ratings)
        mock_load.assert_called_with(
            mock.ANY,
            ["03f1b16a-af43-4cd7-b22c-d2991bf011a3", "2c8412f0-9353-48a2-aedb-1ad8dac9498f"]
        )

        expected_recommendations = [
            {
                'listened_at_iso': "2021-12-17T05:32:11.000Z",
                'track_metadata': {
                    'artist_name': 'Rotersand',
                    'track_name': 'One More Hour',
                    'release_name': 'Random Is Resistance',
                    'additional_info': {
                        'recording_mbid': '03f1b16a-af43-4cd7-b22c-d2991bf011a3',
                        'artist_mbids': ['63aa26c3-d59b-4da4-84ac-716b54f1ef4d'],
                        'release_mbid' : '5da4af04-d796-4d07-801d-a878e83dea48',
                        'caa_id' : 25414187159,
                        'caa_release_mbid' : 'c51e3d19-8080-4faa-9f5d-3e8714343543'
                    }
                }
            },
            {
                'listened_at_iso': "2022-10-13T15:12:23.000Z",
                'track_metadata': {
                    'artist_name': 'Tame Impala',
                    'track_name': 'Sun’s Coming Up',
                    'release_name': 'Year Zero',
                    'additional_info': {
                            'recording_mbid': '2c8412f0-9353-48a2-aedb-1ad8dac9498f',
                            'artist_mbids': ['63aa26c3-d59b-4da4-84ac-716b54f1ef4d'],
                            'release_mbid' : '27280632-fa33-3801-a5b1-081ed0b65bb3',
                            'caa_id' : 33734215643,
                            'caa_release_mbid' : '169d9fb9-bc65-423b-9c44-2d177a329b48'
                    }
                }
            }
        ]
        self.assertEqual(expected_recommendations, received_recommendations)
