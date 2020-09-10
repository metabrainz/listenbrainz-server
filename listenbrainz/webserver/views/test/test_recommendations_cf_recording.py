import json
import listenbrainz.db.user as db_user

from flask import url_for
from unittest.mock import patch
from flask import render_template
from listenbrainz.db.testing import DatabaseTestCase
from listenbrainz.webserver.views.user import _get_user
from flask_login import current_user
from listenbrainz.webserver.testing import ServerTestCase
from listenbrainz.webserver.views import recommendations_cf_recording
import listenbrainz.db.recommendations_cf_recording as db_recommendations_cf_recording


class CFRecommendationsViewsTestCase(ServerTestCase, DatabaseTestCase):
    def setUp(self):
        ServerTestCase.setUp(self)
        DatabaseTestCase.setUp(self)
        self.user = db_user.get_or_create(1, 'vansika')
        db_user.agree_to_gdpr(self.user['musicbrainz_id'])
        self.user2 = db_user.get_or_create(2, 'vansika_1')
        self.user3 = db_user.get_or_create(3, 'vansika_2')

        # insert recommendations
        with open(self.path_to_data_file('cf_recommendations_db_data_for_api_test_recording.json'), 'r') as f:
            self.payload = json.load(f)

        db_recommendations_cf_recording.insert_user_recommendation(2, self.payload['recording_mbid'], [])
        db_recommendations_cf_recording.insert_user_recommendation(3, [], self.payload['recording_mbid'])

    def tearDown(self):
        ServerTestCase.tearDown(self)
        DatabaseTestCase.tearDown(self)

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
            "recommendations_cf_recording/top_artist.html",
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
            "recommendations_cf_recording/similar_artist.html",
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
        self.assertTemplateUsed('recommendations_cf_recording/top_artist.html')
        self.assert_context('active_section', 'top_artist')
        self.assert_context('user', user)
        error_msg="Recommended tracks for the user have not been calculated. Check back later."
        self.assert_context('error_msg', error_msg)

        user = _get_user('vansika')
        recommendations_cf_recording._get_template(active_section='similar_artist', user=user)
        self.assertTemplateUsed('recommendations_cf_recording/similar_artist.html')
        self.assert_context('active_section', 'similar_artist')
        self.assert_context('user', user)
        error_msg="Recommended tracks for the user have not been calculated. Check back later."
        self.assert_context('error_msg', error_msg)

    def test_get_template_missing_rec_top_artist(self):
        user = _get_user('vansika_2')
        recommendations_cf_recording._get_template(active_section='top_artist', user=user)
        self.assertTemplateUsed('recommendations_cf_recording/top_artist.html')
        self.assert_context('active_section', 'top_artist')
        self.assert_context('user', user)
        error_msg="Looks like you weren't active last week. Check back later."
        self.assert_context('error_msg', error_msg)

    def test_get_template_missing_rec_top_artist(self):
        user = _get_user('vansika_1')
        recommendations_cf_recording._get_template(active_section='similar_artist', user=user)
        self.assertTemplateUsed('recommendations_cf_recording/similar_artist.html')
        self.assert_context('active_section', 'similar_artist')
        self.assert_context('user', user)
        error_msg="Looks like you weren't active last week. Check back later."
        self.assert_context('error_msg', error_msg)

    @patch('listenbrainz.db.recommendations_cf_recording.get_user_recommendation')
    @patch('listenbrainz.webserver.views.recommendations_cf_recording._get_listens_from_recording_mbid')
    def test_get_template(self, mock_get_listens, mock_get_rec):
        self.temporary_login(self.user['login_id'])
        user = _get_user('vansika_1')

        mock_get_listens.return_value = [{
            'listened_at' : 0,
            'track_metadata' : {
                'artist_name' : "Ultravox",
                'track_name' : "Serenade (special remix)",
                'release_name' : "Quartet",
                'additional_info' : {
                    'recording_mbid' : "af5a56f4-1f83-4681-b319-70a734d0d047",
                    'artist_mbids' : ["6a70b322-9aa9-41b3-9dce-824733633a1c"]
                }
            },
            'score': 0.756
        }]
        recommendations_cf_recording._get_template(active_section='top_artist', user=user)
        mock_get_rec.assert_called_with(user.id)
        mock_get_listens.assert_called_with(mock_get_rec.return_value)
        self.assertTemplateUsed('recommendations_cf_recording/top_artist.html')
