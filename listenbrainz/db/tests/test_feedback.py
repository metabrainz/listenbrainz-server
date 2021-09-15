# -*- coding: utf-8 -*-
import json
import os

import sqlalchemy

from listenbrainz import config
from listenbrainz.db.model.feedback import Feedback
import listenbrainz.db.feedback as db_feedback
import listenbrainz.db.user as db_user
from listenbrainz.db import timescale as ts
from messybrainz import db as msb_db
from messybrainz.db.data import submit_recording, load_recordings_from_msids
from listenbrainz.db.testing import DatabaseTestCase, TimescaleTestCase, MessyBrainzTestCase


class FeedbackDatabaseTestCase(DatabaseTestCase, TimescaleTestCase, MessyBrainzTestCase):

    def setUp(self):
        DatabaseTestCase.setUp(self)
        TimescaleTestCase.setUp(self)
        MessyBrainzTestCase.setUp(self)
        self.user = db_user.get_or_create(1, "recording_feedback_user")

        self.sample_feedback = [
            {
                "recording_msid": "d23f4719-9212-49f0-ad08-ddbfbfc50d6f",
                "score": 1
            },
            {
                "recording_msid": "222eb00d-9ead-42de-aec9-8f8c1509413d",
                "score": -1
            }
        ]
        self.sample_recording = {
            "title": "Strangers",
            "artist": "Portishead"
        }
        self.sample_feedback_with_metadata = [
            {
                "recording_msid": "",
                "score": 1
            }
        ]
        self.saved_artist_msid = None

    def insert_test_data(self, user_id, neg_score=False):
        """ Insert test data into the database """

        for fb in self.sample_feedback:
            db_feedback.insert(
                Feedback(
                    user_id=user_id,
                    recording_msid=fb["recording_msid"],
                    score=fb["score"]
                )
            )

        return len(self.sample_feedback)

    def insert_test_data_with_metadata(self, user_id, neg_score=False):
        """ Insert test data with metadata into the database """

        with msb_db.engine.connect() as connection:
            msid = submit_recording(connection, self.sample_recording)
            artists = load_recordings_from_msids(connection, [msid])
            self.saved_artist_msid = artists[0]["ids"]["artist_msid"]

        self.sample_feedback_with_metadata[0]["recording_msid"] = msid

        query = """INSERT INTO listen_mbid_mapping
                               (recording_msid, recording_mbid, release_mbid, artist_credit_id,
                                artist_credit_name, recording_name, match_type)
                               values ('%s',
                                       '076255b4-1575-11ec-ac84-135bf6a670e3',
                                       '1fd178b4-1575-11ec-b98a-d72392cd8c97',
                                       65, 'artist name', 'recording name', 'exact_match')""" % msid

        with ts.engine.connect() as connection:
            connection.execute(sqlalchemy.text(query))

        for fb in self.sample_feedback_with_metadata:
            db_feedback.insert(
                Feedback(
                    user_id=user_id,
                    recording_msid=fb["recording_msid"],
                    score=fb["score"]
                )
            )

        return len(self.sample_feedback_with_metadata)


    def test_insert(self):
        count = self.insert_test_data(self.user["id"])
        result = db_feedback.get_feedback_for_user(user_id=self.user["id"], limit=25, offset=0)
        self.assertEqual(len(result), count)

    def test_update_score_when_feedback_already_exits(self):
        update_fb = self.sample_feedback[0]

        count = self.insert_test_data(self.user["id"])
        result = db_feedback.get_feedback_for_user(user_id=self.user["id"], limit=25, offset=0)
        self.assertEqual(len(result), count)

        self.assertEqual(result[1].recording_msid, update_fb["recording_msid"])
        self.assertEqual(result[1].score, 1)

        update_fb["score"] = -1  # change the score to -1

        # update a record by inserting a record with updated score value
        db_feedback.insert(
            Feedback(
                user_id=self.user["id"],
                recording_msid=update_fb["recording_msid"],
                score=update_fb["score"]
            )
        )

        result = db_feedback.get_feedback_for_user(user_id=self.user["id"], limit=25, offset=0)
        self.assertEqual(len(result), count)

        self.assertEqual(result[0].recording_msid, update_fb["recording_msid"])
        self.assertEqual(result[0].score, -1)

    def test_delete(self):
        del_fb = self.sample_feedback[0]

        count = self.insert_test_data(self.user["id"])
        result = db_feedback.get_feedback_for_user(user_id=self.user["id"], limit=25, offset=0)
        self.assertEqual(len(result), count)
        self.assertEqual(result[1].recording_msid, del_fb["recording_msid"])

        # delete one record for the user
        db_feedback.delete(
            Feedback(
                user_id=self.user["id"],
                recording_msid=del_fb["recording_msid"],
                score=del_fb["score"]
            )
        )

        result = db_feedback.get_feedback_for_user(user_id=self.user["id"], limit=25, offset=0)
        self.assertEqual(len(result), 1)

        self.assertNotEqual(result[0].recording_msid, del_fb["recording_msid"])

    def test_get_feedback_for_user(self):
        count = self.insert_test_data(self.user["id"])
        result = db_feedback.get_feedback_for_user(user_id=self.user["id"], limit=25, offset=0)
        self.assertEqual(len(result), count)

        self.assertEqual(result[0].user_id, self.user["id"])
        self.assertEqual(result[0].user_name, self.user["musicbrainz_id"])
        self.assertEqual(result[0].recording_msid, self.sample_feedback[1]["recording_msid"])
        self.assertEqual(result[0].score, self.sample_feedback[1]["score"])

        self.assertEqual(result[1].user_id, self.user["id"])
        self.assertEqual(result[1].user_name, self.user["musicbrainz_id"])
        self.assertEqual(result[1].recording_msid, self.sample_feedback[0]["recording_msid"])
        self.assertEqual(result[1].score, self.sample_feedback[0]["score"])

        # test the score argument
        result = db_feedback.get_feedback_for_user(user_id=self.user["id"], limit=25, offset=0, score=1)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].score, 1)

        result = db_feedback.get_feedback_for_user(user_id=self.user["id"], limit=25, offset=0, score=-1)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].score, -1)

        # test the limit argument
        result = db_feedback.get_feedback_for_user(user_id=self.user["id"], limit=1, offset=0)
        self.assertEqual(len(result), 1)

        # test the offset argument
        result = db_feedback.get_feedback_for_user(user_id=self.user["id"], limit=25, offset=1)
        self.assertEqual(len(result), 1)

    def test_get_feedback_for_user_with_metadata(self):
        count = self.insert_test_data_with_metadata(self.user["id"])
        result = db_feedback.get_feedback_for_user(user_id=self.user["id"], limit=25, offset=0, score=1, metadata=True)
        self.assertEqual(len(result), 1)

        print(result[0])
        self.assertEqual(result[0].user_id, self.user["id"])
        self.assertEqual(result[0].user_name, self.user["musicbrainz_id"])
        self.assertEqual(result[0].recording_msid, self.sample_feedback_with_metadata[0]["recording_msid"])
        self.assertEqual(result[0].score, self.sample_feedback_with_metadata[0]["score"])
        self.assertEqual(result[0].track_metadata["artist_name"], "Portishead")
        self.assertEqual(result[0].track_metadata["track_name"], "Strangers")
        self.assertEqual(result[0].track_metadata["additional_info"]["recording_mbid"], "076255b4-1575-11ec-ac84-135bf6a670e3")
        self.assertEqual(result[0].track_metadata["additional_info"]["release_mbid"], "1fd178b4-1575-11ec-b98a-d72392cd8c97")
        self.assertEqual(result[0].track_metadata["additional_info"]["artist_msid"], self.saved_artist_msid)


    def test_get_feedback_count_for_user(self):
        count = self.insert_test_data(self.user["id"])
        result = db_feedback.get_feedback_count_for_user(user_id=self.user["id"])
        self.assertEqual(result, count)

        result = db_feedback.get_feedback_count_for_user(user_id=self.user["id"], score=1)
        self.assertEqual(result, 1)

        result = db_feedback.get_feedback_count_for_user(user_id=self.user["id"], score=-1)
        self.assertEqual(result, 1)

    def test_get_feedback_for_recording(self):
        fb_msid_1 = self.sample_feedback[0]["recording_msid"]

        self.insert_test_data(self.user["id"])
        result = db_feedback.get_feedback_for_recording(recording_msid=fb_msid_1, limit=25, offset=0)
        self.assertEqual(len(result), 1)

        self.assertEqual(result[0].user_id, self.user["id"])
        self.assertEqual(result[0].user_name, self.user["musicbrainz_id"])
        self.assertEqual(result[0].recording_msid, fb_msid_1)
        self.assertEqual(result[0].score, self.sample_feedback[0]["score"])

        user2 = db_user.get_or_create(2, "recording_feedback_other_user")
        self.insert_test_data(user2["id"])

        result = db_feedback.get_feedback_for_recording(recording_msid=fb_msid_1, limit=25, offset=0)
        self.assertEqual(len(result), 2)

        self.assertEqual(result[0].user_id, user2["id"])
        self.assertEqual(result[0].user_name, user2["musicbrainz_id"])
        self.assertEqual(result[0].recording_msid, fb_msid_1)
        self.assertEqual(result[0].score, self.sample_feedback[0]["score"])

        self.assertEqual(result[1].user_id, self.user["id"])
        self.assertEqual(result[1].user_name, self.user["musicbrainz_id"])
        self.assertEqual(result[1].recording_msid, fb_msid_1)
        self.assertEqual(result[1].score, self.sample_feedback[0]["score"])

        # test the score argument
        result = db_feedback.get_feedback_for_recording(recording_msid=fb_msid_1, limit=25, offset=0, score=1)
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0].score, 1)
        self.assertEqual(result[1].score, 1)

        result = db_feedback.get_feedback_for_recording(recording_msid=fb_msid_1, limit=25, offset=0, score=-1)
        self.assertEqual(len(result), 0)

        # test the limit argument
        result = db_feedback.get_feedback_for_recording(recording_msid=fb_msid_1, limit=1, offset=0)
        self.assertEqual(len(result), 1)

        # test the offset argument
        result = db_feedback.get_feedback_for_recording(recording_msid=fb_msid_1, limit=25, offset=1)
        self.assertEqual(len(result), 1)

    def test_get_feedback_count_for_recording(self):
        fb_msid_1 = self.sample_feedback[0]["recording_msid"]

        self.insert_test_data(self.user["id"])
        result = db_feedback.get_feedback_count_for_recording(recording_msid=fb_msid_1)
        self.assertEqual(result, 1)

        user2 = db_user.get_or_create(2, "recording_feedback_other_user")
        self.insert_test_data(user2["id"])

        result = db_feedback.get_feedback_count_for_recording(recording_msid=fb_msid_1)
        self.assertEqual(result, 2)

    def test_get_feedback_for_multiple_recordings_for_user(self):
        self.insert_test_data(self.user["id"])

        recording_list = []

        # recording_msids for which feedback records are inserted
        recording_list.append(self.sample_feedback[0]["recording_msid"])
        recording_list.append(self.sample_feedback[1]["recording_msid"])

        # recording_msid for which feedback record doesn't exist
        recording_list.append("b83fd3c3-449c-49be-a874-31d7cf26d946")

        result = db_feedback.get_feedback_for_multiple_recordings_for_user(
                                                                           user_id=self.user["id"],
                                                                           recording_list=recording_list
                                                                          )
        self.assertEqual(len(result), len(recording_list))

        # test correct score is returned for recording_msids for which feedback records are inserted
        self.assertEqual(result[0].user_id, self.user["id"])
        self.assertEqual(result[0].user_name, self.user["musicbrainz_id"])
        self.assertEqual(result[0].recording_msid, recording_list[0])
        self.assertEqual(result[0].score, self.sample_feedback[0]["score"])

        self.assertEqual(result[1].user_id, self.user["id"])
        self.assertEqual(result[1].user_name, self.user["musicbrainz_id"])
        self.assertEqual(result[1].recording_msid, recording_list[1])
        self.assertEqual(result[1].score, self.sample_feedback[1]["score"])

        # test score = 0 is returned for recording_msids for which feedback records are inserted
        self.assertEqual(result[2].user_id, self.user["id"])
        self.assertEqual(result[2].user_name, self.user["musicbrainz_id"])
        self.assertEqual(result[2].recording_msid, recording_list[2])
        self.assertEqual(result[2].score, 0)
