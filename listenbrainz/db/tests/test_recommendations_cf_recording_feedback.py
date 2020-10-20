# -*- coding: utf-8 -*-
import json
import os
import uuid
from listenbrainz.db.model.recommendation_feedback import (RecommendationFeedbackSubmit,
                                                           RecommendationFeedbackDelete,
                                                           get_allowed_ratings)
import listenbrainz.db.recommendations_cf_recording_feedback as db_feedback
import listenbrainz.db.user as db_user

from listenbrainz.db.testing import DatabaseTestCase


class RecommendationFeedbackDatabaseTestCase(DatabaseTestCase):

    def setUp(self):
        DatabaseTestCase.setUp(self)
        self.user = db_user.get_or_create(1, "vansika")
        self.user1 = db_user.get_or_create(2, "vansika_1")
        self.user2 = db_user.get_or_create(3, "vansika__2")

        self.sample_feedback = [
            {
                "recording_mbid": "d23f4719-9212-49f0-ad08-ddbfbfc50d6f",
                "rating": 'love',
                'user_id': self.user['id']
            },
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

    def insert_test_data(self):
        """ Insert test data into the database """

        for fb in self.sample_feedback:
            db_feedback.insert(
                RecommendationFeedbackSubmit(
                    user_id=fb['user_id'],
                    recording_mbid=fb["recording_mbid"],
                    rating=fb["rating"]
                )
            )

    def test_insert(self):
        self.insert_test_data()
        result = db_feedback.get_feedback_for_user(user_id=self.user['id'], limit=25, offset=0)
        self.assertEqual(len(result), 1)

        result = db_feedback.get_feedback_for_user(user_id=self.user1['id'], limit=25, offset=0)
        self.assertEqual(len(result), 2)

    def test_update_rating_when_feedback_already_exits(self):
        update_fb = self.sample_feedback[0]

        self.insert_test_data()
        result = db_feedback.get_feedback_for_user(user_id=self.user["id"], limit=25, offset=0)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].recording_mbid, update_fb['recording_mbid'])
        self.assertEqual(result[0].rating, 'love')

        new_rating = "like"  # change the score to -1

        # update a record by inserting a record with updated score value
        db_feedback.insert(
            RecommendationFeedbackSubmit(
                user_id=self.user["id"],
                recording_mbid=update_fb["recording_mbid"],
                rating=new_rating
            )
        )

        result = db_feedback.get_feedback_for_user(user_id=self.user["id"], limit=25, offset=0)
        self.assertEqual(len(result), 1)

        self.assertEqual(result[0].recording_mbid, update_fb["recording_mbid"])
        self.assertEqual(result[0].rating, 'like')

    def test_delete(self):
        del_fb = self.sample_feedback[1]

        self.insert_test_data()
        result = db_feedback.get_feedback_for_user(user_id=self.user1["id"], limit=25, offset=0)
        self.assertEqual(len(result), 2)

        db_feedback.delete(
            RecommendationFeedbackDelete(
                user_id=self.user1["id"],
                recording_mbid=del_fb["recording_mbid"],
            )
        )

        result = db_feedback.get_feedback_for_user(user_id=self.user1["id"], limit=25, offset=0)
        self.assertEqual(len(result), 1)

        self.assertNotEqual(result[0].recording_mbid, del_fb["recording_mbid"])

    def test_get_feedback_for_user(self):
        self.insert_test_data()
        result = db_feedback.get_feedback_for_user(user_id=self.user["id"], limit=25, offset=0)
        self.assertEqual(len(result), 1)

        self.assertEqual(result[0].user_id, self.user["id"])
        self.assertEqual(result[0].recording_mbid, self.sample_feedback[0]["recording_mbid"])
        self.assertEqual(result[0].rating, self.sample_feedback[0]["rating"])

        feedback_love = []
        for i in range(60):
            submit_obj = RecommendationFeedbackSubmit(
                user_id=self.user2['id'],
                recording_mbid=str(uuid.uuid4()),
                rating='love'
            )

            db_feedback.insert(submit_obj)
            # prepended to the list since ``get_feedback_for_users`` returns data in descending
            # order of creation.
            feedback_love.insert(0, submit_obj)

        feedback_hate = []
        for i in range(50):
            submit_obj = RecommendationFeedbackSubmit(
                user_id=self.user2['id'],
                recording_mbid=str(uuid.uuid4()),
                rating='hate'
            )

            db_feedback.insert(submit_obj)
            # prepended to the list since ``get_feedback_for_users`` returns data in descending
            # order of creation.
            feedback_hate.insert(0, submit_obj)
        # ``get_feddback_for_user`` will return feedback_hate data followed by feedback_love
        # data
        result = db_feedback.get_feedback_for_user(user_id=self.user2['id'], limit=120, offset=0)
        self.assertEqual(len(result), 110)

        # test the rating argument
        result = db_feedback.get_feedback_for_user(user_id=self.user2['id'], limit=70, offset=0, rating='love')
        self.assertEqual(len(result), 60)
        for i in range(60):
            self.assertEqual(result[i].user_id, feedback_love[i].user_id)
            self.assertEqual(result[i].recording_mbid, feedback_love[i].recording_mbid)
            self.assertEqual(result[i].rating, feedback_love[i].rating)

        result = db_feedback.get_feedback_for_user(user_id=self.user2['id'], limit=70, offset=0, rating='hate')
        self.assertEqual(len(result), 50)
        for i in range(50):
            self.assertEqual(result[i].user_id, feedback_hate[i].user_id)
            self.assertEqual(result[i].recording_mbid, feedback_hate[i].recording_mbid)
            self.assertEqual(result[i].rating, feedback_hate[i].rating)

        # test the limit argument
        result = db_feedback.get_feedback_for_user(user_id=self.user2['id'], limit=20, offset=0, rating='love')
        self.assertEqual(len(result), 20)
        for i in range(20):
            self.assertEqual(result[i].user_id, feedback_love[i].user_id)
            self.assertEqual(result[i].recording_mbid, feedback_love[i].recording_mbid)
            self.assertEqual(result[i].rating, feedback_love[i].rating)

        # test the offset argument
        result = db_feedback.get_feedback_for_user(user_id=self.user2['id'], limit=25, offset=10)
        self.assertEqual(len(result), 25)
        for i in range(25):
            self.assertEqual(result[i].user_id, feedback_hate[i+10].user_id)
            self.assertEqual(result[i].recording_mbid, feedback_hate[i+10].recording_mbid)
            self.assertEqual(result[i].rating, feedback_hate[i+10].rating)

        result = db_feedback.get_feedback_for_user(user_id=self.user2['id'], limit=25, offset=100)
        self.assertEqual(len(result), 10)
        for i in range(10):
            self.assertEqual(result[i].user_id, feedback_love[i+50].user_id)
            self.assertEqual(result[i].recording_mbid, feedback_love[i+50].recording_mbid)
            self.assertEqual(result[i].rating, feedback_love[i+50].rating)

        result = db_feedback.get_feedback_for_user(user_id=self.user2['id'], limit=30, offset=110)
        self.assertEqual(len(result), 0)

        result = db_feedback.get_feedback_for_user(user_id=self.user2['id'], limit=30, offset=30, rating='hate')
        self.assertEqual(len(result), 20)
        for i in range(20):
            self.assertEqual(result[i].user_id, feedback_hate[i+30].user_id)
            self.assertEqual(result[i].recording_mbid, feedback_hate[i+30].recording_mbid)
            self.assertEqual(result[i].rating, feedback_hate[i+30].rating)

    def test_get_feedback_count_for_user(self):
        self.insert_test_data()
        result = db_feedback.get_feedback_count_for_user(user_id=self.user1["id"])
        self.assertEqual(result, 2)
