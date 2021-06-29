from flask import url_for

import listenbrainz.db.user as db_user
import listenbrainz.db.pinned_recording as db_pinned_rec
import listenbrainz.db.user_relationship as db_user_relationship

from listenbrainz.tests.integration import IntegrationTestCase
from listenbrainz.db.model.pinned_recording import (
    PinnedRecording,
    WritablePinnedRecording,
    DAYS_UNTIL_UNPIN,
)
import json


class PinnedRecAPITestCase(IntegrationTestCase):
    def setUp(self):
        super(PinnedRecAPITestCase, self).setUp()
        self.user = db_user.get_or_create(1, "test_user_1")
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

    def test_pin(self):
        """Tests that pin endpoint returns 200 when successful"""
        response = self.client.post(
            url_for("pinned_rec_api_bp_v1.pin_recording_for_user"),
            data=json.dumps(self.pinned_rec_samples[0]),
            headers={"Authorization": "Token {}".format(self.user["auth_token"])},
            content_type="application/json",
        )

        self.assert200(response)
        self.assertEqual(response.json["status"], "ok")

    def test_pin_unauthorized(self):
        """Tests that pin endpoint returns 401 when auth token is invalid"""
        response = self.client.post(
            url_for("pinned_rec_api_bp_v1.pin_recording_for_user"),
            data=json.dumps(self.pinned_rec_samples[0]),
            headers={"Authorization": "Token {}".format("-- This is an invalid auth token --")},
            content_type="application/json",
        )

        self.assert401(response)
        self.assertEqual(response.json["code"], 401)

    def test_pin_invalid_msid(self):
        """Tests that pin endpoint returns 400 on invalid JSON / MSID validation error"""
        invalid_pin_1 = {
            "recording_msid": "-- invalid MSID --",
            "recording_mbid": "7f3d82ee-3817-4367-9eec-f33a312247a1",
            "blurb_content": "Amazing first recording",
        }
        response = self.client.post(
            url_for("pinned_rec_api_bp_v1.pin_recording_for_user"),
            data=json.dumps(invalid_pin_1),
            headers={"Authorization": "Token {}".format(self.user["auth_token"])},
            content_type="application/json",
        )

        self.assert400(response)
        self.assertEqual(response.json["code"], 400)

    def test_pin_invalid_mbid(self):
        """Tests that pin endpoint returns 400 on invalid JSON / MBID validation error"""
        invalid_pin_1 = {
            "recording_msid": "7f3d82ee-3817-4367-9eec-f33a312247a1",
            "recording_mbid": "-- invalid MBID --",
            "blurb_content": "Amazing first recording",
        }

        response = self.client.post(
            url_for("pinned_rec_api_bp_v1.pin_recording_for_user"),
            data=json.dumps(invalid_pin_1),
            headers={"Authorization": "Token {}".format(self.user["auth_token"])},
            content_type="application/json",
        )

        self.assert400(response)
        self.assertEqual(response.json["code"], 400)

    def test_pin_invalid_pinned_until(self):
        """Tests that pin endpoint returns 400 on invalid JSON / validation error"""
        invalid_pin_1 = {
            "recording_msid": "7f3d82ee-3817-4367-9eec-f33a312247a1",
            "recording_mbid": "7f3d82ee-3817-4367-9eec-f33a312247a1",
            "blurb_content": "Amazing first recording",
            "pinned_until": "-- invalid pinned_until datetime --",
        }

        response = self.client.post(
            url_for("pinned_rec_api_bp_v1.pin_recording_for_user"),
            data=json.dumps(invalid_pin_1),
            headers={"Authorization": "Token {}".format(self.user["auth_token"])},
            content_type="application/json",
        )

        self.assert400(response)
        self.assertEqual(response.json["code"], 400)

    def test_unpin(self):
        """Tests that unpin endpoint returns 200 when successful"""
        # pin track before unpinning
        response = self.client.post(
            url_for("pinned_rec_api_bp_v1.pin_recording_for_user"),
            data=json.dumps(self.pinned_rec_samples[0]),
            headers={"Authorization": "Token {}".format(self.user["auth_token"])},
            content_type="application/json",
        )

        response = self.client.post(
            url_for("pinned_rec_api_bp_v1.unpin_recording_for_user"),
            headers={"Authorization": "Token {}".format(self.user["auth_token"])},
            content_type="application/json",
        )

        self.assert200(response)
        self.assertEqual(response.json["status"], "ok")

    def test_unpin_no_pin_found(self):
        """Tests that unpin endpoint returns 404 when no pinned is found to unpin"""
        response = self.client.post(
            url_for("pinned_rec_api_bp_v1.unpin_recording_for_user"),
            headers={"Authorization": "Token {}".format(self.user["auth_token"])},
            content_type="application/json",
        )

        self.assert404(response)
        self.assertEqual(response.json["code"], 404)

    def test_unpin_unauthorized(self):
        """Tests that unpin endpoint returns 401 when auth token is invalid"""
        response = self.client.post(
            url_for("pinned_rec_api_bp_v1.unpin_recording_for_user"),
            headers={"Authorization": "Token {}".format("-- This is an invalid auth token --")},
            content_type="application/json",
        )

        self.assert401(response)
        self.assertEqual(response.json["code"], 401)

    def test_delete(self):
        """Tests that unpin endpoint returns 200 when successful"""
        # pin track before deleting
        response = self.client.post(
            url_for("pinned_rec_api_bp_v1.pin_recording_for_user"),
            data=json.dumps(self.pinned_rec_samples[0]),
            headers={"Authorization": "Token {}".format(self.user["auth_token"])},
            content_type="application/json",
        )

        pin_to_delete = db_pinned_rec.get_current_pin_for_user(self.user["id"])

        response = self.client.post(
            url_for("pinned_rec_api_bp_v1.delete_pin_for_user", pinned_id=pin_to_delete.row_id),
            headers={"Authorization": "Token {}".format(self.user["auth_token"])},
        )

        self.assert200(response)
        self.assertEqual(response.json["status"], "ok")

    def test_delete_unauthorized(self):
        """Tests that delete endpoint returns 401 when auth token is invalid"""
        # pin track for user1
        response = self.client.post(
            url_for("pinned_rec_api_bp_v1.pin_recording_for_user"),
            data=json.dumps(self.pinned_rec_samples[0]),
            headers={"Authorization": "Token {}".format(self.user["auth_token"])},
            content_type="application/json",
        )

        # attempt to delete
        pin_to_delete = db_pinned_rec.get_current_pin_for_user(self.user["id"])

        response = self.client.post(
            url_for("pinned_rec_api_bp_v1.delete_pin_for_user", pinned_id=pin_to_delete.row_id),
            headers={"Authorization": "Token {}".format("-- This is an invalid auth token --")},
        )
        self.assert401(response)
        self.assertEqual(response.json["code"], 401)

    def test_delete_no_pinned_id_found(self):
        """Tests that delete endpoint returns 404 when no pin with pinned_id is found to delete"""
        self.client.post(
            url_for("pinned_rec_api_bp_v1.pin_recording_for_user"),
            data=json.dumps(self.pinned_rec_samples[0]),
            headers={"Authorization": "Token {}".format(self.user["auth_token"])},
            content_type="application/json",
        )

        response = self.client.post(
            url_for("pinned_rec_api_bp_v1.delete_pin_for_user", pinned_id=98764),
            headers={"Authorization": "Token {}".format(self.followed_user_1["auth_token"])},
        )

        self.assert404(response)
        self.assertEqual(response.json["code"], 404)

    def test_get_pins_for_user(self):
        """Test that valid response is received with 200 code"""
        count = self.insert_test_data(self.user["id"], 2)  # pin 2 recordings
        response = self.client.get(url_for("pinned_rec_api_bp_v1.get_pins_for_user", user_name=self.user["musicbrainz_id"]))
        self.assert200(response)
        data = json.loads(response.data)

        self.assertEqual(data["total_count"], count)
        self.assertEqual(data["offset"], 0)

        pins = data["pinned_recordings"]
        self.assertEqual(data["count"], len(pins))

        # check that data is sorted in descending order of created date
        self.assertGreaterEqual(pins[0]["created"], pins[1]["created"])
        self.assertGreater(pins[0]["pinned_id"], pins[1]["pinned_id"])

        self.assertEqual(pins[0]["recording_msid"], self.pinned_rec_samples[1]["recording_msid"])
        self.assertEqual(pins[0]["recording_mbid"], self.pinned_rec_samples[1]["recording_mbid"])
        self.assertEqual(pins[0]["blurb_content"], self.pinned_rec_samples[1]["blurb_content"])

        self.assertEqual(pins[1]["recording_msid"], self.pinned_rec_samples[0]["recording_msid"])
        self.assertEqual(pins[1]["recording_mbid"], self.pinned_rec_samples[0]["recording_mbid"])
        self.assertEqual(pins[1]["blurb_content"], self.pinned_rec_samples[0]["blurb_content"])

    def test_get_pins_for_user_invalid_username(self):
        """Tests that endpoint returns 404 when no user with given user_name is found"""
        self.insert_test_data(self.user["id"])  # pin 4 recordings for user
        response = self.client.get(url_for("pinned_rec_api_bp_v1.get_pins_for_user", user_name=" -- invalid username -- "))

        self.assert404(response)
        self.assertEqual(response.json["code"], 404)

    def test_get_pins_for_user_count_param(self):
        """Tests that valid response is received honoring count parameter"""
        limit = 2
        pinned_count = self.insert_test_data(self.user["id"])  # pin 4 recordings
        response = self.client.get(
            url_for("pinned_rec_api_bp_v1.get_pins_for_user", user_name=self.user["musicbrainz_id"], count=limit)
        )
        data = json.loads(response.data)
        pins = data["pinned_recordings"]

        self.assertEqual(data["total_count"], pinned_count)
        self.assertEqual(data["count"], limit)

        # check that only the two latest pinned recordings are returned with count = 2 in descending order of created date
        self.assertEqual(pins[0]["blurb_content"], self.pinned_rec_samples[3]["blurb_content"])
        self.assertEqual(pins[1]["blurb_content"], self.pinned_rec_samples[2]["blurb_content"])

        # double check with different limit
        limit = 3
        response = self.client.get(
            url_for("pinned_rec_api_bp_v1.get_pins_for_user", user_name=self.user["musicbrainz_id"], count=limit)
        )
        data = json.loads(response.data)

        self.assertEqual(data["total_count"], pinned_count)
        self.assertEqual(data["count"], limit)

    def test_get_pins_for_user_invalid_count_param(self):
        """Tests that 400 response is received if count parameter is invalid"""

        # test with string
        response = self.client.get(
            url_for("pinned_rec_api_bp_v1.get_pins_for_user", user_name=self.user["musicbrainz_id"], count="-- invalid count --")
        )
        self.assert400(response)
        self.assertEqual(response.json["code"], 400)

        # test with negative integer
        response = self.client.get(
            url_for("pinned_rec_api_bp_v1.get_pins_for_user", user_name=self.user["musicbrainz_id"], count=-1)
        )
        self.assert400(response)
        self.assertEqual(response.json["code"], 400)

    def test_get_pins_for_user_offset_param(self):
        """Tests that valid response is received honoring offset parameter"""
        offset = 2
        pinned_count = self.insert_test_data(self.user["id"])  # pin 4 recordings
        response = self.client.get(
            url_for("pinned_rec_api_bp_v1.get_pins_for_user", user_name=self.user["musicbrainz_id"], offset=offset)
        )
        data = json.loads(response.data)
        pins = data["pinned_recordings"]

        self.assertEqual(data["total_count"], pinned_count)
        self.assertEqual(data["count"], pinned_count - offset)

        # check that only the two older pinned recordings are returned with offset = 2 in descending order of created date
        self.assertEqual(pins[0]["blurb_content"], self.pinned_rec_samples[1]["blurb_content"])
        self.assertEqual(pins[1]["blurb_content"], self.pinned_rec_samples[0]["blurb_content"])

        # double check with different limit
        offset = 3
        response = self.client.get(
            url_for("pinned_rec_api_bp_v1.get_pins_for_user", user_name=self.user["musicbrainz_id"], offset=offset)
        )
        data = json.loads(response.data)

        self.assertEqual(data["total_count"], pinned_count)
        self.assertEqual(data["count"], pinned_count - offset)

    def test_get_pins_for_user_invalid_offset_param(self):
        """Tests that 400 response is received if offset parameter is invalid"""

        # test with string
        response = self.client.get(
            url_for(
                "pinned_rec_api_bp_v1.get_pins_for_user", user_name=self.user["musicbrainz_id"], offset="-- invalid offset --"
            )
        )
        self.assert400(response)
        self.assertEqual(response.json["code"], 400)

        # test with negative integer
        response = self.client.get(
            url_for("pinned_rec_api_bp_v1.get_pins_for_user", user_name=self.user["musicbrainz_id"], offset=-1)
        )
        self.assert400(response)
        self.assertEqual(response.json["code"], 400)

    def test_get_pins_for_user_following(self):
        """Test that valid response is received with 200 code"""
        # user follows followed_user_1 and followed_user_2
        db_user_relationship.insert(self.user["id"], self.followed_user_1["id"], "follow")
        db_user_relationship.insert(self.user["id"], self.followed_user_2["id"], "follow")

        pin1 = self.pin_single_sample(self.followed_user_1["id"], 0)  # pin recording for followed_user_1
        pin2 = self.pin_single_sample(self.followed_user_2["id"], 1)  # pin recording for followed_user_2

        response = self.client.get(
            url_for("pinned_rec_api_bp_v1.get_pins_for_user_following", user_name=self.user["musicbrainz_id"])
        )
        self.assert200(response)
        data = json.loads(response.data)

        pins = data["pinned_recordings"]

        self.assertEqual(data["offset"], 0)
        self.assertEqual(data["count"], 2)
        self.assertEqual(data["user_name"], self.user["musicbrainz_id"])

        # check that data is sorted in descending order of created date
        self.assertEqual(pins[0]["recording_msid"], pin2.recording_msid)  # pin2 was pinned most recently
        self.assertEqual(pins[0]["recording_mbid"], pin2.recording_mbid)
        self.assertEqual(pins[0]["blurb_content"], pin2.blurb_content)
        self.assertEqual(pins[0]["user_name"], self.followed_user_2["musicbrainz_id"])

        self.assertEqual(pins[1]["recording_msid"], pin1.recording_msid)  # pin2 was pinned before pin1
        self.assertEqual(pins[1]["recording_mbid"], pin1.recording_mbid)
        self.assertEqual(pins[1]["blurb_content"], pin1.blurb_content)
        self.assertEqual(pins[1]["user_name"], self.followed_user_1["musicbrainz_id"])

    def test_get_pins_for_user_following_invalid_username(self):
        """Tests that endpoint returns 404 when no user with given user_name is found"""
        response = self.client.get(
            url_for("pinned_rec_api_bp_v1.get_pins_for_user_following", user_name=" -- invalid username -- ")
        )
        self.assert404(response)
        self.assertEqual(response.json["code"], 404)

    def test_get_pins_for_user_count_param(self):
        """Tests that valid response is received honoring count parameter"""
        # user follows followed_user_1 and followed_user_2
        db_user_relationship.insert(self.user["id"], self.followed_user_1["id"], "follow")
        db_user_relationship.insert(self.user["id"], self.followed_user_2["id"], "follow")

        self.pin_single_sample(self.followed_user_1["id"], 0)  # pin recording for followed_user_1
        included_pin = self.pin_single_sample(self.followed_user_2["id"], 1)  # pin recording for followed_user_2

        limit = 1
        response = self.client.get(
            url_for("pinned_rec_api_bp_v1.get_pins_for_user_following", user_name=self.user["musicbrainz_id"], count=limit)
        )
        data = json.loads(response.data)
        pins = data["pinned_recordings"]

        self.assertEqual(data["offset"], 0)
        self.assertEqual(data["count"], 2 - limit)

        # check that only the latest pin was included in returned json
        self.assertEqual(pins[0]["recording_msid"], included_pin.recording_msid)  # included_pin was pinned most recently
        self.assertEqual(pins[0]["recording_mbid"], included_pin.recording_mbid)
        self.assertEqual(pins[0]["blurb_content"], included_pin.blurb_content)
        self.assertEqual(pins[0]["user_name"], self.followed_user_2["musicbrainz_id"])

    def test_get_pins_for_user_following_invalid_count_param(self):
        """Tests that 400 response is received if count parameter is invalid"""

        # test with string
        response = self.client.get(
            url_for(
                "pinned_rec_api_bp_v1.get_pins_for_user_following",
                user_name=self.user["musicbrainz_id"],
                count="-- invalid count --",
            )
        )
        self.assert400(response)
        self.assertEqual(response.json["code"], 400)

        # test with negative integer
        response = self.client.get(
            url_for("pinned_rec_api_bp_v1.get_pins_for_user_following", user_name=self.user["musicbrainz_id"], count=-1)
        )
        self.assert400(response)
        self.assertEqual(response.json["code"], 400)

    def test_get_pins_for_user_following_offset_param(self):
        """Tests that valid response is received honoring offset parameter"""
        # user follows followed_user_1 and followed_user_2
        db_user_relationship.insert(self.user["id"], self.followed_user_1["id"], "follow")
        db_user_relationship.insert(self.user["id"], self.followed_user_2["id"], "follow")

        included_pin = self.pin_single_sample(self.followed_user_1["id"], 0)  # pin recording for followed_user_1
        self.pin_single_sample(self.followed_user_2["id"], 1)  # pin recording for followed_user_2

        offset = 1
        response = self.client.get(
            url_for("pinned_rec_api_bp_v1.get_pins_for_user_following", user_name=self.user["musicbrainz_id"], offset=offset)
        )
        data = json.loads(response.data)
        pins = data["pinned_recordings"]

        self.assertEqual(data["offset"], offset)
        self.assertEqual(data["count"], 2 - offset)

        # check that only the older pin was included in returned JSON
        self.assertEqual(pins[0]["recording_msid"], included_pin.recording_msid)  # included_pin was pinned most recently
        self.assertEqual(pins[0]["recording_mbid"], included_pin.recording_mbid)
        self.assertEqual(pins[0]["blurb_content"], included_pin.blurb_content)
        self.assertEqual(pins[0]["user_name"], self.followed_user_1["musicbrainz_id"])

    def test_get_pins_for_user_following_invalid_offset_param(self):
        """Tests that 400 response is received if offset parameter is invalid"""

        # test with string
        response = self.client.get(
            url_for(
                "pinned_rec_api_bp_v1.get_pins_for_user_following",
                user_name=self.user["musicbrainz_id"],
                offset="-- invalid offset --",
            )
        )
        self.assert400(response)
        self.assertEqual(response.json["code"], 400)

        # test with negative integer
        response = self.client.get(
            url_for("pinned_rec_api_bp_v1.get_pins_for_user_following", user_name=self.user["musicbrainz_id"], offset=-1)
        )
        self.assert400(response)
        self.assertEqual(response.json["code"], 400)
