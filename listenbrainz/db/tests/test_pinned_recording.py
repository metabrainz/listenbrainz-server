# -*- coding: utf-8 -*-
import json
from datetime import datetime
from pydantic import ValidationError

from listenbrainz.db.model.pinned_recording import (
    PinnedRecording,
    WritablePinnedRecording,
    DAYS_UNTIL_UNPIN,
)
import listenbrainz.db.pinned_recording as db_pinned_rec
import listenbrainz.db.user as db_user
import listenbrainz.db.user_relationship as db_user_relationship

from listenbrainz.db.testing import DatabaseTestCase


class PinnedRecDatabaseTestCase(DatabaseTestCase):
    def setUp(self):
        DatabaseTestCase.setUp(self)
        self.user = db_user.get_or_create(1, "test_user")
        self.followed_user_1 = db_user.get_or_create(2, "followed_user_1")
        self.followed_user_2 = db_user.get_or_create(3, "followed_user_2")

        self.pinned_rec_samples = [
            {
                "recording_msid": "7f3d82ee-3817-4367-9eec-f33a312247a1",
                "recording_mbid": "83b57de1-7f69-43cb-a0df-5f77a882e954",
                "blurb_content": "Amazing first recording",
            },
            {
                "recording_msid": "7f3d82ee-3817-4367-9eec-f33a312247a1",
                "recording_mbid": "7e4142f4-b01e-4492-ae13-553493bad634",
                "blurb_content": "Wonderful second recording",
            },
            {
                "recording_msid": "7f3d82ee-3817-4367-9eec-f33a312247a1",
                "recording_mbid": "a67ef149-3550-4547-b1eb-1b7c0b6879fa",
                "blurb_content": "Incredible third recording",
            },
            {
                "recording_msid": "67c4697d-d956-4257-8cc9-198e5cb67479",
                "recording_mbid": "6867f7eb-b0d8-4c08-89e4-aa9d4b58ffb5",
                "blurb_content": "Great fourth recording",
            },
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
                WritablePinnedRecording(
                    user_id=user_id,
                    recording_msid=data["recording_msid"],
                    recording_mbid=data["recording_mbid"],
                    blurb_content=data["blurb_content"],
                )
            )
        return min(limit, len(self.pinned_rec_samples))

    def pin_single_sample(self, user_id: int, index: int = 0) -> WritablePinnedRecording:
        """Inserts one recording from pinned_rec_samples into the database.

        Args:
            user_id: the row ID of the user in the DB
            index: the index of the element in pinned_rec_samples to insert

        Returns:
            The PinnedRecording object that was pinned
        """
        recording_to_pin = WritablePinnedRecording(
            user_id=user_id,
            recording_msid=self.pinned_rec_samples[index]["recording_msid"],
            recording_mbid=self.pinned_rec_samples[index]["recording_mbid"],
            blurb_content=self.pinned_rec_samples[index]["blurb_content"],
        )

        db_pinned_rec.pin(recording_to_pin)
        return recording_to_pin

    def test_Pinned_Recording_model(self):
        # test missing required arguments error
        with self.assertRaises(ValidationError):
            WritablePinnedRecording(
                user_id=self.user["id"],
            )

        # test recording_msid = invalid uuid format
        with self.assertRaises(ValidationError):
            WritablePinnedRecording(
                user_id=self.user["id"],
                recording_msid="7f3-38-43-9e-f3",
                recording_mbid=self.pinned_rec_samples[0]["recording_mbid"],
                blurb_content=self.pinned_rec_samples[0]["blurb_content"],
            )

        # test optional recording_mbid = invalid uuid format
        with self.assertRaises(ValidationError):
            WritablePinnedRecording(
                user_id=self.user["id"],
                recording_msid=self.pinned_rec_samples[0]["recording_msid"],
                recording_mbid="7f3-38-43-9e-f3",
                blurb_content=self.pinned_rec_samples[0]["blurb_content"],
            )

        # test created = invalid datetime error doesn't raise error
        WritablePinnedRecording(
            user_id=self.user["id"],
            recording_msid=self.pinned_rec_samples[0]["recording_msid"],
            recording_mbid=self.pinned_rec_samples[0]["recording_mbid"],
            blurb_content=self.pinned_rec_samples[0]["blurb_content"],
            created="foobar",
        )

        # test pinned_until = datetime with missing tzinfo error
        with self.assertRaises(ValidationError):
            WritablePinnedRecording(
                user_id=self.user["id"],
                recording_msid=self.pinned_rec_samples[0]["recording_msid"],
                recording_mbid=self.pinned_rec_samples[0]["recording_mbid"],
                blurb_content=self.pinned_rec_samples[0]["blurb_content"],
                pinned_until=datetime.now(),
            )

        # test pinned_until = invalid datetime error
        with self.assertRaises(ValidationError):
            WritablePinnedRecording(
                user_id=self.user["id"],
                recording_msid=self.pinned_rec_samples[0]["recording_msid"],
                recording_mbid=self.pinned_rec_samples[0]["recording_mbid"],
                blurb_content=self.pinned_rec_samples[0]["blurb_content"],
                pinned_until="foobar",
            )

        # test pinned_until < created error
        with self.assertRaises(ValidationError):
            WritablePinnedRecording(
                user_id=self.user["id"],
                recording_msid=self.pinned_rec_samples[0]["recording_msid"],
                recording_mbid=self.pinned_rec_samples[0]["recording_mbid"],
                blurb_content=self.pinned_rec_samples[0]["blurb_content"],
                created="2021-06-08 23:23:23.23232+00:00",
                pinned_until="1980-06-08 23:23:23.23232+00:00",
            )

    def test_pin(self):
        count = self.insert_test_data(self.user["id"])
        pin_history = db_pinned_rec.get_pin_history_for_user(user_id=self.user["id"], count=50, offset=0)
        self.assertEqual(len(pin_history), count)

    def test_unpin_if_active_currently_pinned(self):
        original_pinned = self.pin_single_sample(self.user["id"], 0)
        new_pinned = self.pin_single_sample(self.user["id"], 1)
        original_unpinned = db_pinned_rec.get_pin_history_for_user(user_id=self.user["id"], count=50, offset=0)[1]

        # only the pinned_until value of the record should be updated
        self.assertEqual(original_unpinned.user_id, original_pinned.user_id)
        self.assertEqual(original_unpinned.recording_msid, original_pinned.recording_msid)
        self.assertEqual(original_unpinned.recording_mbid, original_pinned.recording_mbid)
        self.assertEqual(original_unpinned.blurb_content, original_pinned.blurb_content)
        self.assertEqual(original_unpinned.created, original_pinned.created)
        self.assertLess(original_unpinned.pinned_until, original_pinned.pinned_until)

        self.assertNotEqual(new_pinned, original_pinned)

    def test_unpin(self):
        pinned = self.pin_single_sample(self.user["id"], 0)
        db_pinned_rec.unpin(self.user["id"])
        self.assertIsNone(db_pinned_rec.get_current_pin_for_user(self.user["id"]))

        # test that the pinned_until value was updated
        unpinned = db_pinned_rec.get_pin_history_for_user(user_id=self.user["id"], count=50, offset=0)[0]
        self.assertGreater(pinned.pinned_until, unpinned.pinned_until)

    def test_delete(self):
        keptIndex = 0

        # insert two records and delete the newer one
        self.pin_single_sample(self.user["id"], keptIndex)
        self.pin_single_sample(self.user["id"], 1)
        old_pin_history = db_pinned_rec.get_pin_history_for_user(user_id=self.user["id"], count=50, offset=0)
        pin_to_delete = old_pin_history[0]
        db_pinned_rec.delete(pin_to_delete.row_id, self.user["id"])

        # test that only the older pin remained in the database
        pin_history = db_pinned_rec.get_pin_history_for_user(user_id=self.user["id"], count=50, offset=0)
        pin_remaining = pin_history[0]
        self.assertEqual(len(pin_history), len(old_pin_history) - 1)
        self.assertEqual(pin_remaining.blurb_content, self.pinned_rec_samples[keptIndex]["blurb_content"])

        # delete the remaining pin
        db_pinned_rec.delete(pin_remaining.row_id, self.user["id"])
        pin_history = db_pinned_rec.get_pin_history_for_user(user_id=self.user["id"], count=50, offset=0)
        self.assertFalse(pin_history)

    def test_get_current_pin_for_user(self):
        self.pin_single_sample(self.user["id"], 0)
        expected_pinned = db_pinned_rec.get_current_pin_for_user(self.user["id"])
        recieved_pinned = db_pinned_rec.get_pin_history_for_user(user_id=self.user["id"], count=50, offset=0)[0]
        self.assertEqual(recieved_pinned, expected_pinned)

        self.pin_single_sample(self.user["id"], 1)
        expected_pinned = db_pinned_rec.get_current_pin_for_user(self.user["id"])
        recieved_pinned = db_pinned_rec.get_current_pin_for_user(self.user["id"])
        self.assertEqual(recieved_pinned, expected_pinned)

    def test_get_pin_history_for_user(self):
        count = 4
        self.insert_test_data(self.user["id"], count)

        # test that pin history includes unpinned recordings
        pin_history = db_pinned_rec.get_pin_history_for_user(user_id=self.user["id"], count=50, offset=0)
        db_pinned_rec.unpin(user_id=self.user["id"])
        new_pin_history = db_pinned_rec.get_pin_history_for_user(user_id=self.user["id"], count=50, offset=0)
        self.assertEqual(len(new_pin_history), len(pin_history))

        # test that the list was returned in descending order of creation date
        self.assertGreater(pin_history[0].created, pin_history[1].created)

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
        self.assertFalse(offset_pin_history)

    def test_get_pin_count_for_user(self):
        self.insert_test_data(self.user["id"])
        pin_history = db_pinned_rec.get_pin_history_for_user(user_id=self.user["id"], count=50, offset=0)
        pin_count = db_pinned_rec.get_pin_count_for_user(user_id=self.user["id"])
        self.assertEqual(pin_count, len(pin_history))

        # test that pin_count includes unpinned recordings
        db_pinned_rec.unpin(user_id=self.user["id"])
        pin_count = db_pinned_rec.get_pin_count_for_user(user_id=self.user["id"])
        self.assertEqual(pin_count, len(pin_history))

        # test that pin_count excludes deleted recordings
        pin_to_delete = pin_history[1]
        db_pinned_rec.delete(pin_to_delete.row_id, self.user["id"])
        pin_count = db_pinned_rec.get_pin_count_for_user(user_id=self.user["id"])
        self.assertEqual(pin_count, len(pin_history) - 1)

    def test_get_pins_for_user_following(self):
        # user follows followed_user_1
        db_user_relationship.insert(self.user["id"], self.followed_user_1["id"], "follow")
        self.assertTrue(db_user_relationship.is_following_user(self.user["id"], self.followed_user_1["id"]))

        # test that followed_pins contains followed_user_1's pinned recording
        self.pin_single_sample(self.followed_user_1["id"], 0)
        followed_pins = db_pinned_rec.get_pins_for_user_following(user_id=1, count=50, offset=0)
        self.assertEqual(len(followed_pins), 1)
        self.assertEqual(followed_pins[0].user_name, "followed_user_1")

        # test that pins from users that the user is not following are not included
        self.pin_single_sample(self.followed_user_2["id"], 0)
        self.assertEqual(len(followed_pins), 1)

        # test that followed_user_2's pin is included after user follows
        db_user_relationship.insert(self.user["id"], self.followed_user_2["id"], "follow")
        followed_pins = db_pinned_rec.get_pins_for_user_following(user_id=1, count=50, offset=0)
        self.assertEqual(len(followed_pins), 2)
        self.assertEqual(followed_pins[0].user_name, "followed_user_2")

        # test that list is returned in descending order of creation date
        self.assertGreater(followed_pins[0].created, followed_pins[1].created)
        self.assertEqual(followed_pins[1].user_name, "followed_user_1")

        # test the limit argument
        limit = 1
        limited_following_pins = db_pinned_rec.get_pins_for_user_following(user_id=self.user["id"], count=limit, offset=0)
        self.assertEqual(len(limited_following_pins), limit)

        limit = 999
        limited_following_pins = db_pinned_rec.get_pins_for_user_following(user_id=self.user["id"], count=limit, offset=0)
        self.assertEqual(len(limited_following_pins), 2)

        # test the offset argument
        offset = 1
        offset_following_pins = db_pinned_rec.get_pins_for_user_following(user_id=self.user["id"], count=50, offset=offset)
        self.assertEqual(len(offset_following_pins), 2 - offset)

        offset = 999
        offset_following_pins = db_pinned_rec.get_pin_history_for_user(user_id=self.user["id"], count=50, offset=offset)
        self.assertFalse(offset_following_pins)
