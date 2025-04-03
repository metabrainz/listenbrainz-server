import json
from unittest import mock

import requests_mock

import listenbrainz.db.feedback as db_feedback
import listenbrainz.db.user as db_user
from listenbrainz import messybrainz
from listenbrainz.db import timescale
from listenbrainz.db.model.feedback import Feedback
from listenbrainz.tests.integration import IntegrationTestCase


class FeedbackAPITestCase(IntegrationTestCase):
    def setUp(self):
        super(FeedbackAPITestCase, self).setUp()
        self.user = db_user.get_or_create(self.db_conn, 1, "testuserpleaseignore")
        self.user2 = db_user.get_or_create(self.db_conn, 2, "anothertestuserpleaseignore")
        self.ts_conn = timescale.engine.connect()

    def tearDown(self):
        self.ts_conn.close()
        super(FeedbackAPITestCase, self).tearDown()

    def insert_test_data(self, user_id):
        sample_feedback = [
            {
                "recording_msid": "d23f4719-9212-49f0-ad08-ddbfbfc50d6f",
                "score": 1
            },
            {
                "recording_msid": "222eb00d-9ead-42de-aec9-8f8c1509413d",
                "score": -1
            }
        ]
        for fb in sample_feedback:
            db_feedback.insert(
                self.db_conn,
                Feedback(
                    user_id=user_id,
                    recording_msid=fb["recording_msid"],
                    score=fb["score"]
                )
            )

        return sample_feedback

    def insert_test_data_with_mbid(self, user_id):
        sample_feedback = [
            {
                "recording_msid": "d23f4719-9212-49f0-ad08-ddbfbfc50d6f",
                "score": 1
            },
            {
                "recording_msid": "222eb00d-9ead-42de-aec9-8f8c1509413d",
                "score": -1
            },
            {
                "recording_mbid": "076255b4-1575-11ec-ac84-135bf6a670e3",
                "score": 1
            },
            {
                "recording_mbid": "1fd178b4-1575-11ec-b98a-d72392cd8c97",
                "score": -1
            }
        ]
        for fb in sample_feedback:
            db_feedback.insert(
                self.db_conn,
                Feedback(
                    user_id=user_id,
                    recording_msid=fb.get("recording_msid"),
                    recording_mbid=fb.get("recording_mbid"),
                    score=fb["score"]
                )
            )
        return sample_feedback

    def test_recording_feedback(self):
        """ Test for submission of valid feedback """
        feedback = {
            "recording_msid": "7babc9be-ca2b-4544-b932-7c9ab38770d6",
            "score": 1
        }
        response = self.client.post(
            self.custom_url_for("feedback_api_v1.recording_feedback"),
            data=json.dumps(feedback),
            headers={"Authorization": "Token {}".format(self.user["auth_token"])},
            content_type="application/json"
        )
        self.assert200(response)
        self.assertEqual(response.json["status"], "ok")

        feedback = {
            "recording_mbid": "e7ebbb99-7346-4323-9541-dffae9e1003b",
            "score": -1
        }
        response = self.client.post(
            self.custom_url_for("feedback_api_v1.recording_feedback"),
            data=json.dumps(feedback),
            headers={"Authorization": "Token {}".format(self.user["auth_token"])},
            content_type="application/json"
        )
        self.assert200(response)
        self.assertEqual(response.json["status"], "ok")

        feedback = {
            "recording_mbid": "9d008211-c920-4ff7-a17f-b86e4246c58c",
            "recording_msid": "9541592c-0102-4b94-93cc-ee0f3cf83d64",
            "score": -1
        }
        response = self.client.post(
            self.custom_url_for("feedback_api_v1.recording_feedback"),
            data=json.dumps(feedback),
            headers={"Authorization": "Token {}".format(self.user["auth_token"])},
            content_type="application/json"
        )
        self.assert200(response)
        self.assertEqual(response.json["status"], "ok")

    def test_recording_feedback_unauthorised_submission(self):
        """ Test for checking that unauthorized submissions return 401 """
        feedback = {
            "recording_msid": "7babc9be-ca2b-4544-b932-7c9ab38770d6",
            "score": 1
        }

        # request with no authorization header
        response = self.client.post(
            self.custom_url_for("feedback_api_v1.recording_feedback"),
            data=json.dumps(feedback),
            content_type="application/json"
        )
        self.assert401(response)
        self.assertEqual(response.json["code"], 401)

        # request with invalid authorization header
        response = self.client.post(
            self.custom_url_for("feedback_api_v1.recording_feedback"),
            data=json.dumps(feedback),
            headers={"Authorization": "Token testtokenplsignore"},
            content_type="application/json"
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
            self.custom_url_for("feedback_api_v1.recording_feedback"),
            data=json.dumps(incomplete_feedback),
            headers={"Authorization": "Token {}".format(self.user["auth_token"])},
            content_type="application/json"
        )
        self.assert400(response)
        self.assertEqual(
            response.json["error"],
            "JSON document must contain either recording_msid or recording_mbid, and score top level keys"
        )

        # submit a feedback without score key
        incomplete_feedback = {
            "recording_msid": "7babc9be-ca2b-4544-b932-7c9ab38770d6",
        }

        response = self.client.post(
            self.custom_url_for("feedback_api_v1.recording_feedback"),
            data=json.dumps(incomplete_feedback),
            headers={"Authorization": "Token {}".format(self.user["auth_token"])},
            content_type="application/json"
        )
        self.assert400(response)
        self.assertEqual(
            response.json["error"],
            "JSON document must contain either recording_msid or recording_mbid, and score top level keys")

        # submit an empty feedback
        empty_feedback = {}

        response = self.client.post(
            self.custom_url_for("feedback_api_v1.recording_feedback"),
            data=json.dumps(empty_feedback),
            headers={"Authorization": "Token {}".format(self.user["auth_token"])},
            content_type="application/json"
        )
        self.assert400(response)
        self.assertEqual(
            response.json["error"],
            "JSON document must contain either recording_msid or recording_mbid, and score top level keys"
        )

    def test_recording_feedback_json_with_extra_keys(self):
        """ Test to check submitting JSON with extra keys returns 400 """
        invalid_feedback = {
            "recording_msid": "7babc9be-ca2b-4544-b932-7c9ab38770d6",
            "score": 1,
            "extra_key": "testvalueplsignore"
        }

        response = self.client.post(
            self.custom_url_for("feedback_api_v1.recording_feedback"),
            data=json.dumps(invalid_feedback),
            headers={"Authorization": "Token {}".format(self.user["auth_token"])},
            content_type="application/json"
        )
        self.assert400(response)
        self.assertEqual(
            response.json["error"],
            "JSON document may only contain recording_msid, recording_mbid and score top level keys"
        )

    def test_recording_feedback_invalid_values(self):
        """ Test to check submitting invalid values in JSON returns 400 """

        # submit feedback with invalid recording_msid
        invalid_feedback = {
            "recording_msid": "invalid_recording_msid",
            "score": 1
        }
        response = self.client.post(
            self.custom_url_for("feedback_api_v1.recording_feedback"),
            data=json.dumps(invalid_feedback),
            headers={"Authorization": "Token {}".format(self.user["auth_token"])},
            content_type="application/json"
        )
        self.assert400(response)
        self.assertEqual(response.json["code"], 400)

        # submit feedback with invalid recording_mbid
        invalid_feedback = {
            "recording_mbid": "invalid_recording_mbid",
            "score": 1
        }
        response = self.client.post(
            self.custom_url_for("feedback_api_v1.recording_feedback"),
            data=json.dumps(invalid_feedback),
            headers={"Authorization": "Token {}".format(self.user["auth_token"])},
            content_type="application/json"
        )
        self.assert400(response)
        self.assertEqual(response.json["code"], 400)

        # submit feedback with invalid score
        invalid_feedback = {
            "recording_msid": "7babc9be-ca2b-4544-b932-7c9ab38770d6",
            "score": 5
        }
        response = self.client.post(
            self.custom_url_for("feedback_api_v1.recording_feedback"),
            data=json.dumps(invalid_feedback),
            headers={"Authorization": "Token {}".format(self.user["auth_token"])},
            content_type="application/json"
        )
        self.assert400(response)
        self.assertEqual(response.json["code"], 400)

        # submit feedback with invalid recording_msid and score
        invalid_feedback = {
            "recording_msid": "invalid_recording_msid",
            "score": 5
        }

        response = self.client.post(
            self.custom_url_for("feedback_api_v1.recording_feedback"),
            data=json.dumps(invalid_feedback),
            headers={"Authorization": "Token {}".format(self.user["auth_token"])},
            content_type="application/json"
        )
        self.assert400(response)
        self.assertEqual(response.json["code"], 400)

    def test_recording_msid_feedback_update_score(self):
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
            self.custom_url_for("feedback_api_v1.recording_feedback"),
            data=json.dumps(feedback),
            headers={"Authorization": "Token {}".format(self.user["auth_token"])},
            content_type="application/json"
        )
        self.assert200(response)
        self.assertEqual(response.json["status"], "ok")

        result = db_feedback.get_feedback_for_user(self.db_conn, self.ts_conn,  self.user["id"], limit=25, offset=0)
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
            self.custom_url_for("feedback_api_v1.recording_feedback"),
            data=json.dumps(updated_feedback),
            headers={"Authorization": "Token {}".format(self.user["auth_token"])},
            content_type="application/json"
        )
        self.assert200(response)
        self.assertEqual(response.json["status"], "ok")

        # check that the record gets updated
        result = db_feedback.get_feedback_for_user(self.db_conn, self.ts_conn,  self.user["id"], limit=25, offset=0)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].user_id, self.user["id"])
        self.assertEqual(result[0].recording_msid, updated_feedback["recording_msid"])
        self.assertEqual(result[0].score, updated_feedback["score"])

    def test_recording_mbid_feedback_update_score(self):
        """
        Test to check that score gets updated when a user changes feedback score for a recording_mbid
        i.e love to hate or vice-versa
        """

        # submit a feedback with score = 1
        feedback = {
            "recording_mbid": "076255b4-1575-11ec-ac84-135bf6a670e3",
            "score": 1
        }

        response = self.client.post(
            self.custom_url_for("feedback_api_v1.recording_feedback"),
            data=json.dumps(feedback),
            headers={"Authorization": "Token {}".format(self.user["auth_token"])},
            content_type="application/json"
        )
        self.assert200(response)
        self.assertEqual(response.json["status"], "ok")

        result = db_feedback.get_feedback_for_user(self.db_conn, self.ts_conn,  self.user["id"], limit=25, offset=0)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].user_id, self.user["id"])
        self.assertEqual(result[0].recording_mbid, feedback["recording_mbid"])
        self.assertEqual(result[0].score, feedback["score"])

        # submit an updated feedback for the same recording_mbid with new score = -1
        updated_feedback = {
            "recording_mbid": "076255b4-1575-11ec-ac84-135bf6a670e3",
            "score": -1
        }

        response = self.client.post(
            self.custom_url_for("feedback_api_v1.recording_feedback"),
            data=json.dumps(updated_feedback),
            headers={"Authorization": "Token {}".format(self.user["auth_token"])},
            content_type="application/json"
        )
        self.assert200(response)
        self.assertEqual(response.json["status"], "ok")

        # check that the record gets updated
        result = db_feedback.get_feedback_for_user(self.db_conn, self.ts_conn,  self.user["id"], limit=25, offset=0)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].user_id, self.user["id"])
        self.assertEqual(result[0].recording_mbid, updated_feedback["recording_mbid"])
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
            self.custom_url_for("feedback_api_v1.recording_feedback"),
            data=json.dumps(feedback),
            headers={"Authorization": "Token {}".format(self.user["auth_token"])},
            content_type="application/json"
        )
        self.assert200(response)
        self.assertEqual(response.json["status"], "ok")

        result = db_feedback.get_feedback_for_user(self.db_conn, self.ts_conn,  self.user["id"], limit=25, offset=0)
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
            self.custom_url_for("feedback_api_v1.recording_feedback"),
            data=json.dumps(updated_feedback),
            headers={"Authorization": "Token {}".format(self.user["auth_token"])},
            content_type="application/json"
        )
        self.assert200(response)
        self.assertEqual(response.json["status"], "ok")

        # check that the record gets deleted
        result = db_feedback.get_feedback_for_user(self.db_conn, self.ts_conn,  self.user["id"], limit=25, offset=0)
        self.assertEqual(len(result), 0)

    def test_recording_mbid_feedback_delete_when_score_is_zero(self):
        """
        Test to check that the feedback record gets deleted when a user removes feedback for a recording_mbid
        by submitting a score = 0
        """

        # submit a feedback with score = 1
        feedback = {
            "recording_mbid": "076255b4-1575-11ec-ac84-135bf6a670e3",
            "score": 1
        }

        response = self.client.post(
            self.custom_url_for("feedback_api_v1.recording_feedback"),
            data=json.dumps(feedback),
            headers={"Authorization": "Token {}".format(self.user["auth_token"])},
            content_type="application/json"
        )
        self.assert200(response)
        self.assertEqual(response.json["status"], "ok")

        result = db_feedback.get_feedback_for_user(self.db_conn, self.ts_conn,  self.user["id"], limit=25, offset=0)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].user_id, self.user["id"])
        self.assertEqual(result[0].recording_mbid, feedback["recording_mbid"])
        self.assertEqual(result[0].score, feedback["score"])

        # submit an updated feedback for the same recording_mbid with new score = 0
        updated_feedback = {
            "recording_mbid": "076255b4-1575-11ec-ac84-135bf6a670e3",
            "score": 0
        }

        response = self.client.post(
            self.custom_url_for("feedback_api_v1.recording_feedback"),
            data=json.dumps(updated_feedback),
            headers={"Authorization": "Token {}".format(self.user["auth_token"])},
            content_type="application/json"
        )
        self.assert200(response)
        self.assertEqual(response.json["status"], "ok")

        # check that the record gets deleted
        result = db_feedback.get_feedback_for_user(self.db_conn, self.ts_conn,  self.user["id"], limit=25, offset=0)
        self.assertEqual(len(result), 0)

    def test_get_feedback_for_user(self):
        """ Test to make sure valid response is received """
        inserted_rows = self.insert_test_data(self.user["id"])

        response = self.client.get(
            self.custom_url_for("feedback_api_v1.get_feedback_for_user", user_name=self.user["musicbrainz_id"]))
        self.assert200(response)
        data = json.loads(response.data)

        self.assertEqual(data["count"], 2)
        self.assertEqual(data["total_count"], len(inserted_rows))
        self.assertEqual(data["offset"], 0)

        feedback = data["feedback"]  # sorted in descending order of their creation
        self.assertEqual(len(feedback), 2)

        self.assertEqual(feedback[0]["user_id"], self.user["musicbrainz_id"])
        self.assertEqual(feedback[0]["recording_msid"], inserted_rows[1]["recording_msid"])
        self.assertEqual(feedback[0]["score"], inserted_rows[1]["score"])

        self.assertEqual(feedback[1]["user_id"], self.user["musicbrainz_id"])
        self.assertEqual(feedback[1]["recording_msid"], inserted_rows[0]["recording_msid"])
        self.assertEqual(feedback[1]["score"], inserted_rows[0]["score"])

    def test_get_feedback_for_user_invalid_user(self):
        """ Test to make sure that the API sends 404 if user does not exist. """
        response = self.client.get(self.custom_url_for("feedback_api_v1.get_feedback_for_user", user_name="nouser"))
        self.assert404(response)
        self.assertEqual(response.json["error"], "Cannot find user: nouser")

    def test_get_feedback_for_user_with_score_param(self):
        """ Test to make sure valid response is received when score param is passed """
        inserted_rows = self.insert_test_data_with_mbid(self.user["id"])

        # pass score = 1
        response = self.client.get(self.custom_url_for("feedback_api_v1.get_feedback_for_user",
                                                       user_name=self.user["musicbrainz_id"]),
                                   query_string={"score": 1})
        self.assert200(response)
        data = json.loads(response.data)

        self.assertEqual(data["count"], 2)
        self.assertEqual(data["total_count"], 2)  # Only count feedback for this score = 1
        self.assertEqual(data["offset"], 0)

        feedback = data["feedback"]  # sorted in descending order of their creation
        self.assertEqual(len(feedback), 2)

        self.assertEqual(feedback[0]["user_id"], self.user["musicbrainz_id"])
        self.assertEqual(feedback[0]["recording_msid"], None)
        self.assertEqual(feedback[0]["recording_mbid"], inserted_rows[2]["recording_mbid"])
        self.assertEqual(feedback[0]["score"], 1)

        self.assertEqual(feedback[1]["user_id"], self.user["musicbrainz_id"])
        self.assertEqual(feedback[1]["recording_msid"], inserted_rows[0]["recording_msid"])
        self.assertEqual(feedback[1]["recording_mbid"], None)
        self.assertEqual(feedback[1]["score"], 1)

        # pass score = -1
        response = self.client.get(self.custom_url_for("feedback_api_v1.get_feedback_for_user",
                                                       user_name=self.user["musicbrainz_id"]),
                                   query_string={"score": -1})
        self.assert200(response)
        data = json.loads(response.data)

        self.assertEqual(data["count"], 2)
        self.assertEqual(data["total_count"], 2)  # Only count feedback for score = -1
        self.assertEqual(data["offset"], 0)

        feedback = data["feedback"]  # sorted in descending order of their creation
        self.assertEqual(len(feedback), 2)

        self.assertEqual(feedback[0]["user_id"], self.user["musicbrainz_id"])
        self.assertEqual(feedback[0]["recording_msid"], None)
        self.assertEqual(feedback[0]["recording_mbid"], inserted_rows[3]["recording_mbid"])
        self.assertEqual(feedback[0]["score"], -1)

        self.assertEqual(feedback[1]["user_id"], self.user["musicbrainz_id"])
        self.assertEqual(feedback[1]["recording_msid"], inserted_rows[1]["recording_msid"])
        self.assertEqual(feedback[1]["recording_mbid"], None)
        self.assertEqual(feedback[1]["score"], -1)

    def test_get_feedback_for_user_with_invalid_score_param(self):
        """ Test to make sure 400 response is received if score argument is not valid """
        inserted_rows = self.insert_test_data(self.user["id"])

        # pass non-int value to score
        response = self.client.get(self.custom_url_for("feedback_api_v1.get_feedback_for_user",
                                                       user_name=self.user["musicbrainz_id"]),
                                   query_string={"score": "invalid_score"})
        self.assert400(response)
        self.assertEqual(response.json["error"], "Invalid score argument: invalid_score")

        # pass invalid int value to score
        response = self.client.get(self.custom_url_for("feedback_api_v1.get_feedback_for_user",
                                                       user_name=self.user["musicbrainz_id"]),
                                   query_string={"score": 10})
        self.assert400(response)
        self.assertEqual(response.json["error"], "Score can have a value of 1 or -1.")

    def test_get_feedback_for_user_with_count_param(self):
        """ Test to make sure valid response is received when count param is passed """
        inserted_rows = self.insert_test_data_with_mbid(self.user["id"])

        # pass count = 1
        response = self.client.get(self.custom_url_for("feedback_api_v1.get_feedback_for_user",
                                                       user_name=self.user["musicbrainz_id"]),
                                   query_string={"count": 1})
        self.assert200(response)
        data = json.loads(response.data)

        self.assertEqual(data["count"], 1)
        self.assertEqual(data["total_count"], len(inserted_rows))
        self.assertEqual(data["offset"], 0)

        feedback = data["feedback"]  # sorted in descending order of their creation
        self.assertEqual(len(feedback), 1)

        self.assertEqual(feedback[0]["user_id"], self.user["musicbrainz_id"])
        self.assertEqual(feedback[0]["recording_msid"], None)
        self.assertEqual(feedback[0]["recording_mbid"], inserted_rows[3]["recording_mbid"])
        self.assertEqual(feedback[0]["score"], inserted_rows[3]["score"])

    def test_get_feedback_for_user_with_invalid_count_param(self):
        """ Test to make sure 400 response is received if count argument is not valid """
        inserted_rows = self.insert_test_data(self.user["id"])

        # pass non-int value to count
        response = self.client.get(self.custom_url_for("feedback_api_v1.get_feedback_for_user",
                                                       user_name=self.user["musicbrainz_id"]),
                                   query_string={"count": "invalid_count"})
        self.assert400(response)
        self.assertEqual(response.json["error"], "'count' should be a non-negative integer")

        # pass negative int value to count
        response = self.client.get(self.custom_url_for("feedback_api_v1.get_feedback_for_user",
                                                       user_name=self.user["musicbrainz_id"]),
                                   query_string={"count": -1})
        self.assert400(response)
        self.assertEqual(response.json["error"], "'count' should be a non-negative integer")

    def test_get_feedback_for_user_with_offset_param(self):
        """ Test to make sure valid response is received when offset param is passed """
        inserted_rows = self.insert_test_data(self.user["id"])

        # pass count = 1
        response = self.client.get(self.custom_url_for("feedback_api_v1.get_feedback_for_user",
                                                       user_name=self.user["musicbrainz_id"]),
                                   query_string={"offset": 1})
        self.assert200(response)
        data = json.loads(response.data)

        self.assertEqual(data["count"], 1)
        self.assertEqual(data["total_count"], len(inserted_rows))
        self.assertEqual(data["offset"], 1)

        feedback = data["feedback"]  # sorted in descending order of their creation
        self.assertEqual(len(feedback), 1)

        self.assertEqual(feedback[0]["user_id"], self.user["musicbrainz_id"])
        self.assertEqual(feedback[0]["recording_msid"], inserted_rows[0]["recording_msid"])
        self.assertEqual(feedback[0]["score"], inserted_rows[0]["score"])

    def test_get_feedback_for_user_with_invalid_offset_param(self):
        """ Test to make sure 400 response is received if offset argument is not valid """
        inserted_rows = self.insert_test_data(self.user["id"])

        # pass non-int value to offset
        response = self.client.get(self.custom_url_for("feedback_api_v1.get_feedback_for_user",
                                                       user_name=self.user["musicbrainz_id"]),
                                   query_string={"offset": "invalid_offset"})
        self.assert400(response)
        self.assertEqual(response.json["error"], "'offset' should be a non-negative integer")

        # pass negative int value to offset
        response = self.client.get(self.custom_url_for("feedback_api_v1.get_feedback_for_user",
                                                       user_name=self.user["musicbrainz_id"]),
                                   query_string={"offset": -1})
        self.assert400(response)
        self.assertEqual(response.json["error"], "'offset' should be a non-negative integer")

    def test_get_feedback_for_recording(self):
        """ Test to make sure valid response is received """
        inserted_rows = self.insert_test_data(self.user["id"])
        inserted_rows = self.insert_test_data(self.user2["id"])

        rec_msid_1 = inserted_rows[0]["recording_msid"]

        response = self.client.get(self.custom_url_for("feedback_api_v1.get_feedback_for_recording_msid",
                                                       recording_msid=rec_msid_1))
        self.assert200(response)
        data = json.loads(response.data)

        self.assertEqual(data["count"], 2)
        self.assertEqual(data["total_count"], len(inserted_rows))
        self.assertEqual(data["offset"], 0)

        feedback = data["feedback"]  # sorted in descending order of their creation
        self.assertEqual(len(feedback), 2)

        self.assertEqual(feedback[0]["user_id"], self.user2["musicbrainz_id"])
        self.assertEqual(feedback[0]["recording_msid"], rec_msid_1)
        self.assertEqual(feedback[0]["score"], inserted_rows[0]["score"])

        self.assertEqual(feedback[1]["user_id"], self.user["musicbrainz_id"])
        self.assertEqual(feedback[1]["recording_msid"], rec_msid_1)
        self.assertEqual(feedback[0]["score"], inserted_rows[0]["score"])

    def test_get_feedback_for_recording_mbid(self):
        """ Test to make sure valid response is received for recording mbid feedback """
        inserted_rows = self.insert_test_data_with_mbid(self.user["id"])
        inserted_rows = self.insert_test_data_with_mbid(self.user2["id"])

        rec_mbid = inserted_rows[2]["recording_mbid"]

        response = self.client.get(self.custom_url_for("feedback_api_v1.get_feedback_for_recording_mbid",
                                                       recording_mbid=rec_mbid))
        self.assert200(response)
        data = json.loads(response.data)

        self.assertEqual(data["count"], 2)
        self.assertEqual(data["total_count"], 2)
        self.assertEqual(data["offset"], 0)

        feedback = data["feedback"]  # sorted in descending order of their creation
        self.assertEqual(len(feedback), 2)

        self.assertEqual(feedback[0]["user_id"], self.user2["musicbrainz_id"])
        self.assertEqual(feedback[0]["recording_msid"], None)
        self.assertEqual(feedback[0]["recording_mbid"], rec_mbid)
        self.assertEqual(feedback[0]["score"], inserted_rows[2]["score"])

        self.assertEqual(feedback[1]["user_id"], self.user["musicbrainz_id"])
        self.assertEqual(feedback[1]["recording_msid"], None)
        self.assertEqual(feedback[1]["recording_mbid"], rec_mbid)
        self.assertEqual(feedback[1]["score"], inserted_rows[2]["score"])

    def test_get_feedback_for_recording_invalid_recording_msid(self):
        """ Test to make sure that the API sends 404 if recording_msid is invalid. """
        response = self.client.get(self.custom_url_for("feedback_api_v1.get_feedback_for_recording_msid",
                                                       recording_msid="invalid_recording_msid"))
        self.assert400(response)
        self.assertEqual(response.json["error"], "invalid_recording_msid msid format invalid.")

    def test_get_feedback_for_recording_mbid_invalid_recording_msid(self):
        """ Test to make sure that the API sends 404 if recording_mbid is invalid. """
        response = self.client.get(self.custom_url_for("feedback_api_v1.get_feedback_for_recording_mbid",
                                                       recording_mbid="invalid_recording_mbid"))
        self.assert400(response)
        self.assertEqual(response.json["error"], "invalid_recording_mbid mbid format invalid.")

    def test_get_feedback_for_recording_with_score_param(self):
        """ Test to make sure valid response is received when score param is passed """
        inserted_rows = self.insert_test_data(self.user["id"])
        inserted_rows = self.insert_test_data(self.user2["id"])

        rec_msid_1 = inserted_rows[0]["recording_msid"]

        # pass score = 1
        response = self.client.get(self.custom_url_for("feedback_api_v1.get_feedback_for_recording_msid",
                                                       recording_msid=rec_msid_1), query_string={"score": 1})
        self.assert200(response)
        data = json.loads(response.data)

        self.assertEqual(data["count"], 2)
        self.assertEqual(data["total_count"], len(inserted_rows))
        self.assertEqual(data["offset"], 0)

        feedback = data["feedback"]  # sorted in descending order of their creation
        self.assertEqual(len(feedback), 2)

        self.assertEqual(feedback[0]["user_id"], self.user2["musicbrainz_id"])
        self.assertEqual(feedback[0]["recording_msid"], rec_msid_1)
        self.assertEqual(feedback[0]["score"], inserted_rows[0]["score"])

        self.assertEqual(feedback[1]["user_id"], self.user["musicbrainz_id"])
        self.assertEqual(feedback[1]["recording_msid"], rec_msid_1)
        self.assertEqual(feedback[0]["score"], inserted_rows[0]["score"])

        # pass score = -1
        response = self.client.get(self.custom_url_for("feedback_api_v1.get_feedback_for_recording_msid",
                                                       recording_msid=rec_msid_1), query_string={"score": -1})
        self.assert200(response)
        data = json.loads(response.data)

        self.assertEqual(data["count"], 0)
        self.assertEqual(data["total_count"], len(inserted_rows))
        self.assertEqual(data["offset"], 0)

        feedback = data["feedback"]  # sorted in descending order of their creation
        self.assertEqual(len(feedback), 0)

    def test_get_feedback_for_recording_mbid_with_score_param(self):
        """ Test to make sure valid response is received when score param is passed """
        inserted_rows = self.insert_test_data_with_mbid(self.user["id"])
        inserted_rows = self.insert_test_data_with_mbid(self.user2["id"])

        rec_mbid_1 = inserted_rows[2]["recording_mbid"]

        # pass score = 1
        response = self.client.get(self.custom_url_for("feedback_api_v1.get_feedback_for_recording_mbid",
                                                       recording_mbid=rec_mbid_1), query_string={"score": 1})
        self.assert200(response)
        data = json.loads(response.data)

        self.assertEqual(data["count"], 2)
        self.assertEqual(data["total_count"], 2)
        self.assertEqual(data["offset"], 0)

        feedback = data["feedback"]  # sorted in descending order of their creation
        self.assertEqual(len(feedback), 2)

        self.assertEqual(feedback[0]["user_id"], self.user2["musicbrainz_id"])
        self.assertEqual(feedback[0]["recording_mbid"], rec_mbid_1)
        self.assertEqual(feedback[0]["score"], inserted_rows[2]["score"])

        self.assertEqual(feedback[1]["user_id"], self.user["musicbrainz_id"])
        self.assertEqual(feedback[1]["recording_mbid"], rec_mbid_1)
        self.assertEqual(feedback[1]["score"], inserted_rows[2]["score"])

        # pass score = -1
        response = self.client.get(self.custom_url_for("feedback_api_v1.get_feedback_for_recording_mbid",
                                                       recording_mbid=rec_mbid_1), query_string={"score": -1})
        self.assert200(response)
        data = json.loads(response.data)

        self.assertEqual(data["count"], 0)
        self.assertEqual(data["total_count"], 2)
        self.assertEqual(data["offset"], 0)

        feedback = data["feedback"]  # sorted in descending order of their creation
        self.assertEqual(len(feedback), 0)

    def test_get_feedback_for_recording_with_invalid_score_param(self):
        """ Test to make sure 400 response is received if score argument is not valid """
        inserted_rows = self.insert_test_data(self.user["id"])
        inserted_rows = self.insert_test_data(self.user2["id"])

        rec_msid_1 = inserted_rows[0]["recording_msid"]

        # pass non-int value to score
        response = self.client.get(self.custom_url_for("feedback_api_v1.get_feedback_for_recording_msid",
                                                       recording_msid=rec_msid_1),
                                   query_string={"score": "invalid_score"})
        self.assert400(response)
        self.assertEqual(response.json["error"], "Invalid score argument: invalid_score")

        # pass invalid int value to score
        response = self.client.get(self.custom_url_for("feedback_api_v1.get_feedback_for_recording_msid",
                                                       recording_msid=rec_msid_1), query_string={"score": 10})
        self.assert400(response)
        self.assertEqual(response.json["error"], "Score can have a value of 1 or -1.")

    def test_get_feedback_for_recording_mbid_with_invalid_score_param(self):
        """ Test to make sure 400 response is received if score argument is not valid """
        inserted_rows = self.insert_test_data_with_mbid(self.user["id"])
        inserted_rows = self.insert_test_data_with_mbid(self.user2["id"])

        rec_mbid_1 = inserted_rows[2]["recording_mbid"]

        # pass non-int value to score
        response = self.client.get(self.custom_url_for("feedback_api_v1.get_feedback_for_recording_mbid",
                                                       recording_mbid=rec_mbid_1),
                                   query_string={"score": "invalid_score"})
        self.assert400(response)
        self.assertEqual(response.json["error"], "Invalid score argument: invalid_score")

        # pass invalid int value to score
        response = self.client.get(self.custom_url_for("feedback_api_v1.get_feedback_for_recording_mbid",
                                                       recording_mbid=rec_mbid_1), query_string={"score": 10})
        self.assert400(response)
        self.assertEqual(response.json["error"], "Score can have a value of 1 or -1.")

    def test_get_feedback_for_recording_with_count_param(self):
        """ Test to make sure valid response is received when count param is passed """
        inserted_rows = self.insert_test_data(self.user["id"])
        inserted_rows = self.insert_test_data(self.user2["id"])

        rec_msid_1 = inserted_rows[0]["recording_msid"]

        # pass count = 1
        response = self.client.get(self.custom_url_for("feedback_api_v1.get_feedback_for_recording_msid",
                                                       recording_msid=rec_msid_1), query_string={"count": 1})
        self.assert200(response)
        data = json.loads(response.data)

        self.assertEqual(data["count"], 1)
        self.assertEqual(data["total_count"], len(inserted_rows))
        self.assertEqual(data["offset"], 0)

        feedback = data["feedback"]  # sorted in descending order of their creation
        self.assertEqual(len(feedback), 1)

        self.assertEqual(feedback[0]["user_id"], self.user2["musicbrainz_id"])
        self.assertEqual(feedback[0]["recording_msid"], rec_msid_1)
        self.assertEqual(feedback[0]["score"], inserted_rows[0]["score"])

    def test_get_feedback_for_recording_mbid_with_count_param(self):
        """ Test to make sure valid response is received when count param is passed """
        inserted_rows = self.insert_test_data_with_mbid(self.user["id"])
        inserted_rows = self.insert_test_data_with_mbid(self.user2["id"])

        rec_mbid_1 = inserted_rows[3]["recording_mbid"]

        # pass count = 1
        response = self.client.get(self.custom_url_for("feedback_api_v1.get_feedback_for_recording_mbid",
                                                       recording_mbid=rec_mbid_1), query_string={"count": 1})
        self.assert200(response)
        data = json.loads(response.data)

        self.assertEqual(data["count"], 1)
        self.assertEqual(data["total_count"], 2)
        self.assertEqual(data["offset"], 0)

        feedback = data["feedback"]  # sorted in descending order of their creation
        self.assertEqual(len(feedback), 1)

        self.assertEqual(feedback[0]["user_id"], self.user2["musicbrainz_id"])
        self.assertEqual(feedback[0]["recording_mbid"], rec_mbid_1)
        self.assertEqual(feedback[0]["score"], inserted_rows[3]["score"])

    def test_get_feedback_for_recording_with_invalid_count_param(self):
        """ Test to make sure 400 response is received if count argument is not valid """
        inserted_rows = self.insert_test_data(self.user["id"])
        inserted_rows = self.insert_test_data(self.user2["id"])

        rec_msid_1 = inserted_rows[0]["recording_msid"]

        # pass non-int value to count
        response = self.client.get(self.custom_url_for("feedback_api_v1.get_feedback_for_recording_msid",
                                                       recording_msid=rec_msid_1),
                                   query_string={"count": "invalid_count"})
        self.assert400(response)
        self.assertEqual(response.json["error"], "'count' should be a non-negative integer")

        # pass negative int value to count
        response = self.client.get(self.custom_url_for("feedback_api_v1.get_feedback_for_recording_msid",
                                                       recording_msid=rec_msid_1), query_string={"count": -1})
        self.assert400(response)
        self.assertEqual(response.json["error"], "'count' should be a non-negative integer")

    def test_get_feedback_for_recording_mbid_with_invalid_count_param(self):
        """ Test to make sure 400 response is received if count argument is not valid """
        inserted_rows = self.insert_test_data_with_mbid(self.user["id"])

        rec_mbid_1 = inserted_rows[2]["recording_mbid"]

        # pass non-int value to count
        response = self.client.get(self.custom_url_for("feedback_api_v1.get_feedback_for_recording_mbid",
                                                       recording_mbid=rec_mbid_1),
                                   query_string={"count": "invalid_count"})
        self.assert400(response)
        self.assertEqual(response.json["error"], "'count' should be a non-negative integer")

        # pass negative int value to count
        response = self.client.get(self.custom_url_for("feedback_api_v1.get_feedback_for_recording_mbid",
                                                       recording_mbid=rec_mbid_1), query_string={"count": -1})
        self.assert400(response)
        self.assertEqual(response.json["error"], "'count' should be a non-negative integer")

    def test_get_feedback_for_recording_with_offset_param(self):
        """ Test to make sure valid response is received when offset param is passed """
        inserted_rows = self.insert_test_data(self.user["id"])
        inserted_rows = self.insert_test_data(self.user2["id"])

        rec_msid_1 = inserted_rows[0]["recording_msid"]

        # pass count = 1
        response = self.client.get(self.custom_url_for("feedback_api_v1.get_feedback_for_recording_msid",
                                                       recording_msid=rec_msid_1), query_string={"offset": 1})
        self.assert200(response)
        data = json.loads(response.data)

        self.assertEqual(data["count"], 1)
        self.assertEqual(data["total_count"], len(inserted_rows))
        self.assertEqual(data["offset"], 1)

        feedback = data["feedback"]  # sorted in descending order of their creation
        self.assertEqual(len(feedback), 1)

        self.assertEqual(feedback[0]["user_id"], self.user["musicbrainz_id"])
        self.assertEqual(feedback[0]["recording_msid"], rec_msid_1)
        self.assertEqual(feedback[0]["score"], inserted_rows[0]["score"])

    def test_get_feedback_for_recording_mbid_with_offset_param(self):
        """ Test to make sure valid response is received when offset param is passed """
        inserted_rows = self.insert_test_data_with_mbid(self.user["id"])
        inserted_rows = self.insert_test_data_with_mbid(self.user2["id"])

        rec_mbid_1 = inserted_rows[3]["recording_mbid"]

        # pass count = 1
        response = self.client.get(self.custom_url_for("feedback_api_v1.get_feedback_for_recording_mbid",
                                                       recording_mbid=rec_mbid_1), query_string={"offset": 1})
        self.assert200(response)
        data = json.loads(response.data)

        self.assertEqual(data["count"], 1)
        self.assertEqual(data["total_count"], 2)
        self.assertEqual(data["offset"], 1)

        feedback = data["feedback"]  # sorted in descending order of their creation
        self.assertEqual(len(feedback), 1)

        self.assertEqual(feedback[0]["user_id"], self.user["musicbrainz_id"])
        self.assertEqual(feedback[0]["recording_mbid"], rec_mbid_1)
        self.assertEqual(feedback[0]["score"], inserted_rows[3]["score"])

    def test_get_feedback_for_recording_with_invalid_offset_param(self):
        """ Test to make sure 400 response is received if offset argument is not valid """
        inserted_rows = self.insert_test_data(self.user["id"])
        inserted_rows = self.insert_test_data(self.user2["id"])

        rec_msid_1 = inserted_rows[0]["recording_msid"]

        # pass non-int value to offset
        response = self.client.get(self.custom_url_for("feedback_api_v1.get_feedback_for_recording_msid",
                                                       recording_msid=rec_msid_1),
                                   query_string={"offset": "invalid_offset"})
        self.assert400(response)
        self.assertEqual(response.json["error"], "'offset' should be a non-negative integer")

        # pass negative int value to offset
        response = self.client.get(self.custom_url_for("feedback_api_v1.get_feedback_for_recording_msid",
                                                       recording_msid=rec_msid_1), query_string={"offset": -1})
        self.assert400(response)
        self.assertEqual(response.json["error"], "'offset' should be a non-negative integer")

    def test_get_feedback_for_recording_mbid_with_invalid_offset_param(self):
        """ Test to make sure 400 response is received if offset argument is not valid """
        inserted_rows = self.insert_test_data_with_mbid(self.user["id"])

        rec_mbid_1 = inserted_rows[3]["recording_mbid"]

        # pass non-int value to offset
        response = self.client.get(self.custom_url_for("feedback_api_v1.get_feedback_for_recording_mbid",
                                                       recording_mbid=rec_mbid_1),
                                   query_string={"offset": "invalid_offset"})
        self.assert400(response)
        self.assertEqual(response.json["error"], "'offset' should be a non-negative integer")

        # pass negative int value to offset
        response = self.client.get(self.custom_url_for("feedback_api_v1.get_feedback_for_recording_mbid",
                                                       recording_mbid=rec_mbid_1), query_string={"offset": -1})
        self.assert400(response)
        self.assertEqual(response.json["error"], "'offset' should be a non-negative integer")

    def _test_get_feedback_for_recordings_for_user_valid(self, fallback):
        param = "recordings" if fallback else "recording_msids"
        inserted_rows = self.insert_test_data(self.user["id"])

        # recording_msids for which feedback records are inserted
        recordings = inserted_rows[0]["recording_msid"] + "," + inserted_rows[1]["recording_msid"]

        # recording_msid for which feedback record doesn't exist
        non_existing_rec_msid = "b83fd3c3-449c-49be-a874-31d7cf26d946"
        recordings = recordings + "," + non_existing_rec_msid

        response = self.client.get(self.custom_url_for("feedback_api_v1.get_feedback_for_recordings_for_user_get",
                                                       user_name=self.user["musicbrainz_id"]),
                                   query_string={param: recordings})
        self.assert200(response)
        data = json.loads(response.data)

        feedback = data["feedback"]
        self.assertEqual(len(feedback), 3)

        self.assertEqual(feedback[0]["user_id"], self.user["musicbrainz_id"])
        self.assertEqual(feedback[0]["recording_msid"], inserted_rows[0]["recording_msid"])
        self.assertEqual(feedback[0]["score"], inserted_rows[0]["score"])

        self.assertEqual(feedback[1]["user_id"], self.user["musicbrainz_id"])
        self.assertEqual(feedback[1]["recording_msid"], inserted_rows[1]["recording_msid"])
        self.assertEqual(feedback[1]["score"], inserted_rows[1]["score"])

        self.assertEqual(feedback[2]["user_id"], self.user["musicbrainz_id"])
        self.assertEqual(feedback[2]["recording_msid"], non_existing_rec_msid)
        self.assertEqual(feedback[2]["score"], 0)

    def test_get_feedback_for_recordings_for_user(self):
        """ Test to make sure valid response is received when recording_msids is used and when fallback recordings
         parameter used """
        self._test_get_feedback_for_recordings_for_user_valid(True)
        self._test_get_feedback_for_recordings_for_user_valid(False)

    def test_get_feedback_for_recordings_for_user_valid_mbids(self):
        inserted_rows = self.insert_test_data_with_mbid(self.user["id"])

        # recording_msids for which feedback records are inserted
        recordings = inserted_rows[0]["recording_msid"] + "," + inserted_rows[1]["recording_msid"]

        # recording_msid for which feedback record doesn't exist
        non_existing_rec_msid = "b83fd3c3-449c-49be-a874-31d7cf26d946"
        recordings = recordings + "," + non_existing_rec_msid

        # recording_msids for which feedback records are inserted
        recording_mbids = inserted_rows[2]["recording_mbid"] + "," + inserted_rows[3]["recording_mbid"]

        # recording_mbid for which feedback record doesn't exist
        non_existing_rec_mbid = "6a221fda-2200-11ec-ac7d-dfa16a57158f"
        recording_mbids = recording_mbids + "," + non_existing_rec_mbid

        response = self.client.get(self.custom_url_for("feedback_api_v1.get_feedback_for_recordings_for_user_get",
                                                       user_name=self.user["musicbrainz_id"]),
                                   query_string={"recording_msids": recordings, "recording_mbids": recording_mbids})
        self.assert200(response)
        data = json.loads(response.data)

        feedback = data["feedback"]
        self.assertEqual(len(feedback), 6)

        expected = [
            {
                "user_id": self.user["musicbrainz_id"],
                "recording_msid": None,
                "recording_mbid": inserted_rows[3]["recording_mbid"],
                "score": inserted_rows[3]["score"],
                "created": None,
                "track_metadata": None
            },
            {
                "user_id": self.user["musicbrainz_id"],
                "recording_msid": None,
                "recording_mbid": inserted_rows[2]["recording_mbid"],
                "score": inserted_rows[2]["score"],
                "created": None,
                "track_metadata": None
            },
            {
                "user_id": self.user["musicbrainz_id"],
                "recording_msid": None,
                "recording_mbid": non_existing_rec_mbid,
                "score": 0,
                "created": None,
                "track_metadata": None
            },
            {
                "user_id": self.user["musicbrainz_id"],
                "recording_msid": non_existing_rec_msid,
                "recording_mbid": None,
                "score": 0,
                "created": None,
                "track_metadata": None
            },
            {
                "user_id": self.user["musicbrainz_id"],
                "recording_msid": inserted_rows[0]["recording_msid"],
                "recording_mbid": None,
                "score": inserted_rows[0]["score"],
                "created": None,
                "track_metadata": None
            },
            {
                "user_id": self.user["musicbrainz_id"],
                "recording_msid": inserted_rows[1]["recording_msid"],
                "recording_mbid": None,
                "score": inserted_rows[1]["score"],
                "created": None,
                "track_metadata": None
            }
        ]
        self.assertCountEqual(feedback, expected)

    def test_get_feedback_for_recordings_for_user_invalid_user(self):
        """ Test to make sure that the API sends 404 if user does not exist. """
        response = self.client.get(self.custom_url_for("feedback_api_v1.get_feedback_for_user", user_name="nouser"))
        self.assert404(response)
        self.assertEqual(response.json["error"], "Cannot find user: nouser")

    def test_get_feedback_for_recordings_for_user_no_recordings(self):
        """ Test to make sure that the API sends 400 if param recordings is not passed or is empty. """
        response = self.client.get(self.custom_url_for("feedback_api_v1.get_feedback_for_recordings_for_user_get",
                                                       user_name=self.user["musicbrainz_id"]))  # missing recordings param
        self.assert400(response)
        self.assertEqual(response.json["error"], "No valid recording msid or recording mbid found.")

        response = self.client.get(self.custom_url_for("feedback_api_v1.get_feedback_for_recordings_for_user_get",
                                                       user_name=self.user["musicbrainz_id"]),
                                   query_string={"recordings": ""})  # empty string
        self.assert400(response)
        self.assertEqual(response.json["error"], "No valid recording msid or recording mbid found.")

        response = self.client.get(self.custom_url_for("feedback_api_v1.get_feedback_for_recordings_for_user_get",
                                                       user_name=self.user["musicbrainz_id"]),
                                   query_string={"recording_msids": ""})  # empty string
        self.assert400(response)
        self.assertEqual(response.json["error"], "No valid recording msid or recording mbid found.")

        response = self.client.get(self.custom_url_for("feedback_api_v1.get_feedback_for_recordings_for_user_get",
                                                       user_name=self.user["musicbrainz_id"]),
                                   query_string={"recording_mbidss": ""})  # empty string
        self.assert400(response)
        self.assertEqual(response.json["error"], "No valid recording msid or recording mbid found.")

    def test_get_feedback_for_recordings_for_user_invalid_recording(self):
        """ Test to make sure that the API sends 400 if params recordings has invalid recording_msid. """
        inserted_rows = self.insert_test_data(self.user["id"])

        recordings = ""
        # recording_msids for which feedback records are inserted
        for row in inserted_rows:
            recordings += row["recording_msid"] + ","

        # invalid recording_msid
        invalid_rec_msid = "invalid_recording_msid"

        recordings += invalid_rec_msid
        response = self.client.get(self.custom_url_for("feedback_api_v1.get_feedback_for_recordings_for_user_get",
                                                       user_name=self.user["musicbrainz_id"]),
                                   query_string={"recording_msids": recordings})  # recording_msids has invalid recording_msid
        self.assert400(response)
        self.assertEqual(response.json["code"], 400)

        response = self.client.get(self.custom_url_for("feedback_api_v1.get_feedback_for_recordings_for_user_get",
                                                       user_name=self.user["musicbrainz_id"]),
                                   query_string={
                                       "recording_mbids": recordings})  # recording_mbids has invalid recording_msid
        self.assert400(response)
        self.assertEqual(response.json["code"], 400)

    def test_get_feedback_for_recordings_for_post_method_for_user_valid_mbids(self):
        inserted_rows = self.insert_test_data_with_mbid(self.user["id"])

        # recording_msids for which feedback records are inserted
        recordings = [inserted_rows[0]["recording_msid"], inserted_rows[1]["recording_msid"]]

        # recording_msid for which feedback record doesn't exist
        non_existing_rec_msid = "b83fd3c3-449c-49be-a874-31d7cf26d946"
        recordings.append(non_existing_rec_msid)

        # recording_msids for which feedback records are inserted
        recording_mbids = [inserted_rows[2]["recording_mbid"], inserted_rows[3]["recording_mbid"]]

        # recording_mbid for which feedback record doesn't exist
        non_existing_rec_mbid = "6a221fda-2200-11ec-ac7d-dfa16a57158f"
        recording_mbids.append(non_existing_rec_mbid)

        response = self.client.post(self.custom_url_for("feedback_api_v1.get_feedback_for_recordings_for_user_post",
                                                        user_name=self.user["musicbrainz_id"]),
                                    data=json.dumps({"recording_msids": recordings, "recording_mbids": recording_mbids}),
                                    content_type="application/json")

        self.assert200(response)
        data = json.loads(response.data)

        feedback = data["feedback"]
        self.assertEqual(len(feedback), 6)

        expected = [
            {
                "user_id": self.user["musicbrainz_id"],
                "recording_msid": None,
                "recording_mbid": inserted_rows[3]["recording_mbid"],
                "score": inserted_rows[3]["score"],
                "created": None,
                "track_metadata": None
            },
            {
                "user_id": self.user["musicbrainz_id"],
                "recording_msid": None,
                "recording_mbid": inserted_rows[2]["recording_mbid"],
                "score": inserted_rows[2]["score"],
                "created": None,
                "track_metadata": None
            },
            {
                "user_id": self.user["musicbrainz_id"],
                "recording_msid": None,
                "recording_mbid": non_existing_rec_mbid,
                "score": 0,
                "created": None,
                "track_metadata": None
            },
            {
                "user_id": self.user["musicbrainz_id"],
                "recording_msid": non_existing_rec_msid,
                "recording_mbid": None,
                "score": 0,
                "created": None,
                "track_metadata": None
            },
            {
                "user_id": self.user["musicbrainz_id"],
                "recording_msid": inserted_rows[0]["recording_msid"],
                "recording_mbid": None,
                "score": inserted_rows[0]["score"],
                "created": None,
                "track_metadata": None
            },
            {
                "user_id": self.user["musicbrainz_id"],
                "recording_msid": inserted_rows[1]["recording_msid"],
                "recording_mbid": None,
                "score": inserted_rows[1]["score"],
                "created": None,
                "track_metadata": None
            }
        ]
        self.assertCountEqual(feedback, expected)

    def test_get_feedback_for_recordings_for_user_for_post_method_no_recordings(self):
        """ Test to make sure that the API sends 400 if body data recording_msids or recording_mbids is not passed or is empty. """
        response = self.client.post(self.custom_url_for("feedback_api_v1.get_feedback_for_recordings_for_user_post",
                                                        user_name=self.user["musicbrainz_id"]),
                                    data=json.dumps({"recording_msids": []}),  # empty list
                                    content_type="application/json")
        self.assert400(response)
        self.assertEqual(response.json["error"], "No valid recording msid or recording mbid found.")

        response = self.client.post(self.custom_url_for("feedback_api_v1.get_feedback_for_recordings_for_user_post",
                                                        user_name=self.user["musicbrainz_id"]),
                                    data=json.dumps({"recording_mbids": []}),  # empty list
                                    content_type="application/json")
        self.assert400(response)
        self.assertEqual(response.json["error"], "No valid recording msid or recording mbid found.")

    def test_get_feedback_for_recordings_for_post_method_for_user_invalid_recording(self):
        """ Test to make sure that the API sends 400 if body data recording_msids has invalid recording_msid. """
        inserted_rows = self.insert_test_data(self.user["id"])

        recordings = []
        # recording_msids for which feedback records are inserted
        for row in inserted_rows:
            recordings.append(row["recording_msid"])

        # invalid recording_msid
        invalid_rec_msid = "invalid_recording_msid"

        recordings.append(invalid_rec_msid)
        response = self.client.post(self.custom_url_for("feedback_api_v1.get_feedback_for_recordings_for_user_post",
                                                        user_name=self.user["musicbrainz_id"]),
                                    data=json.dumps({"recording_msids": recordings}),
                                    content_type="application/json")
        self.assert400(response)
        self.assertEqual(response.json["code"], 400)

    def _insert_feedback_with_metadata(self, user_id):
        recordings = [
            {
                "title": "Strangers",
                "artist": "Portishead",
                "release": "Dummy"
            },
            {
                "title": "Wicked Game",
                "artist": "Tom Ellis",
                "release": "Lucifer"
            }
        ]
        submitted_data = messybrainz.insert_all_in_transaction(self.ts_conn, recordings)

        sample_feedback = [
            {
                "recording_msid": submitted_data[0],
                "score": 1
            },
            {
                "recording_msid": submitted_data[1],
                "score": -1
            }
        ]
        for fb in sample_feedback:
            db_feedback.insert(
                self.db_conn,
                Feedback(
                    user_id=user_id,
                    recording_msid=fb["recording_msid"],
                    score=fb["score"]
                )
            )
        return sample_feedback

    def test_feedback_view(self):
        # user.taste endpoint queries recording feedback with metadata which loads
        # data from msb so insert recordings into msb as well, otherwise the test will fail
        inserted_rows = self._insert_feedback_with_metadata(self.user["id"])

        # Fetch loved page
        r = self.client.post(self.custom_url_for('user.taste', user_name=self.user['musicbrainz_id']))
        self.assert200(r)
        json_response = r.json

        self.assertEqual(json_response['feedback_count'], 1)
        self.assertEqual(json_response['active_section'], 'taste')
        feedback = json_response["feedback"]

        self.assertEqual(len(feedback), 1)
        self.assertEqual(feedback[0]["user_id"], self.user["musicbrainz_id"])
        self.assertEqual(feedback[0]["recording_msid"], inserted_rows[0]["recording_msid"])
        self.assertEqual(feedback[0]["score"], inserted_rows[0]["score"])
        self.assertNotEqual(feedback[0]["created"], "")

        # Fetch hated page
        r = self.client.post(self.custom_url_for('user.taste', user_name=self.user['musicbrainz_id'], score=-1))
        self.assert200(r)
        json_response = r.json

        self.assertEqual(json_response['feedback_count'], 1)
        self.assertEqual(json_response['active_section'], 'taste')
        feedback = json_response["feedback"]

        self.assertEqual(len(feedback), 1)
        self.assertEqual(feedback[0]["user_id"], self.user["musicbrainz_id"])
        self.assertEqual(feedback[0]["recording_msid"], inserted_rows[1]["recording_msid"])
        self.assertEqual(feedback[0]["score"], inserted_rows[1]["score"])
        self.assertNotEqual(feedback[0]["created"], "")

    @mock.patch("listenbrainz.domain.lastfm.load_recordings_from_tracks")
    @requests_mock.Mocker()
    def test_feedback_import(self, mock_load_recordings, mock_requests):
        with open(self.path_to_data_file("lastfm_loved_tracks_1.json")) as f:
            page_1 = json.load(f)
        with open(self.path_to_data_file("lastfm_loved_tracks_2.json")) as f:
            page_2 = json.load(f)
        mock_requests.get("https://ws.audioscrobbler.com/2.0/", [
            {"json": page_1, "status_code": 200},
            {"json": page_1, "status_code": 200},
            {"json": page_2, "status_code": 200}
        ])
        mock_load_recordings.return_value = {
            "07e81754-518c-4e3b-8671-c5df5643dad0": "7ac86b1a-d183-40ca-9d41-df2d90681ffd",
            "018dfa9b-7a80-3997-b64e-8520488656a1": "9d0c31ef-257a-41af-9a8c-f28a5cd87467",
            "2446a9ae-6e63-3273-bfc9-58eed8571d7a": "f53937b3-f6dc-450c-8d57-bbc667d8af23"
        }
        expected_msid = messybrainz.submit_recording(self.ts_conn, "Let Me Love You", "ariana grande")
        self.ts_conn.commit()

        r = self.client.post(
            self.custom_url_for("feedback_api_v1.import_feedback"),
            data=json.dumps({"service": "lastfm", "user_name": "lucifer"}),
            headers={"Authorization": f'Token {self.user["auth_token"]}'},
            content_type="application/json"
        )
        self.assert200(r)
        self.assertDictEqual(r.json, {
            "total": 8,
            "imported": 6,
        })
        r = self.client.get(
            self.custom_url_for("feedback_api_v1.get_feedback_for_user", user_name=self.user["musicbrainz_id"]))
        print(r.json)

        data = r.json
        self.assertEqual(data["count"], 6)
        self.assertEqual(data["total_count"], 6)
        self.assertEqual(data["offset"], 0)
        expected_mbids = [
            "7ac86b1a-d183-40ca-9d41-df2d90681ffd",
            "9d0c31ef-257a-41af-9a8c-f28a5cd87467",
            "f53937b3-f6dc-450c-8d57-bbc667d8af23"
        ]
        received_mbids = {f["recording_mbid"] for f in data["feedback"]}
        received_msids = {f["recording_msid"] for f in data["feedback"]}
        for mbid in expected_mbids:
            self.assertIn(mbid, received_mbids)
        self.assertIn(expected_msid, received_msids)
