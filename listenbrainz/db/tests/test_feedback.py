# -*- coding: utf-8 -*-
import json
import os
from listenbrainz.feedback import Feedback
import listenbrainz.db.feedback as db_feedback
import listenbrainz.db.user as db_user

from listenbrainz.db.testing import DatabaseTestCase


class FeedbackDatabaseTestCase(DatabaseTestCase):

    def setUp(self):
        DatabaseTestCase.setUp(self)
        self.user = db_user.get_or_create(1, 'recording_feedback_user')

        self.sample_feedback = [
            {
                "recording_msid": "d23f4719-9212-49f0-ad08-ddbfbfc50d6f",
                "score": 1
            },
            {
                "recording_msid": "222eb00d-9ead-42de-aec9-8f8c1509413d",
                "score": 1
            }
        ]
        self.sample_feedback_neg_score = [
            {
                "recording_msid": "d23f4719-9212-49f0-ad08-ddbfbfc50d6f",
                "score": -1
            },
            {
                "recording_msid": "31c2af1a-9968-47d3-b7a1-4a40d3a25f4f",
                "score": -1
            }
        ]

    def insert_test_data(self, user_id, neg_score=False):
        """ Insert test data into the database """

        if neg_score:
            # Insert the two records with negative score
            for fb_neg in self.sample_feedback_neg_score:
                db_feedback.insert(
                    Feedback(
                        user_id=user_id,
                        recording_msid=fb_neg["recording_msid"],
                        score=fb_neg["score"]
                    )
                )
            return

        # Insert the two records with positive score
        for fb in self.sample_feedback:
            db_feedback.insert(
                Feedback(
                    user_id=user_id,
                    recording_msid=fb["recording_msid"],
                    score=fb["score"]
                )
            )

    def test_insert(self):
        self.insert_test_data(self.user['id'])
        result = db_feedback.get_feedback_by_user_id(self.user['id'])
        self.assertEqual(len(result), 2)

    def test_update_score_when_feedback_already_exits(self):
        self.insert_test_data(self.user['id'])
        result = db_feedback.get_feedback_by_user_id(self.user['id'])
        self.assertEqual(len(result), 2)

        # insert the negative score records, where 1 recording_msid already exists
        # with postive score for the given user
        self.insert_test_data(self.user['id'], neg_score=True)
        result = db_feedback.get_feedback_by_user_id(self.user['id'])
        self.assertEqual(len(result), 3)

    def test_delete(self):
        self.insert_test_data(self.user['id'])
        result = db_feedback.get_feedback_by_user_id(self.user['id'])
        self.assertEqual(len(result), 2)

        # delete one record for the user
        del_fb = self.sample_feedback[0]
        db_feedback.delete(
            Feedback(
                user_id=self.user['id'],
                recording_msid=del_fb["recording_msid"],
                score=del_fb["score"]
            )
        )

        result = db_feedback.get_feedback_by_user_id(self.user['id'])
        self.assertEqual(len(result), 1)

        self.assertNotEqual(result[0].recording_msid, del_fb["recording_msid"])

    def test_get_feedback_by_user_id(self):
        self.insert_test_data(self.user['id'])
        result = db_feedback.get_feedback_by_user_id(self.user['id'])
        self.assertEqual(len(result), 2)

        self.assertEqual(result[0].score, 1)
        self.assertEqual(result[1].score, 1)

        # insert the negative score records
        self.insert_test_data(self.user['id'], neg_score=True)
        result = db_feedback.get_feedback_by_user_id(self.user['id'])
        self.assertEqual(len(result), 3)

        self.assertEqual(result[0].score, -1)
        self.assertEqual(result[1].score, -1)
        self.assertEqual(result[2].score, 1)

    def test_get_feedback_by_user__id_and_score(self):
        self.insert_test_data(self.user['id'])
        result = db_feedback.get_feedback_by_user__id_and_score(self.user['id'], 1)
        self.assertEqual(len(result), 2)

        self.assertEqual(result[0].score, 1)
        self.assertEqual(result[1].score, 1)

        # insert the negative score records
        self.insert_test_data(self.user['id'], neg_score=True)
        result = db_feedback.get_feedback_by_user__id_and_score(self.user['id'], -1)
        self.assertEqual(len(result), 2)

        self.assertEqual(result[0].score, -1)
        self.assertEqual(result[1].score, -1)

    def test_get_feedback_by_recording_msid(self):
        fb_msid_1 = self.sample_feedback[0]["recording_msid"]
        fb_msid_2 = self.sample_feedback[1]["recording_msid"]

        self.insert_test_data(self.user['id'])

        result = db_feedback.get_feedback_by_recording_msid(fb_msid_1)
        self.assertEqual(len(result), 1)
        result = db_feedback.get_feedback_by_recording_msid(fb_msid_2)
        self.assertEqual(len(result), 1)

        user2 = db_user.get_or_create(2, 'recording_feedback_other_user')
        self.insert_test_data(user2['id'])

        result = db_feedback.get_feedback_by_recording_msid(fb_msid_1)
        self.assertEqual(len(result), 2)
        result = db_feedback.get_feedback_by_recording_msid(fb_msid_2)
        self.assertEqual(len(result), 2)
