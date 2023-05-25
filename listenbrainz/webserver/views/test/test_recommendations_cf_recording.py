import uuid
from unittest import mock

import orjson
import listenbrainz.db.user as db_user
from datetime import datetime

from flask import url_for
from unittest.mock import patch
from flask import render_template, current_app
from listenbrainz.tests.integration import IntegrationTestCase
from listenbrainz.webserver.views.user import _get_user
from werkzeug.exceptions import BadRequest, InternalServerError
from listenbrainz.webserver.views import recommendations_cf_recording
import listenbrainz.db.recommendations_cf_recording as db_recommendations_cf_recording
from data.model.user_cf_recommendations_recording_message import (UserRecommendationsJson,
                                                                  UserRecommendationsData)


class CFRecommendationsViewsTestCase(IntegrationTestCase):
    def setUp(self):
        self.server_url = "https://labs.api.listenbrainz.org/recording-mbid-lookup/json"
        super(CFRecommendationsViewsTestCase, self).setUp()
        self.user = db_user.get_or_create(1, 'vansika')
        db_user.agree_to_gdpr(self.user['musicbrainz_id'])
        self.user2 = db_user.get_or_create(2, 'vansika_1')
        self.user3 = db_user.get_or_create(3, 'vansika_2')

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
            self.user2["id"],
            UserRecommendationsJson(**{
                'top_artist': data['recording_mbid'],
                'similar_artist': []
            })
        )

        db_recommendations_cf_recording.insert_user_recommendation(
            self.user3["id"],
            UserRecommendationsJson(**{
                'top_artist': [],
                'similar_artist': data['recording_mbid']
            })
        )

    def test_info_invalid_user(self):
        response = self.client.get(url_for('recommendations_cf_recording.info', user_name="invalid"))
        self.assert404(response)

    @patch('listenbrainz.webserver.views.recommendations_cf_recording._get_user')
    def test_info_valid_user(self, mock_user):
        response = self.client.get(url_for('recommendations_cf_recording.info', user_name="vansika"))
        self.assert200(response)
        self.assertTemplateUsed('recommendations_cf_recording/info.html')
        self.assert_context('active_section', 'info')
        self.assert_context('user', mock_user.return_value)
        mock_user.assert_called_with("vansika")

    def test_top_artist_invalid_user(self):
        response = self.client.get(url_for('recommendations_cf_recording.top_artist', user_name="invalid"))
        self.assert404(response)

    @patch('listenbrainz.webserver.views.recommendations_cf_recording._get_user')
    @patch('listenbrainz.webserver.views.recommendations_cf_recording._get_template')
    def test_top_artist_valid_user(self, mock_template, mock_user):
        # Flask essentially needs render_template to generate a response
        # this is a fake repsonse to check _get_template wa called with desired params.
        mock_template.return_value = render_template(
            "recommendations_cf_recording/base.html",
            active_section='top_artist',
            user=self.user,
            error_msg="test"
        )
        response = self.client.get(url_for('recommendations_cf_recording.top_artist', user_name="vansika"))
        self.assert200(response)
        mock_user.assert_called_with("vansika")
        mock_template.assert_called_with(active_section='top_artist', user=mock_user.return_value)

    def test_similar_artist_invalid_user(self):
        response = self.client.get(url_for('recommendations_cf_recording.top_artist', user_name="invalid"))
        self.assert404(response)

    @patch('listenbrainz.webserver.views.recommendations_cf_recording._get_user')
    @patch('listenbrainz.webserver.views.recommendations_cf_recording._get_template')
    def test_similar_artist_valid_user(self, mock_template, mock_user):
        # Flask essentially needs render_template to generate a response
        # this is a fake repsonse to check _get_template wa called with desired params.
        mock_template.return_value = render_template(
            "recommendations_cf_recording/base.html",
            active_section='similar_artist',
            user=self.user,
            error_msg="test"
        )
        response = self.client.get(url_for('recommendations_cf_recording.similar_artist', user_name="vansika"))
        self.assert200(response)
        mock_user.assert_called_with("vansika")
        mock_template.assert_called_with(active_section='similar_artist', user=mock_user.return_value)

    def test_get_template_missing_user_from_rec_db(self):
        user = _get_user('vansika')
        recommendations_cf_recording._get_template(active_section='top_artist', user=user)
        self.assertTemplateUsed('recommendations_cf_recording/base.html')
        self.assert_context('active_section', 'top_artist')
        self.assert_context('user', user)

        user = _get_user('vansika')
        recommendations_cf_recording._get_template(active_section='similar_artist', user=user)
        self.assertTemplateUsed('recommendations_cf_recording/base.html')
        self.assert_context('active_section', 'similar_artist')
        self.assert_context('user', user)

    def test_get_template_missing_rec_top_artist(self):
        user = _get_user('vansika_2')
        recommendations_cf_recording._get_template(active_section='top_artist', user=user)
        self.assertTemplateUsed('recommendations_cf_recording/base.html')
        self.assert_context('active_section', 'top_artist')
        self.assert_context('user', user)

    def test_get_template_missing_rec_similar_artist(self):
        user = _get_user('vansika_1')
        recommendations_cf_recording._get_template(active_section='similar_artist', user=user)
        self.assertTemplateUsed('recommendations_cf_recording/base.html')
        self.assert_context('active_section', 'similar_artist')
        self.assert_context('user', user)

    @patch('listenbrainz.webserver.views.recommendations_cf_recording.db_recommendations_cf_recording.get_user_recommendation')
    @patch('listenbrainz.webserver.views.recommendations_cf_recording._get_playable_recommendations_list')
    def test_get_template_empty_repsonce_top_artist(self, mock_get_recommendations, mock_get_rec):
        user = _get_user('vansika_1')

        mock_get_rec.return_value = UserRecommendationsData(**{
            'recording_mbid': {
                'top_artist': [{
                    'recording_mbid': "af5a56f4-1f83-4681-b319-70a734d0d047",
                    'score': 0.4
                }]
            },
            'created': datetime.utcnow(),
            'user_id': self.user["id"]
        })
        mock_get_recommendations.return_value = []

        recommendations_cf_recording._get_template(active_section='top_artist', user=user)
        self.assertTemplateUsed('recommendations_cf_recording/base.html')
        self.assert_context('active_section', 'top_artist')
        self.assert_context('user', user)
        error_msg = "An error occurred while processing your request. Check back later!"
        self.assert_context('error_msg', error_msg)

    @patch('listenbrainz.webserver.views.recommendations_cf_recording.db_recommendations_cf_recording.get_user_recommendation')
    @patch('listenbrainz.webserver.views.recommendations_cf_recording._get_playable_recommendations_list')
    def test_get_template_empty_repsonce_similar_artist(self, mock_get_recommendations, mock_get_rec):
        user = _get_user('vansika_1')

        mock_get_rec.return_value = UserRecommendationsData(**{
            'recording_mbid': {
                'similar_artist': [{
                    'recording_mbid': "9f5a56f4-1f83-4681-b319-70a734d0d047",
                    'score': 0.9
                }]
            },
            'created': datetime.utcnow(),
            'user_id': self.user["id"]
        })
        mock_get_recommendations.return_value = []

        recommendations_cf_recording._get_template(active_section='similar_artist', user=user)
        self.assertTemplateUsed('recommendations_cf_recording/base.html')
        self.assert_context('active_section', 'similar_artist')
        self.assert_context('user', user)
        error_msg = "An error occurred while processing your request. Check back later!"
        self.assert_context('error_msg', error_msg)

    @patch('listenbrainz.webserver.views.recommendations_cf_recording.db_recommendations_cf_recording.get_user_recommendation')
    @patch('listenbrainz.webserver.views.recommendations_cf_recording._get_playable_recommendations_list')
    def test_get_template(self, mock_get_recommendations, mock_get_rec):
        # active_section = 'top_artist'
        user = _get_user('vansika_1')
        created = datetime.utcnow()

        mock_get_rec.return_value = UserRecommendationsData(**{
            'recording_mbid': {
                'top_artist': [{
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

        recommendations_cf_recording._get_template(active_section='top_artist', user=user)
        mock_get_rec.assert_called_with(user.id)
        mock_get_recommendations.assert_called_once()
        self.assertTemplateUsed('recommendations_cf_recording/base.html')
        self.assert_context('active_section', 'top_artist')
        self.assert_context('user', user)
        self.assert_context('last_updated', created.strftime('%d %b %Y'))

        expected_props = {
            "user": {
                "id": self.user2["id"],
                "name": 'vansika_1',
            },
            "recommendations": recommendations,
        }
        received_props = orjson.loads(self.get_context_variable('props'))
        self.assertEqual(expected_props, received_props)

        # only assert fields that should change with 'active_section'
        # here active_section = 'similar_artist'
        mock_get_rec.return_value = UserRecommendationsData(**{
            'recording_mbid': {
                'similar_artist': [{
                    'recording_mbid': "9f5a56f4-1f83-4681-b319-70a734d0d047",
                    'score': 0.9
                }]
            },
            'created': datetime.utcnow(),
            'user_id': self.user["id"]
        })

        recommendations_cf_recording._get_template(active_section='similar_artist', user=user)
        self.assertTemplateUsed('recommendations_cf_recording/base.html')
        self.assert_context('active_section', 'similar_artist')
        received_props = orjson.loads(self.get_context_variable('props'))
        self.assertEqual(expected_props, received_props)

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
