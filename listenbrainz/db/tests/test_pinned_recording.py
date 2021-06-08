# -*- coding: utf-8 -*-
import json
from datetime import datetime, timedelta, timezone

from listenbrainz.db.model.pinned_recording import PinnedRecording
import listenbrainz.db.pinned_recording as db_pinned_rec
import listenbrainz.db.user as db_user

from listenbrainz.db.testing import DatabaseTestCase


class PinnedRecDatabaseTestCase(DatabaseTestCase):
    def setUp(self):
        DatabaseTestCase.setUp(self)
        self.user = db_user.get_or_create(1, "pintestuser")
        self.pinned_rec_samples = [
            {"recording_mbid": "7f3d82ee-3817-4367-9eec-f33a312247a1", "blurb_content": "Amazing first recording"},
            {"recording_mbid": "7f3d82ee-3817-4367-9eec-f33a312247a1", "blurb_content": "Wonderful second recording"},
            {"recording_mbid": "7f3d82ee-3817-4367-9eec-f33a312247a1", "blurb_content": "Incredible third recording"},
            {"recording_mbid": "67c4697d-d956-4257-8cc9-198e5cb67479", "blurb_content": "Spectacular fourth recording"},
        ]

    def insert_test_data(self, user_id: int, limit: int = 4):
        """Inserts test data into the database.

        Args:
            user_id: the row ID of the user in the DB
            limit: the amount of recordings in pinned_rec_samples to insert (default = all 4)

        Returns:
            The amount of samples inserted.
        """

        for data in self.pinned_rec_samples[:limit]:
            db_pinned_rec.pin(
                PinnedRecording(
                    user_id=user_id,
                    recording_mbid=data["recording_mbid"],
                    blurb_content=data["blurb_content"],
                )
            )
        return min(limit, len(self.pinned_rec_samples))

    def pin_single_sample(self, user_id: int, index: int = 0) -> PinnedRecording:
        """Inserts one recording from pinned_rec_samples into the database.

        Args:
            user_id: the row ID of the user in the DB
            index: the index of the element in pinned_rec_samples to insert

        Returns:
            The PinnedRecording object that was pinned
        """
        recording_to_pin = PinnedRecording(
            user_id=user_id,
            recording_mbid=self.pinned_rec_samples[index]["recording_mbid"],
            blurb_content=self.pinned_rec_samples[index]["blurb_content"],
        )

        db_pinned_rec.pin(recording_to_pin)
        return recording_to_pin

    def test_Pinned_Recording_model(self):
        # test missing required arguments error
        with self.assertRaises(ValueError):
            PinnedRecording(
                user_id=self.user["id"],
            )

        # test created = datetime with missing tzinfo error
        with self.assertRaises(ValueError):
            PinnedRecording(
                user_id=self.user["id"],
                recording_mbid=self.pinned_rec_samples[0]["recording_mbid"],
                blurb_content=self.pinned_rec_samples[0]["blurb_content"],
                created=datetime.now(),
            )

        # test created = invalid datetime error
        with self.assertRaises(ValueError):
            PinnedRecording(
                user_id=self.user["id"],
                recording_mbid=self.pinned_rec_samples[0]["recording_mbid"],
                blurb_content=self.pinned_rec_samples[0]["blurb_content"],
                created="foobar",
            )

        # test pinned_until = datetime with missing tzinfo error
        with self.assertRaises(ValueError):
            PinnedRecording(
                user_id=self.user["id"],
                recording_mbid=self.pinned_rec_samples[0]["recording_mbid"],
                blurb_content=self.pinned_rec_samples[0]["blurb_content"],
                pinned_until=datetime.now(),
            )

        # test pinned_until = invalid datetime error
        with self.assertRaises(ValueError):
            PinnedRecording(
                user_id=self.user["id"],
                recording_mbid=self.pinned_rec_samples[0]["recording_mbid"],
                blurb_content=self.pinned_rec_samples[0]["blurb_content"],
                pinned_until="foobar",
            )

        # test pinned_until < created error
        with self.assertRaises(ValueError):
            PinnedRecording(
                user_id=self.user["id"],
                recording_mbid=self.pinned_rec_samples[0]["recording_mbid"],
                blurb_content=self.pinned_rec_samples[0]["blurb_content"],
                created="2021-06-08 23:23:23.23232+00:00",
                pinned_until="1980-06-08 23:23:23.23232+00:00",
            )

        # test default pinned_until value
        now = datetime.now(timezone.utc)
        pin_until_test_rec = PinnedRecording(
            user_id=self.user["id"],
            recording_mbid=self.pinned_rec_samples[0]["recording_mbid"],
            blurb_content=self.pinned_rec_samples[0]["blurb_content"],
            created=now,
        )
        self.assertEqual(pin_until_test_rec.pinned_until, now + timedelta(days=7))

    def test_pin(self):
        count = self.insert_test_data(self.user["id"])
        pin_history = db_pinned_rec.get_pin_history_for_user(user_id=self.user["id"], count=50, offset=0)
        self.assertEqual(len(pin_history), count)

    def test_unpin_if_active_currently_pinned(self):
        self.insert_test_data(self.user["id"], 3)  # pin 3 recordings
        initial_original_pin = db_pinned_rec.get_current_pin_for_user(user_id=self.user["id"])

        self.pin_single_sample(self.user["id"], 3)  # pin 4th recording
        new_pin = db_pinned_rec.get_current_pin_for_user(user_id=self.user["id"])
        updated_original_pin = db_pinned_rec.get_pin_history_for_user(user_id=self.user["id"], count=50, offset=0)[1]

        # only the pinned_until value of the record should be updated
        self.assertEqual(initial_original_pin.user_id, updated_original_pin.user_id)
        self.assertEqual(initial_original_pin.recording_mbid, updated_original_pin.recording_mbid)
        self.assertEqual(initial_original_pin.blurb_content, updated_original_pin.blurb_content)
        self.assertEqual(initial_original_pin.created, updated_original_pin.created)
        self.assertGreater(initial_original_pin.pinned_until, updated_original_pin.pinned_until)

        self.assertNotEqual(new_pin, initial_original_pin)

    def test_unpin(self):
        recording_pinned = self.pin_single_sample(self.user["id"], 0)
        recording_in_db = db_pinned_rec.get_current_pin_for_user(self.user["id"])
        self.assertEqual(recording_pinned, recording_in_db)

        db_pinned_rec.unpin(self.user["id"])
        self.assertIsNone(db_pinned_rec.get_current_pin_for_user(self.user["id"]))

        pinned_history = db_pinned_rec.get_pin_history_for_user(user_id=self.user["id"], count=50, offset=0)
        self.assertEqual(len(pinned_history), 1)

        # test that the pinned_until value was updated
        initial_pinned_until = recording_pinned.pinned_until
        updated_pinned_until = pinned_history[0].pinned_until
        self.assertGreater(initial_pinned_until, updated_pinned_until)

    def test_delete(self):
        self.pin_single_sample(self.user["id"], 0)
        self.pin_single_sample(self.user["id"], 1)
        old_pin_history = db_pinned_rec.get_pin_history_for_user(user_id=self.user["id"], count=50, offset=0)
        pinned = old_pin_history[0]
        db_pinned_rec.delete(
            PinnedRecording(  # delete the newer record
                user_id=self.user["id"],
                recording_mbid=pinned.recording_mbid,
                pinned_until=pinned.pinned_until,
                created=pinned.created,
            )
        )

        new_pin_history = db_pinned_rec.get_pin_history_for_user(user_id=self.user["id"], count=50, offset=0)
        self.assertEqual(len(new_pin_history), len(old_pin_history) - 1)
        self.assertEqual("Amazing first recording", new_pin_history[0].blurb_content)

        old_pin_history = new_pin_history
        pinned = old_pin_history[0]
        db_pinned_rec.delete(
            PinnedRecording(  # delete the newer record
                user_id=self.user["id"],
                recording_mbid=pinned.recording_mbid,
                pinned_until=pinned.pinned_until,
                created=pinned.created,
            )
        )

        new_pin_history = db_pinned_rec.get_pin_history_for_user(user_id=self.user["id"], count=50, offset=0)
        self.assertEqual(len(new_pin_history), 0)
        self.assertIsNotNone(new_pin_history)

    def test_get_current_pin_for_user(self):
        # insert 2 recordings from sample and test that the correct one is the active pin
        self.pin_single_sample(self.user["id"], 0)
        expected_pinned = self.pin_single_sample(self.user["id"], 1)
        recieved_pinned = db_pinned_rec.get_current_pin_for_user(self.user["id"])
        self.assertEqual(recieved_pinned, expected_pinned)

        # insert 2 more recordings from sample and test that the correct one is the active pin
        self.pin_single_sample(self.user["id"], 2)
        expected_pinned = self.pin_single_sample(self.user["id"], 3)
        recieved_pinned = db_pinned_rec.get_current_pin_for_user(self.user["id"])
        self.assertEqual(recieved_pinned, expected_pinned)

    def test_get_pin_history_for_user(self):
        # test that function returns correct number of records for user
        count = 3
        self.insert_test_data(self.user["id"], count)
        pin_history = db_pinned_rec.get_pin_history_for_user(user_id=self.user["id"], count=50, offset=0)
        self.assertEqual(len(pin_history), count)

        # test that pin history includes unpinned recordings
        db_pinned_rec.unpin(user_id=self.user["id"])
        new_pin_history = db_pinned_rec.get_pin_history_for_user(user_id=self.user["id"], count=50, offset=0)
        self.assertEqual(len(new_pin_history), len(pin_history))

        # test that the list was returned in descending order of creation date
        self.assertGreater(pin_history[0].created, pin_history[1].created)
        self.assertEqual(pin_history[0].blurb_content, self.pinned_rec_samples[count - 1]["blurb_content"])

        # test the limit argument
        limit = 1
        limited_pin_history = db_pinned_rec.get_pin_history_for_user(user_id=self.user["id"], count=limit, offset=0)
        self.assertEqual(len(limited_pin_history), limit)
        limit = 999
        limited_pin_history = db_pinned_rec.get_pin_history_for_user(user_id=self.user["id"], count=limit, offset=0)
        self.assertEqual(len(limited_pin_history), count)

        # test the offset argument
        offset = 1
        offset_pin_history = db_pinned_rec.get_pin_history_for_user(user_id=self.user["id"], count=50, offset=offset)
        self.assertEqual(len(offset_pin_history), count - offset)
        offset = 999
        offset_pin_history = db_pinned_rec.get_pin_history_for_user(user_id=self.user["id"], count=50, offset=offset)
        self.assertEqual(len(offset_pin_history), 0)

    def test_get_pin_count_for_user(self):
        self.insert_test_data(self.user["id"])
        pin_history = db_pinned_rec.get_pin_history_for_user(user_id=self.user["id"], count=50, offset=0)
        self.assertEqual(len(pin_history), db_pinned_rec.get_pin_count_for_user(user_id=self.user["id"]))
