import json
import listenbrainz.db.user as db_user
import listenbrainz.db.feedback as db_feedback

from flask import url_for
from listenbrainz.feedback import Feedback
from listenbrainz.tests.integration import IntegrationTestCase


class FeedbackAPITestCase(IntegrationTestCase):
    def setUp(self):
        super(FeedbackAPITestCase, self).setUp()
        self.user = db_user.get_or_create(1, "testuserpleaseignore")
        self.user2 = db_user.get_or_create(2, "anothertestuserpleaseignore")

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
                Feedback(
                    user_id=user_id,
                    recording_msid=fb["recording_msid"],
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
            url_for("feedback_api_v1.recording_feedback"),
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
            url_for("feedback_api_v1.recording_feedback"),
            data=json.dumps(feedback),
            content_type="application/json"
        )
        self.assert401(response)
        self.assertEqual(response.json["code"], 401)

        # request with invalid authorization header
        response = self.client.post(
            url_for("feedback_api_v1.recording_feedback"),
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
            url_for("feedback_api_v1.recording_feedback"),
            data=json.dumps(incomplete_feedback),
            headers={"Authorization": "Token {}".format(self.user["auth_token"])},
            content_type="application/json"
        )
        self.assert400(response)
        self.assertEqual(response.json["error"], "JSON document must contain recording_msid and "
                         "score top level keys")

        # submit a feedback without score key
        incomplete_feedback = {
            "recording_msid": "7babc9be-ca2b-4544-b932-7c9ab38770d6",
        }

        response = self.client.post(
            url_for("feedback_api_v1.recording_feedback"),
            data=json.dumps(incomplete_feedback),
            headers={"Authorization": "Token {}".format(self.user["auth_token"])},
            content_type="application/json"
        )
        self.assert400(response)
        self.assertEqual(response.json["error"], "JSON document must contain recording_msid and "
                         "score top level keys")

        # submit an empty feedback
        empty_feedback = {}

        response = self.client.post(
            url_for("feedback_api_v1.recording_feedback"),
            data=json.dumps(empty_feedback),
            headers={"Authorization": "Token {}".format(self.user["auth_token"])},
            content_type="application/json"
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
            url_for("feedback_api_v1.recording_feedback"),
            data=json.dumps(invalid_feedback),
            headers={"Authorization": "Token {}".format(self.user["auth_token"])},
            content_type="application/json"
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
            url_for("feedback_api_v1.recording_feedback"),
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
            url_for("feedback_api_v1.recording_feedback"),
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
            url_for("feedback_api_v1.recording_feedback"),
            data=json.dumps(invalid_feedback),
            headers={"Authorization": "Token {}".format(self.user["auth_token"])},
            content_type="application/json"
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
            url_for("feedback_api_v1.recording_feedback"),
            data=json.dumps(feedback),
            headers={"Authorization": "Token {}".format(self.user["auth_token"])},
            content_type="application/json"
        )
        self.assert200(response)
        self.assertEqual(response.json["status"], "ok")

        result = db_feedback.get_feedback_for_user(self.user["id"], limit=25, offset=0)
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
            url_for("feedback_api_v1.recording_feedback"),
            data=json.dumps(updated_feedback),
            headers={"Authorization": "Token {}".format(self.user["auth_token"])},
            content_type="application/json"
        )
        self.assert200(response)
        self.assertEqual(response.json["status"], "ok")

        # check that the record gets updated
        result = db_feedback.get_feedback_for_user(self.user["id"], limit=25, offset=0)
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
            url_for("feedback_api_v1.recording_feedback"),
            data=json.dumps(feedback),
            headers={"Authorization": "Token {}".format(self.user["auth_token"])},
            content_type="application/json"
        )
        self.assert200(response)
        self.assertEqual(response.json["status"], "ok")

        result = db_feedback.get_feedback_for_user(self.user["id"], limit=25, offset=0)
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
            url_for("feedback_api_v1.recording_feedback"),
            data=json.dumps(updated_feedback),
            headers={"Authorization": "Token {}".format(self.user["auth_token"])},
            content_type="application/json"
        )
        self.assert200(response)
        self.assertEqual(response.json["status"], "ok")

        # check that the record gets deleted
        result = db_feedback.get_feedback_for_user(self.user["id"], limit=25, offset=0)
        self.assertEqual(len(result), 0)

    def test_get_feedback_for_user(self):
        """ Test to make sure valid response is received """
        inserted_rows = self.insert_test_data(self.user["id"])

        response = self.client.get(url_for("feedback_api_v1.get_feedback_for_user", user_name=self.user["musicbrainz_id"]))
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
        response = self.client.get(url_for("stats_api_v1.get_artist", user_name="nouser"))
        self.assert404(response)
        self.assertEqual(response.json["error"], "Cannot find user: nouser")

    def test_get_feedback_for_user_with_score_param(self):
        """ Test to make sure valid response is received when score param is passed """
        inserted_rows = self.insert_test_data(self.user["id"])

        # pass score = 1
        response = self.client.get(url_for("feedback_api_v1.get_feedback_for_user",
                                   user_name=self.user["musicbrainz_id"]), query_string={"score": 1})
        self.assert200(response)
        data = json.loads(response.data)

        self.assertEqual(data["count"], 1)
        self.assertEqual(data["total_count"], len(inserted_rows))
        self.assertEqual(data["offset"], 0)

        feedback = data["feedback"]  # sorted in descending order of their creation
        self.assertEqual(len(feedback), 1)

        self.assertEqual(feedback[0]["user_id"], self.user["musicbrainz_id"])
        self.assertEqual(feedback[0]["recording_msid"], inserted_rows[0]["recording_msid"])
        self.assertEqual(feedback[0]["score"], 1)

        # pass score = -1
        response = self.client.get(url_for("feedback_api_v1.get_feedback_for_user",
                                   user_name=self.user["musicbrainz_id"]), query_string={"score": -1})
        self.assert200(response)
        data = json.loads(response.data)

        self.assertEqual(data["count"], 1)
        self.assertEqual(data["total_count"], len(inserted_rows))
        self.assertEqual(data["offset"], 0)

        feedback = data["feedback"]  # sorted in descending order of their creation
        self.assertEqual(len(feedback), 1)

        self.assertEqual(feedback[0]["user_id"], self.user["musicbrainz_id"])
        self.assertEqual(feedback[0]["recording_msid"], inserted_rows[1]["recording_msid"])
        self.assertEqual(feedback[0]["score"], -1)

    def test_get_feedback_for_user_with_invalid_score_param(self):
        """ Test to make sure 400 response is received if score argument is not valid """
        inserted_rows = self.insert_test_data(self.user["id"])

        # pass non-int value to score
        response = self.client.get(url_for("feedback_api_v1.get_feedback_for_user",
                                   user_name=self.user["musicbrainz_id"]), query_string={"score": "invalid_score"})
        self.assert400(response)
        self.assertEqual(response.json["error"], "Invalid score argument: invalid_score")

        # pass invalid int value to score
        response = self.client.get(url_for("feedback_api_v1.get_feedback_for_user",
                                   user_name=self.user["musicbrainz_id"]), query_string={"score": 10})
        self.assert400(response)
        self.assertEqual(response.json["error"], "Score can have a value of 1 or -1.")

    def test_get_feedback_for_user_with_count_param(self):
        """ Test to make sure valid response is received when count param is passed """
        inserted_rows = self.insert_test_data(self.user["id"])

        # pass count = 1
        response = self.client.get(url_for("feedback_api_v1.get_feedback_for_user",
                                   user_name=self.user["musicbrainz_id"]), query_string={"count": 1})
        self.assert200(response)
        data = json.loads(response.data)

        self.assertEqual(data["count"], 1)
        self.assertEqual(data["total_count"], len(inserted_rows))
        self.assertEqual(data["offset"], 0)

        feedback = data["feedback"]  # sorted in descending order of their creation
        self.assertEqual(len(feedback), 1)

        self.assertEqual(feedback[0]["user_id"], self.user["musicbrainz_id"])
        self.assertEqual(feedback[0]["recording_msid"], inserted_rows[1]["recording_msid"])
        self.assertEqual(feedback[0]["score"], inserted_rows[1]["score"])

    def test_get_feedback_for_user_with_invalid_count_param(self):
        """ Test to make sure 400 response is received if count argument is not valid """
        inserted_rows = self.insert_test_data(self.user["id"])

        # pass non-int value to count
        response = self.client.get(url_for("feedback_api_v1.get_feedback_for_user",
                                   user_name=self.user["musicbrainz_id"]), query_string={"count": "invalid_count"})
        self.assert400(response)
        self.assertEqual(response.json["error"], "'count' should be a non-negative integer")

        # pass negative int value to count
        response = self.client.get(url_for("feedback_api_v1.get_feedback_for_user",
                                   user_name=self.user["musicbrainz_id"]), query_string={"count": -1})
        self.assert400(response)
        self.assertEqual(response.json["error"], "'count' should be a non-negative integer")

    def test_get_feedback_for_user_with_offset_param(self):
        """ Test to make sure valid response is received when offset param is passed """
        inserted_rows = self.insert_test_data(self.user["id"])

        # pass count = 1
        response = self.client.get(url_for("feedback_api_v1.get_feedback_for_user",
                                   user_name=self.user["musicbrainz_id"]), query_string={"offset": 1})
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
        response = self.client.get(url_for("feedback_api_v1.get_feedback_for_user",
                                   user_name=self.user["musicbrainz_id"]), query_string={"offset": "invalid_offset"})
        self.assert400(response)
        self.assertEqual(response.json["error"], "'offset' should be a non-negative integer")

        # pass negative int value to offset
        response = self.client.get(url_for("feedback_api_v1.get_feedback_for_user",
                                   user_name=self.user["musicbrainz_id"]), query_string={"offset": -1})
        self.assert400(response)
        self.assertEqual(response.json["error"], "'offset' should be a non-negative integer")

    def test_get_feedback_for_recording(self):
        """ Test to make sure valid response is received """
        inserted_rows = self.insert_test_data(self.user["id"])
        inserted_rows = self.insert_test_data(self.user2["id"])

        rec_msid_1 = inserted_rows[0]["recording_msid"]

        response = self.client.get(url_for("feedback_api_v1.get_feedback_for_recording",
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

    def test_get_feedback_for_recording_invalid_recording_msid(self):
        """ Test to make sure that the API sends 404 if recording_msid is invalid. """
        response = self.client.get(url_for("feedback_api_v1.get_feedback_for_recording", recording_msid="invalid_recording_msid"))
        self.assert400(response)
        self.assertEqual(response.json["error"], "invalid_recording_msid MSID format invalid.")

    def test_get_feedback_for_recording_with_score_param(self):
        """ Test to make sure valid response is received when score param is passed """
        inserted_rows = self.insert_test_data(self.user["id"])
        inserted_rows = self.insert_test_data(self.user2["id"])

        rec_msid_1 = inserted_rows[0]["recording_msid"]

        # pass score = 1
        response = self.client.get(url_for("feedback_api_v1.get_feedback_for_recording",
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
        response = self.client.get(url_for("feedback_api_v1.get_feedback_for_recording",
                                           recording_msid=rec_msid_1), query_string={"score": -1})
        self.assert200(response)
        data = json.loads(response.data)

        self.assertEqual(data["count"], 0)
        self.assertEqual(data["total_count"], len(inserted_rows))
        self.assertEqual(data["offset"], 0)

        feedback = data["feedback"]  # sorted in descending order of their creation
        self.assertEqual(len(feedback), 0)

    def test_get_feedback_for_recording_with_invalid_score_param(self):
        """ Test to make sure 400 response is received if score argument is not valid """
        inserted_rows = self.insert_test_data(self.user["id"])
        inserted_rows = self.insert_test_data(self.user2["id"])

        rec_msid_1 = inserted_rows[0]["recording_msid"]

        # pass non-int value to score
        response = self.client.get(url_for("feedback_api_v1.get_feedback_for_recording",
                                           recording_msid=rec_msid_1), query_string={"score": "invalid_score"})
        self.assert400(response)
        self.assertEqual(response.json["error"], "Invalid score argument: invalid_score")

        # pass invalid int value to score
        response = self.client.get(url_for("feedback_api_v1.get_feedback_for_recording",
                                           recording_msid=rec_msid_1), query_string={"score": 10})
        self.assert400(response)
        self.assertEqual(response.json["error"], "Score can have a value of 1 or -1.")

    def test_get_feedback_for_recording_with_count_param(self):
        """ Test to make sure valid response is received when count param is passed """
        inserted_rows = self.insert_test_data(self.user["id"])
        inserted_rows = self.insert_test_data(self.user2["id"])

        rec_msid_1 = inserted_rows[0]["recording_msid"]

        # pass count = 1
        response = self.client.get(url_for("feedback_api_v1.get_feedback_for_recording",
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

    def test_get_feedback_for_recording_with_invalid_count_param(self):
        """ Test to make sure 400 response is received if count argument is not valid """
        inserted_rows = self.insert_test_data(self.user["id"])
        inserted_rows = self.insert_test_data(self.user2["id"])

        rec_msid_1 = inserted_rows[0]["recording_msid"]

        # pass non-int value to count
        response = self.client.get(url_for("feedback_api_v1.get_feedback_for_recording",
                                           recording_msid=rec_msid_1), query_string={"count": "invalid_count"})
        self.assert400(response)
        self.assertEqual(response.json["error"], "'count' should be a non-negative integer")

        # pass negative int value to count
        response = self.client.get(url_for("feedback_api_v1.get_feedback_for_recording",
                                           recording_msid=rec_msid_1), query_string={"count": -1})
        self.assert400(response)
        self.assertEqual(response.json["error"], "'count' should be a non-negative integer")

    def test_get_feedback_for_recording_with_offset_param(self):
        """ Test to make sure valid response is received when offset param is passed """
        inserted_rows = self.insert_test_data(self.user["id"])
        inserted_rows = self.insert_test_data(self.user2["id"])

        rec_msid_1 = inserted_rows[0]["recording_msid"]

        # pass count = 1
        response = self.client.get(url_for("feedback_api_v1.get_feedback_for_recording",
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

    def test_get_feedback_for_recording_with_invalid_offset_param(self):
        """ Test to make sure 400 response is received if offset argument is not valid """
        inserted_rows = self.insert_test_data(self.user["id"])
        inserted_rows = self.insert_test_data(self.user2["id"])

        rec_msid_1 = inserted_rows[0]["recording_msid"]

        # pass non-int value to offset
        response = self.client.get(url_for("feedback_api_v1.get_feedback_for_recording",
                                           recording_msid=rec_msid_1), query_string={"offset": "invalid_offset"})
        self.assert400(response)
        self.assertEqual(response.json["error"], "'offset' should be a non-negative integer")

        # pass negative int value to offset
        response = self.client.get(url_for("feedback_api_v1.get_feedback_for_recording",
                                           recording_msid=rec_msid_1), query_string={"offset": -1})
        self.assert400(response)
        self.assertEqual(response.json["error"], "'offset' should be a non-negative integer")
