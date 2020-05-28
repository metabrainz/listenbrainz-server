import json

from flask import url_for

import listenbrainz.db.feedback as db_feedback
import listenbrainz.db.user as db_user
from listenbrainz.tests.integration import IntegrationTestCase


class FeedbackAPITestCase(IntegrationTestCase):
    def setUp(self):
        super(FeedbackAPITestCase, self).setUp()
        self.user = db_user.get_or_create(1, 'testuserpleaseignore')

    def insert_test_data(user_id):
    def test_recording_feedback(self):
        """ Test for submission of valid feedback """
        feedback = {
            "recording_msid": "7babc9be-ca2b-4544-b932-7c9ab38770d6",
            "score": 1
        }

        response = self.client.post(
            url_for('feedback_api_v1.recording_feedback'),
            data=json.dumps(feedback),
            headers={'Authorization': 'Token {}'.format(self.user['auth_token'])},
            content_type='application/json'
        )
        self.assert200(response)
        self.assertEqual(response.json['status'], 'ok')

    def test_recording_feedback_unauthorised_submission(self):
        """ Test for checking that unauthorized submissions return 401 """
        feedback = {
            "recording_msid": "7babc9be-ca2b-4544-b932-7c9ab38770d6",
            "score": 1
        }

        # request with no authorization header
        response = self.client.post(
            url_for('feedback_api_v1.recording_feedback'),
            data=json.dumps(feedback),
            content_type='application/json'
        )
        self.assert401(response)
        self.assertEqual(response.json["code"], 401)

        # request with invalid authorization header
        response = self.client.post(
            url_for('feedback_api_v1.recording_feedback'),
            data=json.dumps(feedback),
            headers={'Authorization': 'Token testtokenplsignore'},
            content_type='application/json'
        )
        self.assert401(response)
        self.assertEqual(response.json["code"], 401)

    def test_recording_feedback_json_with_missing_keys(self):
        """ Test for checking that submitting JSON with missing keys returns 400 """

        # submit a feedback without recording_msid key
        incomplete_feedback = {
            "score": 1
        }

        response = self.client.post(
            url_for('feedback_api_v1.recording_feedback'),
            data=json.dumps(incomplete_feedback),
            headers={'Authorization': 'Token {}'.format(self.user['auth_token'])},
            content_type='application/json'
        )
        self.assert400(response)
        self.assertEqual(response.json["error"], "JSON document must contain recording_msid and "
                         "score top level keys")

        # submit a feedback without score key
        incomplete_feedback = {
            "recording_msid": "7babc9be-ca2b-4544-b932-7c9ab38770d6",
        }

        response = self.client.post(
            url_for('feedback_api_v1.recording_feedback'),
            data=json.dumps(incomplete_feedback),
            headers={'Authorization': 'Token {}'.format(self.user['auth_token'])},
            content_type='application/json'
        )
        self.assert400(response)
        self.assertEqual(response.json["error"], "JSON document must contain recording_msid and "
                         "score top level keys")

        # submit an empty feedback
        empty_feedback = {}

        response = self.client.post(
            url_for('feedback_api_v1.recording_feedback'),
            data=json.dumps(empty_feedback),
            headers={'Authorization': 'Token {}'.format(self.user['auth_token'])},
            content_type='application/json'
        )
        self.assert400(response)
        self.assertEqual(response.json["error"], "JSON document must contain recording_msid and "
                         "score top level keys")

    def test_recording_feedback_json_with_extra_keys(self):
        """ Test to check submitting JSON with extra keys returns 400 """
        invalid_feedback = {
            "recording_msid": "7babc9be-ca2b-4544-b932-7c9ab38770d6",
            "score": 1,
            "extra_key": "testvalueplsignore"
        }

        response = self.client.post(
            url_for('feedback_api_v1.recording_feedback'),
            data=json.dumps(invalid_feedback),
            headers={'Authorization': 'Token {}'.format(self.user['auth_token'])},
            content_type='application/json'
        )
        self.assert400(response)
        self.assertEqual(response.json["error"], "JSON document may only contain recording_msid and "
                         "score top level keys")

    def test_recording_feedback_invalid_values(self):
        """ Test to check submitting invalid values in JSON returns 400 """

        # submit feedback with invalid recording_msid
        invalid_feedback = {
            "recording_msid": "invalid_recording_msid",
            "score": 1
        }

        response = self.client.post(
            url_for('feedback_api_v1.recording_feedback'),
            data=json.dumps(invalid_feedback),
            headers={'Authorization': 'Token {}'.format(self.user['auth_token'])},
            content_type='application/json'
        )
        self.assert400(response)
        self.assertEqual(response.json["code"], 400)

        # submit feedback with invalid score
        invalid_feedback = {
            "recording_msid": "7babc9be-ca2b-4544-b932-7c9ab38770d6",
            "score": 5
        }

        response = self.client.post(
            url_for('feedback_api_v1.recording_feedback'),
            data=json.dumps(invalid_feedback),
            headers={'Authorization': 'Token {}'.format(self.user['auth_token'])},
            content_type='application/json'
        )
        self.assert400(response)
        self.assertEqual(response.json["code"], 400)

        # submit feedback with invalid recording_msid and score
        invalid_feedback = {
            "recording_msid": "invalid_recording_msid",
            "score": 5
        }

        response = self.client.post(
            url_for('feedback_api_v1.recording_feedback'),
            data=json.dumps(invalid_feedback),
            headers={'Authorization': 'Token {}'.format(self.user['auth_token'])},
            content_type='application/json'
        )
        self.assert400(response)
        self.assertEqual(response.json["code"], 400)

    def test_recording_feedback_update_score(self):
        """ 
        Test to check that score gets updated when a user changes feedback score for a recording_msid
        i.e love to hate or vice-versa
        """

        # submit a feedback with score = 1
        feedback = {
            "recording_msid": "7babc9be-ca2b-4544-b932-7c9ab38770d6",
            "score": 1
        }

        response = self.client.post(
            url_for('feedback_api_v1.recording_feedback'),
            data=json.dumps(feedback),
            headers={'Authorization': 'Token {}'.format(self.user['auth_token'])},
            content_type='application/json'
        )
        self.assert200(response)
        self.assertEqual(response.json["status"], "ok")

        result = db_feedback.get_feedback_by_user_id(self.user["id"])
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].user_id, self.user["id"])
        self.assertEqual(result[0].recording_msid, feedback["recording_msid"])
        self.assertEqual(result[0].score, feedback["score"])

        # submit an updated feedback for the same recording_msid with new score = -1
        updated_feedback = {
            "recording_msid": "7babc9be-ca2b-4544-b932-7c9ab38770d6",
            "score": -1
        }

        response = self.client.post(
            url_for('feedback_api_v1.recording_feedback'),
            data=json.dumps(updated_feedback),
            headers={'Authorization': 'Token {}'.format(self.user['auth_token'])},
            content_type='application/json'
        )
        self.assert200(response)
        self.assertEqual(response.json["status"], "ok")

        # check that the record gets updated
        result = db_feedback.get_feedback_by_user_id(self.user["id"])
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].user_id, self.user["id"])
        self.assertEqual(result[0].recording_msid, updated_feedback["recording_msid"])
        self.assertEqual(result[0].score, updated_feedback["score"])

    def test_recording_feedback_delete_when_score_is_zero(self):
        """ 
        Test to check that the feedback record gets deleted when a user removes feedback for a recording_msid
        by submitting a score = 0
        """

        # submit a feedback with score = 1
        feedback = {
            "recording_msid": "7babc9be-ca2b-4544-b932-7c9ab38770d6",
            "score": 1
        }

        response = self.client.post(
            url_for('feedback_api_v1.recording_feedback'),
            data=json.dumps(feedback),
            headers={'Authorization': 'Token {}'.format(self.user['auth_token'])},
            content_type='application/json'
        )
        self.assert200(response)
        self.assertEqual(response.json["status"], "ok")

        result = db_feedback.get_feedback_by_user_id(self.user["id"])
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].user_id, self.user["id"])
        self.assertEqual(result[0].recording_msid, feedback["recording_msid"])
        self.assertEqual(result[0].score, feedback["score"])

        # submit an updated feedback for the same recording_msid with new score = 0
        updated_feedback = {
            "recording_msid": "7babc9be-ca2b-4544-b932-7c9ab38770d6",
            "score": 0
        }

        response = self.client.post(
            url_for('feedback_api_v1.recording_feedback'),
            data=json.dumps(updated_feedback),
            headers={'Authorization': 'Token {}'.format(self.user['auth_token'])},
            content_type='application/json'
        )
        self.assert200(response)
        self.assertEqual(response.json["status"], "ok")

        # check that the record gets deleted
        result = db_feedback.get_feedback_by_user_id(self.user["id"])
        self.assertEqual(len(result), 0)