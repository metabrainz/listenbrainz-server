from datetime import datetime

import sqlalchemy
from pydantic import ValidationError
import time

from listenbrainz.db.msid_mbid_mapping import fetch_track_metadata_for_items
from listenbrainz.db.model.pinned_recording import (
    WritablePinnedRecording,
    MAX_BLURB_CONTENT_LENGTH
)
import listenbrainz.db.pinned_recording as db_pinned_rec
import listenbrainz.db.user as db_user
import listenbrainz.db.user_relationship as db_user_relationship

from listenbrainz.db.testing import DatabaseTestCase, TimescaleTestCase
from listenbrainz import messybrainz as msb_db


class PinnedRecDatabaseTestCase(DatabaseTestCase, TimescaleTestCase):

    def setUp(self):
        DatabaseTestCase.setUp(self)
        TimescaleTestCase.setUp(self)
        self.user = db_user.get_or_create(self.db_conn, 1, "test_user")
        self.followed_user_1 = db_user.get_or_create(self.db_conn, 2, "followed_user_1")
        self.followed_user_2 = db_user.get_or_create(self.db_conn, 3, "followed_user_2")

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

    def tearDown(self):
        DatabaseTestCase.tearDown(self)
        TimescaleTestCase.tearDown(self)

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
                self.db_conn,
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

        db_pinned_rec.pin(self.db_conn, recording_to_pin)
        return recording_to_pin

    def test_pinned_recording_with_metadata(self):
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

        msids = msb_db.insert_all_in_transaction(self.ts_conn, recordings)

        query = """
                INSERT INTO mapping.mb_metadata_cache
                           (recording_mbid, artist_mbids, release_mbid, recording_data, artist_data, tag_data, release_data, dirty)
                    VALUES ('2f3d422f-8890-41a1-9762-fbe16f107c31'
                          , '{8f6bd1e4-fbe1-4f50-aa9b-94c450ec0f11}'::UUID[]
                          , '76df3287-6cda-33eb-8e9a-044b5e15ffdd'
                          , '{"name": "Strangers", "rels": [], "length": 291160}'
                          , '{"name": "Portishead", "artist_credit_id": 204, "artists": [{"area": "United Kingdom", "rels": {"lyrics": "https://muzikum.eu/en/122-6105/portishead/lyrics.html", "youtube": "https://www.youtube.com/user/portishead1002", "wikidata": "https://www.wikidata.org/wiki/Q191352", "streaming": "https://tidal.com/artist/27441", "free streaming": "https://www.deezer.com/artist/1069", "social network": "https://www.facebook.com/portishead", "official homepage": "http://www.portishead.co.uk/", "purchase for download": "https://www.junodownload.com/artists/Portishead/releases/"}, "type": "Group", "begin_year": 1991, "name": "Portishead", "join_phrase": ""}]}'
                          , '{"artist": [], "recording": [], "release_group": []}'
                          , '{"mbid": "76df3287-6cda-33eb-8e9a-044b5e15ffdd", "name": "Dummy"}'
                          , 'f'
                           )
        """
        self.ts_conn.execute(sqlalchemy.text(query))

        query = """INSERT INTO mbid_mapping
                               (recording_msid, recording_mbid, match_type, last_updated)
                        VALUES (:msid, '2f3d422f-8890-41a1-9762-fbe16f107c31', 'exact_match', now())"""
        self.ts_conn.execute(sqlalchemy.text(query), {"msid": msids[0]})

        pinned_recs = [
            {
                "recording_msid": msids[0],
                "recording_mbid": "2f3d422f-8890-41a1-9762-fbe16f107c31",
                "blurb_content": "Awesome recordings with mapped data"
            },
            {
                "recording_msid": msids[1],
                "recording_mbid": None,
                "blurb_content": "Great recording but unmapped"
            }
        ]

        for data in pinned_recs:
            db_pinned_rec.pin(
                self.db_conn,
                WritablePinnedRecording(
                    user_id=self.user["id"],
                    recording_msid=data["recording_msid"],
                    recording_mbid=data["recording_mbid"],
                    blurb_content=data["blurb_content"],
                )
            )

        pins = db_pinned_rec.get_pin_history_for_user(self.db_conn, self.user["id"], 5, 0)
        pins_with_metadata = fetch_track_metadata_for_items(self.ts_conn, pins)

        received = [x.dict() for x in pins_with_metadata]
        # pinned recs returned in reverse order of submitted because order newest to oldest
        self.assertEqual(received[0]["recording_msid"], pinned_recs[1]["recording_msid"])
        self.assertEqual(received[0]["recording_mbid"], pinned_recs[1]["recording_mbid"])
        self.assertEqual(received[0]["blurb_content"], pinned_recs[1]["blurb_content"])
        self.assertEqual(received[0]["track_metadata"], {
            "track_name": "Wicked Game",
            "artist_name": "Tom Ellis",
            "release_name": "Lucifer",
            "additional_info": {
                "recording_msid": msids[1]
            }
        })

        self.assertEqual(received[1]["recording_msid"], pinned_recs[0]["recording_msid"])
        self.assertEqual(received[1]["recording_mbid"], pinned_recs[0]["recording_mbid"])
        self.assertEqual(received[1]["blurb_content"], pinned_recs[0]["blurb_content"])
        self.assertEqual(received[1]["track_metadata"], {
            "track_name": "Strangers",
            "artist_name": "Portishead",
            "release_name": "Dummy",
            "additional_info": {
                "recording_msid": msids[0]
            },
            "mbid_mapping": {
                "recording_mbid": "2f3d422f-8890-41a1-9762-fbe16f107c31",
                "release_mbid": "76df3287-6cda-33eb-8e9a-044b5e15ffdd",
                "artist_mbids": ["8f6bd1e4-fbe1-4f50-aa9b-94c450ec0f11"],
                "artists": [
                    {
                        "artist_credit_name": "Portishead",
                        "join_phrase": "",
                        "artist_mbid": "8f6bd1e4-fbe1-4f50-aa9b-94c450ec0f11"
                    }
                ]
            }
        })

    def test_Pinned_Recording_model(self):
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

        # test blurb_content = invalid string length raises error
        invalid_blurb_content = "a" * (MAX_BLURB_CONTENT_LENGTH + 1)
        with self.assertRaises(ValidationError):
            WritablePinnedRecording(
                user_id=self.user["id"],
                recording_msid=self.pinned_rec_samples[0]["recording_msid"],
                recording_mbid=self.pinned_rec_samples[0]["recording_mbid"],
                blurb_content=invalid_blurb_content,
            )

        # test blurb_content = None doesn't raise error
        WritablePinnedRecording(
            user_id=self.user["id"],
            recording_msid=self.pinned_rec_samples[0]["recording_msid"],
            recording_mbid=self.pinned_rec_samples[0]["recording_mbid"],
            blurb_content=None,
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
        pin_history = db_pinned_rec.get_pin_history_for_user(
            self.db_conn, user_id=self.user["id"], count=50, offset=0
        )
        self.assertEqual(len(pin_history), count)

    def test_unpin_if_active_currently_pinned(self):
        original_pinned = self.pin_single_sample(self.user["id"], 0)
        new_pinned = self.pin_single_sample(self.user["id"], 1)
        original_unpinned = db_pinned_rec.get_pin_history_for_user(
            self.db_conn, user_id=self.user["id"], count=50, offset=0
        )[1]

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
        db_pinned_rec.unpin(self.db_conn, self.user["id"])
        self.assertIsNone(db_pinned_rec.get_current_pin_for_user(self.db_conn, self.user["id"]))

        # test that the pinned_until value was updated
        unpinned = db_pinned_rec.get_pin_history_for_user(self.db_conn, user_id=self.user["id"], count=50, offset=0)[0]
        self.assertGreater(pinned.pinned_until, unpinned.pinned_until)

    def test_delete(self):
        keptIndex = 0

        # insert two records and delete the newer one
        self.pin_single_sample(self.user["id"], keptIndex)
        self.pin_single_sample(self.user["id"], 1)
        old_pin_history = db_pinned_rec.get_pin_history_for_user(self.db_conn, user_id=self.user["id"], count=50, offset=0)
        pin_to_delete = old_pin_history[0]
        db_pinned_rec.delete(self.db_conn, pin_to_delete.row_id, self.user["id"])

        # test that only the older pin remained in the database
        pin_history = db_pinned_rec.get_pin_history_for_user(self.db_conn, user_id=self.user["id"], count=50, offset=0)
        pin_remaining = pin_history[0]
        self.assertEqual(len(pin_history), len(old_pin_history) - 1)
        self.assertEqual(pin_remaining.blurb_content, self.pinned_rec_samples[keptIndex]["blurb_content"])

        # delete the remaining pin
        db_pinned_rec.delete(self.db_conn, pin_remaining.row_id, self.user["id"])
        pin_history = db_pinned_rec.get_pin_history_for_user(self.db_conn, user_id=self.user["id"], count=50, offset=0)
        self.assertFalse(pin_history)

    def test_get_current_pin_for_user(self):
        self.pin_single_sample(self.user["id"], 0)
        expected_pinned = db_pinned_rec.get_current_pin_for_user(self.db_conn, self.user["id"])
        recieved_pinned = db_pinned_rec.get_pin_history_for_user(
            self.db_conn, user_id=self.user["id"], count=50, offset=0
        )[0]
        self.assertEqual(recieved_pinned, expected_pinned)

        self.pin_single_sample(self.user["id"], 1)
        expected_pinned = db_pinned_rec.get_current_pin_for_user(self.db_conn, self.user["id"])
        recieved_pinned = db_pinned_rec.get_current_pin_for_user(self.db_conn, self.user["id"])
        self.assertEqual(recieved_pinned, expected_pinned)

    def test_get_pin_history_for_user(self):
        count = 4
        self.insert_test_data(self.user["id"], count)

        # test that pin history includes unpinned recordings
        pin_history = db_pinned_rec.get_pin_history_for_user(self.db_conn, user_id=self.user["id"], count=50, offset=0)
        db_pinned_rec.unpin(self.db_conn, user_id=self.user["id"])
        new_pin_history = db_pinned_rec.get_pin_history_for_user(self.db_conn, user_id=self.user["id"], count=50, offset=0)
        self.assertEqual(len(new_pin_history), len(pin_history))

        # test that the list was returned in descending order of creation date
        self.assertGreater(pin_history[0].created, pin_history[1].created)

        # test the limit argument
        limit = 1
        limited_pin_history = db_pinned_rec.get_pin_history_for_user(
            self.db_conn, user_id=self.user["id"], count=limit, offset=0
        )
        self.assertEqual(len(limited_pin_history), limit)

        limit = 999
        limited_pin_history = db_pinned_rec.get_pin_history_for_user(
            self.db_conn, user_id=self.user["id"], count=limit, offset=0
        )
        self.assertEqual(len(limited_pin_history), count)

        # test the offset argument
        offset = 1
        offset_pin_history = db_pinned_rec.get_pin_history_for_user(
            self.db_conn, user_id=self.user["id"], count=50, offset=offset
        )
        self.assertEqual(len(offset_pin_history), count - offset)

        offset = 999
        offset_pin_history = db_pinned_rec.get_pin_history_for_user(
            self.db_conn, user_id=self.user["id"], count=50, offset=offset
        )
        self.assertFalse(offset_pin_history)

    def test_get_pin_count_for_user(self):
        self.insert_test_data(self.user["id"])
        pin_history = db_pinned_rec.get_pin_history_for_user(self.db_conn, user_id=self.user["id"], count=50, offset=0)
        pin_count = db_pinned_rec.get_pin_count_for_user(self.db_conn, user_id=self.user["id"])
        self.assertEqual(pin_count, len(pin_history))

        # test that pin_count includes unpinned recordings
        db_pinned_rec.unpin(self.db_conn, user_id=self.user["id"])
        pin_count = db_pinned_rec.get_pin_count_for_user(self.db_conn, user_id=self.user["id"])
        self.assertEqual(pin_count, len(pin_history))

        # test that pin_count excludes deleted recordings
        pin_to_delete = pin_history[1]
        db_pinned_rec.delete(self.db_conn, pin_to_delete.row_id, self.user["id"])
        pin_count = db_pinned_rec.get_pin_count_for_user(self.db_conn, user_id=self.user["id"])
        self.assertEqual(pin_count, len(pin_history) - 1)

    def test_get_pins_for_user_following(self):
        # user follows followed_user_1
        db_user_relationship.insert(self.db_conn, self.user["id"], self.followed_user_1["id"], "follow")
        self.assertTrue(
            db_user_relationship.is_following_user(
                self.db_conn,
                self.user["id"],
                self.followed_user_1["id"]
            )
        )

        # test that followed_pins contains followed_user_1's pinned recording
        self.pin_single_sample(self.followed_user_1["id"], 0)
        followed_pins = db_pinned_rec.get_pins_for_user_following(
            self.db_conn, user_id=self.user["id"], count=50, offset=0
        )
        self.assertEqual(len(followed_pins), 1)
        self.assertEqual(followed_pins[0].user_name, "followed_user_1")

        # test that pins from users that the user is not following are not included
        self.pin_single_sample(self.followed_user_2["id"], 0)
        self.assertEqual(len(followed_pins), 1)

        # test that followed_user_2's pin is included after user follows
        db_user_relationship.insert(self.db_conn, self.user["id"], self.followed_user_2["id"], "follow")
        followed_pins = db_pinned_rec.get_pins_for_user_following(
            self.db_conn, user_id=self.user["id"], count=50, offset=0
        )
        self.assertEqual(len(followed_pins), 2)
        self.assertEqual(followed_pins[0].user_name, "followed_user_2")

        # test that list is returned in descending order of creation date
        self.assertGreater(followed_pins[0].created, followed_pins[1].created)
        self.assertEqual(followed_pins[1].user_name, "followed_user_1")

        # test the limit argument
        limit = 1
        limited_following_pins = db_pinned_rec.get_pins_for_user_following(
            self.db_conn, user_id=self.user["id"], count=limit, offset=0
        )
        self.assertEqual(len(limited_following_pins), limit)

        limit = 999
        limited_following_pins = db_pinned_rec.get_pins_for_user_following(
            self.db_conn, user_id=self.user["id"], count=limit, offset=0
        )
        self.assertEqual(len(limited_following_pins), 2)

        # test the offset argument
        offset = 1
        offset_following_pins = db_pinned_rec.get_pins_for_user_following(
            self.db_conn, user_id=self.user["id"], count=50, offset=offset
        )
        self.assertEqual(len(offset_following_pins), 2 - offset)

        offset = 999
        offset_following_pins = db_pinned_rec.get_pin_history_for_user(
            self.db_conn, user_id=self.user["id"], count=50, offset=offset
        )
        self.assertFalse(offset_following_pins)

    def get_pins_for_feed(self):
        # test that correct pins are returned in correct order
        self.insert_test_data(self.user["id"])  # pin 4 recordings for user
        self.pin_single_sample(self.followed_user_1["id"])  # pin 1 recording for followed_user_1

        feedPins = db_pinned_rec.get_pins_for_feed(
            self.db_conn,
            user_ids=(self.user["id"],),
            min_ts=0,
            max_ts=int(time.time()) + 10,
            count=10,
        )
        self.assertEqual(len(feedPins), 4)
        self.assertEqual(feedPins[0].blurb_content, self.pinned_rec_samples[3]["blurb_content"])

        # test that user_ids param is honored
        feedPins = db_pinned_rec.get_pins_for_feed(
            self.db_conn,
            user_ids=(self.user["id"], self.followed_user_1["id"]),
            min_ts=0,
            max_ts=int(time.time()) + 10,
            count=10,
        )
        self.assertEqual(len(feedPins), 5)
        self.assertEqual(feedPins[0].blurb_content, self.pinned_rec_samples[0]["blurb_content"])

        # test that count parameter is honored
        limit = 1
        feedPins = db_pinned_rec.get_pins_for_feed(
            self.db_conn,
            user_ids=(self.user["id"], self.followed_user_1["id"]),
            min_ts=0,
            max_ts=int(time.time()) + 10,
            count=limit,
        )
        self.assertEqual(len(feedPins), limit)

        feedPins = db_pinned_rec.get_pins_for_feed(
            self.db_conn,
            user_ids=(self.user["id"], self.followed_user_1["id"]),
            min_ts=0,
            max_ts=0,  # too low, nothing is returned.
            count=limit,
        )
        self.assertEqual(len(feedPins), 0)

        feedPins = db_pinned_rec.get_pins_for_feed(
            self.db_conn,
            user_ids=(self.user["id"], self.followed_user_1["id"]),
            min_ts=9999,  # too high, nothing is returned.
            max_ts=9999,
            count=limit,
        )
        self.assertEqual(len(feedPins), 0)
