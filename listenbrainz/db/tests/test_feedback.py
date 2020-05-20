# -*- coding: utf-8 -*-
import json
import os
import listenbrainz.db.feedback as db_feedback
import listenbrainz.db.user as db_user

from listenbrainz.db.testing import DatabaseTestCase

class FeedbackDatabaseTestCase(DatabaseTestCase):


    def setUp(self):
        DatabaseTestCase.setUp(self)
        self.user = db_user.get_or_create(1, 'recording_feedback_user')


    def insert_test_data(self, user_id, neg_score=False):
        """ Insert test data into the database """

        if neg_score:
            # Insert the two records with negative score
            with open(self.path_to_data_file('recording_feedback_negative_score.json')) as f:
                rec_feedback_neg_score = json.load(f)

            for fb_neg in rec_feedback_neg_score:
                db_feedback.insert(user_id, fb_neg["recording_msid"], fb_neg["score"])

            return
    
        # Insert the two records with positive score
        with open(self.path_to_data_file('recording_feedback.json')) as f:
            rec_feedback = json.load(f)

        for fb in rec_feedback:
            db_feedback.insert(user_id, fb["recording_msid"], fb["score"])


    def test_insert(self):
        self.insert_test_data(self.user['id'])
        result = db_feedback.get_feedback(self.user['id'])
        self.assertEqual(len(result), 2)


    def test_update_score_when_feedback_already_exits(self):
        self.insert_test_data(self.user['id'])
        result = db_feedback.get_feedback(self.user['id'])
        self.assertEqual(len(result), 2)

        # insert the negative score records, where 1 recording_msid already exists 
        # with postive score for the given user
        self.insert_test_data(self.user['id'], neg_score=True)
        result = db_feedback.get_feedback(self.user['id'])
        self.assertEqual(len(result), 3)

    def test_delete(self):
        self.insert_test_data(self.user['id'])
        result = db_feedback.get_feedback(self.user['id'])
        self.assertEqual(len(result), 2)

        # delete one record for the user
        del_rec_msid = "d23f4719-9212-49f0-ad08-ddbfbfc50d6f"
        db_feedback.delete(self.user['id'], del_rec_msid)

        result = db_feedback.get_feedback(self.user['id'])
        self.assertEqual(len(result), 1)

        self.assertNotEqual(result[0]["recording_msid"], del_rec_msid)


    def test_get_feedback(self):
        self.insert_test_data(self.user['id'])
        result = db_feedback.get_feedback(self.user['id'])
        self.assertEqual(len(result), 2)

        self.assertEqual(result[0]["score"], 1)
        self.assertEqual(result[1]["score"], 1)

        # insert the negative score records
        self.insert_test_data(self.user['id'], neg_score=True)
        result = db_feedback.get_feedback(self.user['id'])
        self.assertEqual(len(result), 3)

        self.assertEqual(result[0]["score"], -1)
        self.assertEqual(result[1]["score"], -1)
        self.assertEqual(result[2]["score"], 1)


    def test_get_feedback_single_type(self):
        self.insert_test_data(self.user['id'])
        result = db_feedback.get_feedback_single_type(self.user['id'], 1)
        self.assertEqual(len(result), 2)

        self.assertEqual(result[0]["score"], 1)
        self.assertEqual(result[1]["score"], 1)

        # insert the negative score records
        self.insert_test_data(self.user['id'], neg_score=True)
        result = db_feedback.get_feedback_single_type(self.user['id'], -1)
        self.assertEqual(len(result), 2)

        self.assertEqual(result[0]["score"], -1)
        self.assertEqual(result[1]["score"], -1)


    def test_get_feedback_for_recording(self):
        rec_msid_1 = "d23f4719-9212-49f0-ad08-ddbfbfc50d6f"
        rec_msid_2 = "222eb00d-9ead-42de-aec9-8f8c1509413d"

        self.insert_test_data(self.user['id'])

        result = db_feedback.get_feedback_for_recording(rec_msid_1)
        self.assertEqual(len(result), 1)
        result = db_feedback.get_feedback_for_recording(rec_msid_2)
        self.assertEqual(len(result), 1)

        user2 = db_user.get_or_create(2, 'recording_feedback_other_user')
        self.insert_test_data(user2['id'])

        result = db_feedback.get_feedback_for_recording(rec_msid_1)
        self.assertEqual(len(result), 2)
        result = db_feedback.get_feedback_for_recording(rec_msid_2)
        self.assertEqual(len(result), 2)
