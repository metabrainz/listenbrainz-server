import sqlalchemy

from listenbrainz.db.model.feedback import Feedback
import listenbrainz.db.feedback as db_feedback
import listenbrainz.db.user as db_user
from listenbrainz.db import timescale as ts, timescale
from listenbrainz import messybrainz as msb_db
from listenbrainz.db.testing import DatabaseTestCase, TimescaleTestCase


class FeedbackDatabaseTestCase(DatabaseTestCase, TimescaleTestCase):

    def setUp(self):
        DatabaseTestCase.setUp(self)
        TimescaleTestCase.setUp(self)
        self.user = db_user.get_or_create(1, "recording_feedback_user")

        self.sample_feedback = [
            {
                "recording_msid": "d23f4719-9212-49f0-ad08-ddbfbfc50d6f",
                "recording_mbid": None,
                "score": 1
            },
            {
                "recording_msid": "222eb00d-9ead-42de-aec9-8f8c1509413d",
                "recording_mbid": None,
                "score": -1
            },
            {
                "recording_msid": None,
                "recording_mbid": "9541592c-0102-4b94-93cc-ee0f3cf83d64",
                "score": 1
            },
            {
                "recording_msid": "9d008211-c920-4ff7-a17f-b86e4246c58c",
                "recording_mbid": "e7ebbb99-7346-4323-9541-dffae9e1003b",
                "score": -1
            }
        ]
        self.sample_recording = {
            "title": "Strangers",
            "artist": "Portishead",
            "release": None
        }
        self.sample_feedback_with_metadata = [
            {
                "recording_msid": "",
                "score": 1
            }
        ]

    def insert_test_data(self, user_id):
        """ Insert test data into the database """

        for fb in self.sample_feedback:
            db_feedback.insert(
                Feedback(
                    user_id=user_id,
                    recording_msid=fb["recording_msid"],
                    recording_mbid=fb["recording_mbid"],
                    score=fb["score"]
                )
            )

        return len(self.sample_feedback)

    def insert_test_data_with_metadata(self, user_id):
        """ Insert test data with metadata into the database """
        msid = msb_db.insert_all_in_transaction([self.sample_recording])[0]

        self.sample_feedback_with_metadata[0]["recording_msid"] = msid

        query = """INSERT INTO mbid_mapping_metadata
                               (recording_mbid, release_mbid, release_name, artist_credit_id,
                                artist_mbids, artist_credit_name, recording_name)
                        VALUES ('076255b4-1575-11ec-ac84-135bf6a670e3',
                                '1fd178b4-1575-11ec-b98a-d72392cd8c97',
                                'release_name',
                                65,
                                '{6a221fda-2200-11ec-ac7d-dfa16a57158f}'::UUID[],
                                'Portishead', 'Strangers')"""

        with ts.engine.begin() as connection:
            connection.execute(sqlalchemy.text(query))

        query = """INSERT INTO mbid_mapping
                               (recording_msid, recording_mbid, match_type, last_updated)
                        VALUES (:msid, :mbid, :match_type, now())"""

        with ts.engine.begin() as connection:
            connection.execute(sqlalchemy.text(query),
                               {"msid": msid, "mbid": "076255b4-1575-11ec-ac84-135bf6a670e3", "match_type": "exact_match"})

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

    def test_update_score_when_feedback_already_exist(self):
        update_fb = self.sample_feedback[0]

        count = self.insert_test_data(self.user["id"])
        result = db_feedback.get_feedback_for_user(user_id=self.user["id"], limit=25, offset=0)
        self.assertEqual(len(result), count)

        self.assertEqual(result[3].recording_msid, update_fb["recording_msid"])
        self.assertEqual(result[3].score, 1)

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
        self.assertEqual(result[3].recording_msid, del_fb["recording_msid"])

        # delete one record for the user using msid
        db_feedback.delete(
            Feedback(
                user_id=self.user["id"],
                recording_msid=del_fb["recording_msid"],
                score=del_fb["score"]
            )
        )

        result = db_feedback.get_feedback_for_user(user_id=self.user["id"], limit=25, offset=0)
        self.assertEqual(len(result), 3)
        self.assertNotIn(del_fb["recording_msid"], [x.recording_msid for x in result])

        # delete using mbid
        db_feedback.delete(
            Feedback(
                user_id=self.user["id"],
                recording_mbid=self.sample_feedback[2]["recording_mbid"],
                score=self.sample_feedback[2]["score"]
            )
        )
        result = db_feedback.get_feedback_for_user(user_id=self.user["id"], limit=25, offset=0)
        self.assertEqual(len(result), 2)
        self.assertNotIn(self.sample_feedback[2]["recording_mbid"], [x.recording_mbid for x in result])

        # delete using mbid and msid both
        db_feedback.delete(
            Feedback(
                user_id=self.user["id"],
                recording_mbid=self.sample_feedback[3]["recording_mbid"],
                recording_msid=self.sample_feedback[3]["recording_msid"],
                score=self.sample_feedback[2]["score"]
            )
        )
        result = db_feedback.get_feedback_for_user(user_id=self.user["id"], limit=25, offset=0)
        self.assertEqual(len(result), 1)
        self.assertNotIn(self.sample_feedback[3]["recording_mbid"], [x.recording_mbid for x in result])

    def test_get_feedback_for_user(self):
        count = self.insert_test_data(self.user["id"])
        result = db_feedback.get_feedback_for_user(user_id=self.user["id"], limit=25, offset=0)
        self.assertEqual(len(result), count)

        self.assertEqual(result[0].user_id, self.user["id"])
        self.assertEqual(result[0].user_name, self.user["musicbrainz_id"])
        self.assertEqual(result[0].recording_msid, self.sample_feedback[3]["recording_msid"])
        self.assertEqual(result[0].recording_mbid, self.sample_feedback[3]["recording_mbid"])
        self.assertEqual(result[0].score, self.sample_feedback[3]["score"])

        self.assertEqual(result[1].user_id, self.user["id"])
        self.assertEqual(result[1].user_name, self.user["musicbrainz_id"])
        self.assertEqual(result[1].recording_msid, self.sample_feedback[2]["recording_msid"])
        self.assertEqual(result[1].recording_mbid, self.sample_feedback[2]["recording_mbid"])
        self.assertEqual(result[1].score, self.sample_feedback[2]["score"])

        self.assertEqual(result[2].user_id, self.user["id"])
        self.assertEqual(result[2].user_name, self.user["musicbrainz_id"])
        self.assertEqual(result[2].recording_msid, self.sample_feedback[1]["recording_msid"])
        self.assertEqual(result[2].recording_mbid, self.sample_feedback[1]["recording_mbid"])
        self.assertEqual(result[2].score, self.sample_feedback[1]["score"])

        self.assertEqual(result[3].user_id, self.user["id"])
        self.assertEqual(result[3].user_name, self.user["musicbrainz_id"])
        self.assertEqual(result[3].recording_msid, self.sample_feedback[0]["recording_msid"])
        self.assertEqual(result[3].recording_mbid, self.sample_feedback[0]["recording_mbid"])
        self.assertEqual(result[3].score, self.sample_feedback[0]["score"])

        # test the score argument
        result = db_feedback.get_feedback_for_user(user_id=self.user["id"], limit=25, offset=0, score=1)
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0].score, 1)
        self.assertEqual(result[1].score, 1)

        result = db_feedback.get_feedback_for_user(user_id=self.user["id"], limit=25, offset=0, score=-1)
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0].score, -1)
        self.assertEqual(result[1].score, -1)

        # test the limit argument
        result = db_feedback.get_feedback_for_user(user_id=self.user["id"], limit=1, offset=0)
        self.assertEqual(len(result), 1)

        # test the offset argument
        result = db_feedback.get_feedback_for_user(user_id=self.user["id"], limit=25, offset=1)
        self.assertEqual(len(result), 3)

    def test_get_feedback_for_user_with_metadata(self):
        count = self.insert_test_data_with_metadata(self.user["id"])
        result = db_feedback.get_feedback_for_user(user_id=self.user["id"], limit=25, offset=0, score=1, metadata=True)
        self.assertEqual(len(result), 1)

        self.assertEqual(result[0].user_id, self.user["id"])
        self.assertEqual(result[0].user_name, self.user["musicbrainz_id"])
        self.assertEqual(result[0].recording_msid, self.sample_feedback_with_metadata[0]["recording_msid"])
        self.assertEqual(result[0].score, self.sample_feedback_with_metadata[0]["score"])
        self.assertEqual(result[0].track_metadata["artist_name"], "Portishead")
        self.assertEqual(result[0].track_metadata["track_name"], "Strangers")
        self.assertEqual(result[0].track_metadata["additional_info"]["recording_mbid"], "076255b4-1575-11ec-ac84-135bf6a670e3")
        self.assertEqual(result[0].track_metadata["additional_info"]["release_mbid"], "1fd178b4-1575-11ec-b98a-d72392cd8c97")

    def test_get_feedback_count_for_user(self):
        count = self.insert_test_data(self.user["id"])
        result = db_feedback.get_feedback_count_for_user(user_id=self.user["id"])
        self.assertEqual(result, count)

        result = db_feedback.get_feedback_count_for_user(user_id=self.user["id"], score=1)
        self.assertEqual(result, 2)

        result = db_feedback.get_feedback_count_for_user(user_id=self.user["id"], score=-1)
        self.assertEqual(result, 2)

    def test_get_feedback_for_recording(self):
        fb_msid_1 = self.sample_feedback[0]["recording_msid"]

        self.insert_test_data(self.user["id"])
        result = db_feedback.get_feedback_for_recording("recording_msid", fb_msid_1, limit=25, offset=0)
        self.assertEqual(len(result), 1)

        self.assertEqual(result[0].user_id, self.user["id"])
        self.assertEqual(result[0].user_name, self.user["musicbrainz_id"])
        self.assertEqual(result[0].recording_msid, fb_msid_1)
        self.assertEqual(result[0].score, self.sample_feedback[0]["score"])

        fb_mbid = self.sample_feedback[3]["recording_mbid"]
        result = db_feedback.get_feedback_for_recording("recording_mbid", fb_mbid, limit=25, offset=0)
        self.assertEqual(len(result), 1)

        self.assertEqual(result[0].user_id, self.user["id"])
        self.assertEqual(result[0].user_name, self.user["musicbrainz_id"])
        self.assertEqual(result[0].recording_mbid, fb_mbid)
        self.assertEqual(result[0].recording_msid, self.sample_feedback[3]["recording_msid"])
        self.assertEqual(result[0].score, self.sample_feedback[3]["score"])

        user2 = db_user.get_or_create(2, "recording_feedback_other_user")
        self.insert_test_data(user2["id"])

        result = db_feedback.get_feedback_for_recording("recording_msid", fb_msid_1, limit=25, offset=0)
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
        result = db_feedback.get_feedback_for_recording("recording_msid", fb_msid_1, limit=25, offset=0, score=1)
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0].score, 1)
        self.assertEqual(result[1].score, 1)

        result = db_feedback.get_feedback_for_recording("recording_msid", fb_msid_1, limit=25, offset=0, score=-1)
        self.assertEqual(len(result), 0)

        # test the limit argument
        result = db_feedback.get_feedback_for_recording("recording_msid", fb_msid_1, limit=1, offset=0)
        self.assertEqual(len(result), 1)

        # test the offset argument
        result = db_feedback.get_feedback_for_recording("recording_msid", fb_msid_1, limit=25, offset=1)
        self.assertEqual(len(result), 1)

    def test_get_feedback_count_for_recording(self):
        fb_msid_1 = self.sample_feedback[0]["recording_msid"]
        fb_mbid = self.sample_feedback[2]["recording_mbid"]

        self.insert_test_data(self.user["id"])
        result = db_feedback.get_feedback_count_for_recording("recording_msid", fb_msid_1)
        self.assertEqual(result, 1)

        result = db_feedback.get_feedback_count_for_recording("recording_mbid", fb_mbid)
        self.assertEqual(result, 1)

        user2 = db_user.get_or_create(2, "recording_feedback_other_user")
        self.insert_test_data(user2["id"])

        result = db_feedback.get_feedback_count_for_recording("recording_msid", fb_msid_1)
        self.assertEqual(result, 2)

        result = db_feedback.get_feedback_count_for_recording("recording_mbid", fb_mbid)
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
            user_name=self.user["musicbrainz_id"],
            recording_msids=recording_list,
            recording_mbids=[]
        )
        self.assertEqual(len(result), len(recording_list))

        # test correct score is returned for recording_msids for which feedback records are inserted
        self.assertEqual(result[0].user_id, self.user["id"])
        self.assertEqual(result[0].user_name, self.user["musicbrainz_id"])
        self.assertEqual(result[0].recording_msid, recording_list[0])
        self.assertEqual(result[0].recording_mbid, self.sample_feedback[0]["recording_mbid"])
        self.assertEqual(result[0].score, self.sample_feedback[0]["score"])

        self.assertEqual(result[1].user_id, self.user["id"])
        self.assertEqual(result[1].user_name, self.user["musicbrainz_id"])
        self.assertEqual(result[1].recording_msid, recording_list[1])
        self.assertEqual(result[1].recording_mbid, self.sample_feedback[1]["recording_mbid"])
        self.assertEqual(result[1].score, self.sample_feedback[1]["score"])

        # test score = 0 is returned for recording_msids for which feedback records are inserted
        self.assertEqual(result[2].user_id, self.user["id"])
        self.assertEqual(result[2].user_name, self.user["musicbrainz_id"])
        self.assertEqual(result[2].recording_msid, recording_list[2])
        self.assertEqual(result[2].score, 0)


        mbids_list = [
            self.sample_feedback[2]["recording_mbid"],
            self.sample_feedback[3]["recording_mbid"],
            "d53ff85d-f126-46d7-b78f-f8f4d144f6d3"  # non existing recording mbid should return score = 0
        ]

        result = db_feedback.get_feedback_for_multiple_recordings_for_user(
            user_id=self.user["id"],
            user_name=self.user["musicbrainz_id"],
            recording_msids=[],
            recording_mbids=mbids_list
        )
        self.assertEqual(len(result), len(mbids_list))

        # test correct score is returned for recording_mbids for which feedback records are inserted
        self.assertEqual(result[0].user_id, self.user["id"])
        self.assertEqual(result[0].user_name, self.user["musicbrainz_id"])
        self.assertEqual(result[0].recording_msid, self.sample_feedback[2]["recording_msid"])
        self.assertEqual(result[0].recording_mbid, mbids_list[0])
        self.assertEqual(result[0].score, self.sample_feedback[2]["score"])

        self.assertEqual(result[1].user_id, self.user["id"])
        self.assertEqual(result[1].user_name, self.user["musicbrainz_id"])
        self.assertEqual(result[1].recording_msid, self.sample_feedback[3]["recording_msid"])
        self.assertEqual(result[1].recording_mbid, mbids_list[1])
        self.assertEqual(result[1].score, self.sample_feedback[3]["score"])

        # test score = 0 is returned for recording_mbids for which feedback records are inserted
        self.assertEqual(result[2].user_id, self.user["id"])
        self.assertEqual(result[2].user_name, self.user["musicbrainz_id"])
        self.assertEqual(result[2].recording_mbid, mbids_list[2])
        self.assertEqual(result[2].score, 0)


        result = db_feedback.get_feedback_for_multiple_recordings_for_user(
            user_id=self.user["id"],
            user_name=self.user["musicbrainz_id"],
            recording_msids=recording_list,
            recording_mbids=mbids_list
        )
        self.assertEqual(len(result), len(mbids_list) + len(recording_list))
        result_map_msid = {x.recording_msid: x for x in result if x.recording_msid}
        result_map_mbid = {x.recording_mbid: x for x in result if x.recording_mbid}

        # test correct score is returned for recording_mbids for which feedback records are inserted
        feedback = result_map_mbid[mbids_list[0]]
        self.assertEqual(feedback.user_id, self.user["id"])
        self.assertEqual(feedback.user_name, self.user["musicbrainz_id"])
        self.assertEqual(feedback.recording_msid, self.sample_feedback[2]["recording_msid"])
        self.assertEqual(feedback.recording_mbid, mbids_list[0])
        self.assertEqual(feedback.score, self.sample_feedback[2]["score"])

        feedback = result_map_mbid[mbids_list[1]]
        self.assertEqual(feedback.user_id, self.user["id"])
        self.assertEqual(feedback.user_name, self.user["musicbrainz_id"])
        self.assertEqual(feedback.recording_msid, self.sample_feedback[3]["recording_msid"])
        self.assertEqual(feedback.recording_mbid, mbids_list[1])
        self.assertEqual(feedback.score, self.sample_feedback[3]["score"])

        feedback = result_map_mbid[mbids_list[2]]
        # test score = 0 is returned for recording_mbids for which feedback records are inserted
        self.assertEqual(feedback.user_id, self.user["id"])
        self.assertEqual(feedback.user_name, self.user["musicbrainz_id"])
        self.assertEqual(feedback.recording_mbid, mbids_list[2])
        self.assertEqual(feedback.score, 0)

        # test correct score is returned for recording_msids for which feedback records are inserted
        feedback = result_map_msid[recording_list[0]]
        self.assertEqual(feedback.user_id, self.user["id"])
        self.assertEqual(feedback.user_name, self.user["musicbrainz_id"])
        self.assertEqual(feedback.recording_msid, recording_list[0])
        self.assertEqual(feedback.recording_mbid, self.sample_feedback[0]["recording_mbid"])
        self.assertEqual(feedback.score, self.sample_feedback[0]["score"])

        feedback = result_map_msid[recording_list[1]]
        self.assertEqual(feedback.user_id, self.user["id"])
        self.assertEqual(feedback.user_name, self.user["musicbrainz_id"])
        self.assertEqual(feedback.recording_msid, recording_list[1])
        self.assertEqual(feedback.recording_mbid, self.sample_feedback[1]["recording_mbid"])
        self.assertEqual(feedback.score, self.sample_feedback[1]["score"])

        feedback = result_map_msid[recording_list[2]]
        # test score = 0 is returned for recording_msids for which feedback records are inserted
        self.assertEqual(feedback.user_id, self.user["id"])
        self.assertEqual(feedback.user_name, self.user["musicbrainz_id"])
        self.assertEqual(feedback.recording_msid, recording_list[2])
        self.assertEqual(feedback.score, 0)