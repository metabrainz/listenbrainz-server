import json
import uuid
import listenbrainz.db.user as db_user
import listenbrainz.db.recommendations_cf_recording_feedback as db_feedback

from redis import Redis
from flask import url_for, current_app
from listenbrainz.db.model.recommendation_feedback import (RecommendationFeedbackSubmit,
                                                           RecommendationFeedbackDelete,
                                                           get_allowed_ratings)
from listenbrainz.tests.integration import IntegrationTestCase


class RecommendationFeedbackAPITestCase(IntegrationTestCase):
    def setUp(self):
        super(RecommendationFeedbackAPITestCase, self).setUp()
        self.user = db_user.get_or_create(1, "vansika")
        self.user1 = db_user.get_or_create(2, "vansika_1")
        self.user2 = db_user.get_or_create(3, "vansika_2")

    def tearDown(self):
        r = Redis(host=current_app.config['REDIS_HOST'], port=current_app.config['REDIS_PORT'])
        r.flushall()
        super(RecommendationFeedbackAPITestCase, self).tearDown()

    def insert_test_data(self):
        sample_feedback = [
            {
                "recording_mbid": "222eb00d-9ead-42de-aec9-8f8c1509413d",
                "rating": 'bad_recommendation',
                "user_id": self.user1['id']
            },
            {
                "recording_mbid": "922eb00d-9ead-42de-aec9-8f8c1509413d",
                "rating": 'hate',
                "user_id": self.user1['id']
            }
        ]

        for fb in sample_feedback:
            db_feedback.insert(
                RecommendationFeedbackSubmit(
                    user_id=fb['user_id'],
                    recording_mbid=fb["recording_mbid"],
                    rating=fb["rating"]
                )
            )

        return sample_feedback

    def test_recommendation_feedback_submit(self):
        """ Test for submission of valid feedback """
        feedback = {
            "recording_mbid": "7babc9be-ca2b-4544-b932-7c9ab38770d6",
            "rating": 'love'
        }

        response = self.client.post(
            url_for("recommendation_feedback_api_v1.submit_recommendation_feedback"),
            data=json.dumps(feedback),
            headers={"Authorization": "Token {}".format(self.user["auth_token"])},
            content_type="application/json"
        )
        self.assert200(response)
        self.assertEqual(response.json["status"], "ok")

    def test_recommendation_feedback_submit_unauthorised_submission(self):
        """ Test for checking that unauthorized submissions return 401 """
        feedback = {
            "recording_mbid": "7babc9be-ca2b-4544-b932-7c9ab38770d6",
            "rating": 'hate'
        }

        # request with no authorization header
        response = self.client.post(
            url_for("recommendation_feedback_api_v1.submit_recommendation_feedback"),
            data=json.dumps(feedback),
            content_type="application/json"
        )
        self.assert401(response)
        self.assertEqual(response.json["code"], 401)

        # request with invalid authorization header
        response = self.client.post(
            url_for("recommendation_feedback_api_v1.submit_recommendation_feedback"),
            data=json.dumps(feedback),
            headers={"Authorization": "Token testtokenplsignore"},
            content_type="application/json"
        )
        self.assert401(response)
        self.assertEqual(response.json["code"], 401)

    def test_recommendation_feedback_submit_json_with_missing_keys(self):
        """ Test for checking that submitting JSON with missing keys returns 400 """

        # submit a feedback without recording_mbid key
        incomplete_feedback = {
            "rating": 'hate'
        }

        response = self.client.post(
            url_for("recommendation_feedback_api_v1.submit_recommendation_feedback"),
            data=json.dumps(incomplete_feedback),
            headers={"Authorization": "Token {}".format(self.user["auth_token"])},
            content_type="application/json"
        )
        self.assert400(response)
        self.assertEqual(response.json["error"], "JSON document must contain recording_mbid and rating")

        # submit a feedback without rating key
        incomplete_feedback = {
            "recording_mbid": "7babc9be-ca2b-4544-b932-7c9ab38770d6",
        }

        response = self.client.post(
            url_for("recommendation_feedback_api_v1.submit_recommendation_feedback"),
            data=json.dumps(incomplete_feedback),
            headers={"Authorization": "Token {}".format(self.user["auth_token"])},
            content_type="application/json"
        )
        self.assert400(response)
        self.assertEqual(response.json["error"], "JSON document must contain recording_mbid and rating")

        # submit an empty feedback
        empty_feedback = {}

        response = self.client.post(
            url_for("recommendation_feedback_api_v1.submit_recommendation_feedback"),
            data=json.dumps(empty_feedback),
            headers={"Authorization": "Token {}".format(self.user["auth_token"])},
            content_type="application/json"
        )
        self.assert400(response)
        self.assertEqual(response.json["error"], "JSON document must contain recording_mbid and rating")

    def test_recommendation_feedback_submit_json_with_extra_keys(self):
        """ Test to check submitting JSON with extra keys returns 400 """
        invalid_feedback = {
            "recording_mbid": "7babc9be-ca2b-4544-b932-7c9ab38770d6",
            "rating": 'like',
            "extra_key": "extra_key"
        }

        response = self.client.post(
            url_for("recommendation_feedback_api_v1.submit_recommendation_feedback"),
            data=json.dumps(invalid_feedback),
            headers={"Authorization": "Token {}".format(self.user["auth_token"])},
            content_type="application/json"
        )
        self.assert400(response)
        self.assertEqual(response.json["error"], "JSON document must only contain recording_mbid and rating")

    def test_recommendation_feedback_submit_invalid_values(self):
        """ Test to check submitting invalid values in JSON returns 400 """

        # submit feedback with invalid recording_mbid
        invalid_feedback = {
            "recording_mbid": "invalid_recording_mbid",
            "rating": 'hate'
        }

        response = self.client.post(
            url_for("recommendation_feedback_api_v1.submit_recommendation_feedback"),
            data=json.dumps(invalid_feedback),
            headers={"Authorization": "Token {}".format(self.user["auth_token"])},
            content_type="application/json"
        )
        self.assert400(response)

        # submit feedback with invalid rating
        invalid_feedback = {
            "recording_mbid": "7babc9be-ca2b-4544-b932-7c9ab38770d6",
            "rating": "lalalalala"
        }

        response = self.client.post(
            url_for("recommendation_feedback_api_v1.submit_recommendation_feedback"),
            data=json.dumps(invalid_feedback),
            headers={"Authorization": "Token {}".format(self.user["auth_token"])},
            content_type="application/json"
        )
        self.assert400(response)

        # submit feedback with invalid recording_mbid and rating
        invalid_feedback = {
            "recording_mbid": "invalid_recording_msid",
            "rating": 'lalalalala'
        }

        response = self.client.post(
            url_for("recommendation_feedback_api_v1.submit_recommendation_feedback"),
            data=json.dumps(invalid_feedback),
            headers={"Authorization": "Token {}".format(self.user["auth_token"])},
            content_type="application/json"
        )
        self.assert400(response)

    def test_recommendation_feedback_update_rating(self):
        """
        Test to check that rating gets updated when a user changes feedback rating for a recording_mbid
        """
        feedback = {
            "recording_mbid": "7babc9be-ca2b-4544-b932-7c9ab38770d6",
            "rating": "love"
        }

        response = self.client.post(
            url_for("recommendation_feedback_api_v1.submit_recommendation_feedback"),
            data=json.dumps(feedback),
            headers={"Authorization": "Token {}".format(self.user["auth_token"])},
            content_type="application/json"
        )
        self.assert200(response)
        self.assertEqual(response.json["status"], "ok")

        result = db_feedback.get_feedback_for_user(self.user["id"], limit=25, offset=0)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].user_id, self.user["id"])
        self.assertEqual(result[0].recording_mbid, feedback["recording_mbid"])
        self.assertEqual(result[0].rating, feedback["rating"])

        # submit an updated feedback for the same recording_mbid with new rating = "bad_recommendation"
        updated_feedback = {
            "recording_mbid": "7babc9be-ca2b-4544-b932-7c9ab38770d6",
            "rating": "bad_recommendation"
        }

        response = self.client.post(
            url_for("recommendation_feedback_api_v1.submit_recommendation_feedback"),
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
        self.assertEqual(result[0].recording_mbid, updated_feedback["recording_mbid"])
        self.assertEqual(result[0].rating, updated_feedback["rating"])

    def test_recommendation_feedback_delete(self):
        """ Test for submission of valid feedback """
        feedback = {
            "recording_mbid": "7babc9be-ca2b-4544-b932-7c9ab38770d6",
            "rating": 'love'
        }

        response = self.client.post(
            url_for("recommendation_feedback_api_v1.submit_recommendation_feedback"),
            data=json.dumps(feedback),
            headers={"Authorization": "Token {}".format(self.user["auth_token"])},
            content_type="application/json"
        )
        self.assert200(response)
        self.assertEqual(response.json["status"], "ok")

        result = db_feedback.get_feedback_for_user(self.user["id"], limit=25, offset=0)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].user_id, self.user["id"])
        self.assertEqual(result[0].recording_mbid, feedback["recording_mbid"])
        self.assertEqual(result[0].rating, feedback["rating"])

        response = self.client.post(
            url_for("recommendation_feedback_api_v1.delete_recommendation_feedback"),
            data=json.dumps({
                "recording_mbid": "7babc9be-ca2b-4544-b932-7c9ab38770d6",
            }),
            headers={"Authorization": "Token {}".format(self.user["auth_token"])},
            content_type="application/json"
        )
        self.assert200(response)
        self.assertEqual(response.json["status"], "ok")

        # check that the record gets deleted
        result = db_feedback.get_feedback_for_user(self.user["id"], limit=25, offset=0)
        self.assertEqual(len(result), 0)

    def test_recommendation_feedback_delete_unauthorised_submission(self):
        """ Test for checking that unauthorized submissions return 401 """
        del_rec = {
            "recording_mbid": "7babc9be-ca2b-4544-b932-7c9ab38770d6",
        }

        # request with no authorization header
        response = self.client.post(
            url_for("recommendation_feedback_api_v1.delete_recommendation_feedback"),
            data=json.dumps(del_rec),
            content_type="application/json"
        )
        self.assert401(response)

        # request with invalid authorization header
        response = self.client.post(
            url_for("recommendation_feedback_api_v1.delete_recommendation_feedback"),
            data=json.dumps(del_rec),
            headers={"Authorization": "Token testtokenplsignore"},
            content_type="application/json"
        )
        self.assert401(response)
        self.assertEqual(response.json["code"], 401)

    def test_recommendation_feedback_delete_json_with_missing_and_invalid_keys(self):

        invalid_del_rec = {
            "invalid": 'invalid'
        }

        response = self.client.post(
            url_for("recommendation_feedback_api_v1.delete_recommendation_feedback"),
            data=json.dumps(invalid_del_rec),
            headers={"Authorization": "Token {}".format(self.user["auth_token"])},
            content_type="application/json"
        )
        self.assert400(response)
        self.assertEqual(response.json["error"], "JSON document must contain recording_mbid")

        empty_del_rec = {}

        response = self.client.post(
            url_for("recommendation_feedback_api_v1.delete_recommendation_feedback"),
            data=json.dumps(empty_del_rec),
            headers={"Authorization": "Token {}".format(self.user["auth_token"])},
            content_type="application/json"
        )
        self.assert400(response)
        self.assertEqual(response.json["error"], "JSON document must contain recording_mbid")

        invalid_del_rec = {
            "recording_mbid": 'invalid'
        }

        response = self.client.post(
            url_for("recommendation_feedback_api_v1.delete_recommendation_feedback"),
            data=json.dumps(invalid_del_rec),
            headers={"Authorization": "Token {}".format(self.user["auth_token"])},
            content_type="application/json"
        )
        self.assert400(response)

    def test_recommendation_feedback_submit_json_with_extra_delete_keys(self):
        """ Test to check submitting JSON with extra keys returns 400 """
        invalid_del_rec = {
            "recording_mbid": "7babc9be-ca2b-4544-b932-7c9ab38770d6",
            "extra_key": "extra_key"
        }

        response = self.client.post(
            url_for("recommendation_feedback_api_v1.delete_recommendation_feedback"),
            data=json.dumps(invalid_del_rec),
            headers={"Authorization": "Token {}".format(self.user["auth_token"])},
            content_type="application/json"
        )
        self.assert400(response)
        self.assertEqual(response.json["error"], "JSON document must only contain recording_mbid")

    def test_get_feedback_for_user(self):
        sample_feedback = self.insert_test_data()

        response = self.client.get(url_for("recommendation_feedback_api_v1.get_feedback_for_user", user_name=self.user1["musicbrainz_id"]))
        self.assert200(response)
        data = json.loads(response.data)

        self.assertEqual(data["count"], 2)
        self.assertEqual(data["total_count"], 2)
        self.assertEqual(data["offset"], 0)
        self.assertEqual(data['user_name'], self.user1['musicbrainz_id'])

        feedback = data["recommendation-feedback"]  # sorted in descending order of their creation
        self.assertEqual(len(feedback), 2)

        self.assertEqual(feedback[0]["recording_mbid"], sample_feedback[1]["recording_mbid"])
        self.assertEqual(feedback[0]["rating"], sample_feedback[1]["rating"])
        self.assertNotIn("user_id", feedback[0])
        self.assertEqual(type(feedback[0]['created']), int)

        self.assertEqual(feedback[1]["recording_mbid"], sample_feedback[0]["recording_mbid"])
        self.assertEqual(feedback[1]["rating"], sample_feedback[0]["rating"])
        self.assertNotIn("user_id", feedback[0])
        self.assertEqual(type(feedback[0]['created']), int)

    def test_get_feedback_for_user_invalid_user(self):
        """ Test to make sure that the API sends 404 if user does not exist. """
        response = self.client.get(url_for("recommendation_feedback_api_v1.get_feedback_for_user", user_name="invalid"))
        self.assert404(response)

    def test_get_feedback_for_user_with_rating_param(self):
        sample_feedback = self.insert_test_data()

        response = self.client.get(url_for("recommendation_feedback_api_v1.get_feedback_for_user",
                                   user_name=self.user1["musicbrainz_id"]), query_string={"rating": 'hate'})
        self.assert200(response)
        data = json.loads(response.data)

        self.assertEqual(data["count"], 1)
        self.assertEqual(data["total_count"], len(sample_feedback))
        self.assertEqual(data["offset"], 0)
        self.assertEqual(data['user_name'], self.user1['musicbrainz_id'])

        feedback = data["recommendation-feedback"]  # sorted in descending order of their creation
        self.assertEqual(len(feedback), 1)

        self.assertEqual(feedback[0]["recording_mbid"], sample_feedback[1]["recording_mbid"])
        self.assertEqual(feedback[0]["rating"], 'hate')
        self.assertNotIn("user_id", feedback[0])
        self.assertEqual(type(feedback[0]['created']), int)

    def test_get_feedback_for_user_with_invalid_rating_param(self):
        """ Test to make sure 400 response is received if rating argument is not valid """
        response = self.client.get(url_for("recommendation_feedback_api_v1.get_feedback_for_user",
                                   user_name=self.user1["musicbrainz_id"]), query_string={"rating": "invalid"})
        self.assert400(response)

    def test_get_feedback_for_user_for_count_and_offset(self):
        """ Test to make sure valid response is received when count rating is passed """
        feedback_love = []
        for i in range(110):
            rec_mbid = str(uuid.uuid4())
            db_feedback.insert(
                RecommendationFeedbackSubmit(
                    user_id=self.user2['id'],
                    recording_mbid=rec_mbid,
                    rating='love'
                )
            )

            # prepended to the list since ``get_feedback_for_users`` returns data in descending
            # order of creation.
            feedback_love.insert(
                0,
                {
                    'recording_mbid': rec_mbid,
                    'rating': 'love'
                }
            )
        # check for count
        response = self.client.get(url_for("recommendation_feedback_api_v1.get_feedback_for_user",
                                   user_name=self.user2["musicbrainz_id"]), query_string={"count": 10})
        self.assert200(response)
        data = json.loads(response.data)

        self.assertEqual(data["count"], 10)
        self.assertEqual(data["total_count"], 110)
        self.assertEqual(data["offset"], 0)
        self.assertEqual(data["user_name"], self.user2['musicbrainz_id'])

        feedback = data["recommendation-feedback"]
        self.assertEqual(len(feedback), 10)
        for i in range(10):
            self.assertEqual(feedback[i]['recording_mbid'], feedback_love[i]['recording_mbid'])
            self.assertEqual(feedback[i]['rating'], feedback_love[i]['rating'])

        # check for offset
        response = self.client.get(url_for("recommendation_feedback_api_v1.get_feedback_for_user",
                                   user_name=self.user2["musicbrainz_id"]), query_string={"offset": 90})
        self.assert200(response)
        data = json.loads(response.data)

        self.assertEqual(data["count"], 20)
        self.assertEqual(data["total_count"], 110)
        self.assertEqual(data["offset"], 90)
        self.assertEqual(data["user_name"], self.user2['musicbrainz_id'])

        feedback = data["recommendation-feedback"]  # sorted in descending order of their creation
        self.assertEqual(len(feedback), 20)
        for i in range(10):
            self.assertEqual(feedback[i]['recording_mbid'], feedback_love[i+90]['recording_mbid'])
            self.assertEqual(feedback[i]['rating'], feedback_love[i+90]['rating'])
        # check for feedback, too many
        response = self.client.get(url_for("recommendation_feedback_api_v1.get_feedback_for_user",
                                   user_name=self.user2["musicbrainz_id"]), query_string={"count": 110})
        self.assert200(response)
        data = json.loads(response.data)

        self.assertEqual(data["count"], 100)
        self.assertEqual(data["total_count"], 110)
        self.assertEqual(data["offset"], 0)
        self.assertEqual(data["user_name"], self.user2['musicbrainz_id'])

        feedback = data["recommendation-feedback"]  # sorted in descending order of their creation
        self.assertEqual(len(feedback), 100)
        for i in range(100):
            self.assertEqual(feedback[i]['recording_mbid'], feedback_love[i]['recording_mbid'])
            self.assertEqual(feedback[i]['rating'], feedback_love[i]['rating'])

    def test_get_feedback_for_user_with_invalid_count_param(self):
        """ Test to make sure 400 response is received if count argument is not valid """

        # pass non-int value to count
        response = self.client.get(url_for("recommendation_feedback_api_v1.get_feedback_for_user",
                                   user_name=self.user["musicbrainz_id"]), query_string={"count": "invalid_count"})
        self.assert400(response)

        # pass negative int value to count
        response = self.client.get(url_for("recommendation_feedback_api_v1.get_feedback_for_user",
                                   user_name=self.user["musicbrainz_id"]), query_string={"count": -1})
        self.assert400(response)

    def test_get_feedback_for_user_with_invalid_offset_param(self):
        """ Test to make sure 400 response is received if offset argument is not valid """

        # pass non-int value to offset
        response = self.client.get(url_for("recommendation_feedback_api_v1.get_feedback_for_user",
                                   user_name=self.user["musicbrainz_id"]), query_string={"offset": "invalid_offset"})
        self.assert400(response)

        # pass negative int value to offset
        response = self.client.get(url_for("recommendation_feedback_api_v1.get_feedback_for_user",
                                   user_name=self.user["musicbrainz_id"]), query_string={"offset": -1})
        self.assert400(response)
