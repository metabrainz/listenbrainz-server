import json
import uuid
from typing import Literal, get_args, get_origin, get_type_hints, is_typeddict
from unittest import mock

import orjson
import requests_mock

import data.model.synapse_event as synapse_event
import listenbrainz.db.pinned_recording as db_pinned_rec
import listenbrainz.db.user as db_user
import listenbrainz.db.user_relationship as db_user_relationship
import listenbrainz.db.user_timeline_event as db_user_timeline_event
from listenbrainz import synapse_client
from listenbrainz.db.model.pinned_recording import WritablePinnedRecording
from listenbrainz.db.model.user_timeline_event import RecordingRecommendationMetadata
from listenbrainz.domain.critiquebrainz import CritiqueBrainzService, CRITIQUEBRAINZ_REVIEW_SUBMIT_URL
from listenbrainz.tests.integration import ListenAPIIntegrationTestCase

TRACK = {
    "track_name": "Song",
    "artist_name": "Band",
    "release_name": "Album",
    "mbid_mapping": {"recording_mbid": "6a0ce8f4-2c3f-4a43-9c4e-0f0b4f1d2a10", "caa_id": 42,
                     "caa_release_mbid": "1b2c3d4e-0000-4000-8000-000000000000"},
}

PAYLOAD_TYPES = {
    "follow": synapse_event.FollowEvent,
    "notification": synapse_event.NotificationEvent,
    "cb_review": synapse_event.CritiqueBrainzReviewEvent,
    "recording_pin": synapse_event.RecordingPinEvent,
    "recording_recommendation": synapse_event.RecordingRecommendationEvent,
    "personal_recording_recommendation": synapse_event.PersonalRecordingRecommendationEvent,
    "thanks": synapse_event.ThanksEvent,
}


def fill_track_metadata(_conn, items):
    for item in items:
        item.track_metadata = TRACK
    return items


class SynapsePublishTestCase(ListenAPIIntegrationTestCase):

    def setUp(self):
        super().setUp()
        self.author = db_user.get_or_create(self.db_conn, 301, "pin_author")
        self.follower = db_user.get_or_create(self.db_conn, 302, "pin_follower")
        db_user_relationship.insert(self.db_conn, self.follower["id"], self.author["id"], "follow")

        self.root = self.app.config["SERVER_ROOT_URL"]
        self.producer = mock.MagicMock()
        self.pool = mock.MagicMock()
        self.pool.acquire.return_value.__enter__.return_value = self.producer
        self.patch("listenbrainz.synapse_client._producer_pool", new=self.pool)
        self.patch("listenbrainz.synapse_client.fetch_track_metadata_for_items", side_effect=fill_track_metadata)

    def patch(self, target, **kwargs):
        patcher = mock.patch(target, **kwargs)
        self.addCleanup(patcher.stop)
        return patcher.start()

    def post(self, endpoint, user, body, **url_args):
        r = self.client.post(
            self.custom_url_for(endpoint, **url_args),
            data=json.dumps(body),
            headers={"Authorization": f"Token {user['auth_token']}"},
            content_type="application/json",
        )
        self.assert200(r)
        return r

    def published(self):
        """The one message published, after checking its payload against the generated type."""
        self.producer.publish.assert_called_once()
        message = orjson.loads(self.producer.publish.call_args.args[0])
        self.assertEqual(message["tenant_id"], "listenbrainz")
        self.assert_matches(message["payload"], PAYLOAD_TYPES[message["event_type"]])
        return message

    def assert_matches(self, value, expected_type):
        """Checks value against a generated TypedDict: no unknown or missing keys, right literals."""
        if is_typeddict(expected_type):
            hints = get_type_hints(expected_type)
            self.assertLessEqual(set(value), set(hints), expected_type.__name__)
            self.assertLessEqual(expected_type.__required_keys__, set(value), expected_type.__name__)
            for key, item in value.items():
                self.assert_matches(item, hints[key])
        elif get_origin(expected_type) is Literal:
            self.assertIn(value, get_args(expected_type))
        else:
            self.assertIsInstance(value, expected_type)

    def actor(self, user):
        return {"username": user["musicbrainz_id"], "url": f"{self.root}/user/{user['musicbrainz_id']}"}

    def recording(self):
        return {
            "track_name": "Song",
            "artist_name": "Band",
            "release_name": "Album",
            "mbid": "6a0ce8f4-2c3f-4a43-9c4e-0f0b4f1d2a10",
            "url": f"{self.root}/music/recording/6a0ce8f4-2c3f-4a43-9c4e-0f0b4f1d2a10",
            "album_art_url": "https://archive.org/download/mbid-1b2c3d4e-0000-4000-8000-000000000000/"
                             "mbid-1b2c3d4e-0000-4000-8000-000000000000-42_thumb250.jpg",
        }

    def pin(self):
        return self.post("pinned_rec_api_bp_v1.pin_recording_for_user", self.author,
                         {"recording_msid": str(uuid.uuid4()), "blurb_content": "on repeat"})

    def test_follow(self):
        self.post("social_api_v1.follow_user", self.author, {}, user_name="pin_follower")
        self.assertEqual(self.published(), {
            "tenant_id": "listenbrainz",
            "event_type": "follow",
            "recipients": [str(self.follower["musicbrainz_row_id"])],
            "payload": {"actor": self.actor(self.author)},
            "idempotency_key": f"follow:{self.author['id']}:{self.follower['id']}",
        })
        self.assertEqual(self.producer.publish.call_args.kwargs["exchange"], "events.ingest")
        self.assertEqual(self.producer.publish.call_args.kwargs["confirm_timeout"], 2)

    def test_recording_pin(self):
        r = self.pin()
        message = self.published()
        self.assertEqual(message["recipients"], [str(self.follower["musicbrainz_row_id"])])
        self.assertEqual(message["payload"], {
            "actor": self.actor(self.author), "recording": self.recording(), "message": "on repeat"})
        self.assertEqual(message["idempotency_key"], f"recording_pin:{r.json['pinned_recording']['row_id']}")
        # The track metadata fetched for Synapse doesn't leak into the API response.
        self.assertIsNone(r.json["pinned_recording"]["track_metadata"])

    def test_recording_recommendation(self):
        r = self.post("user_timeline_event_api_bp.create_user_recording_recommendation_event", self.author,
                      {"metadata": {"recording_msid": str(uuid.uuid4())}}, user_name="pin_author")
        message = self.published()
        self.assertEqual(message["event_type"], "recording_recommendation")
        self.assertEqual(message["payload"], {"actor": self.actor(self.author), "recording": self.recording()})
        self.assertEqual(message["idempotency_key"], f"recording_recommendation:{r.json['id']}")
        self.assertIsNone(r.json["metadata"]["track_metadata"])

    def test_personal_recommendation(self):
        r = self.post("user_timeline_event_api_bp.create_personal_recommendation_event", self.author,
                      {"metadata": {"recording_msid": str(uuid.uuid4()), "users": ["pin_follower"],
                                    "blurb_content": "for you"}},
                      user_name="pin_author")
        message = self.published()
        self.assertEqual(message["recipients"], [str(self.follower["musicbrainz_row_id"])])
        self.assertEqual(message["payload"]["message"], "for you")
        self.assertEqual(message["idempotency_key"], f"personal_recording_recommendation:{r.json['id']}")

    def test_thanks(self):
        pin = db_pinned_rec.pin(self.db_conn, WritablePinnedRecording(
            user_id=self.author["id"], recording_msid=str(uuid.uuid4())))
        rec = db_user_timeline_event.create_user_track_recommendation_event(
            self.db_conn, self.author["id"], RecordingRecommendationMetadata(recording_msid=str(uuid.uuid4())))

        for event_type, event_id in (("recording_pin", pin.row_id), ("recording_recommendation", rec.id)):
            self.producer.reset_mock()
            self.post("user_timeline_event_api_bp.create_thanks_event", self.follower,
                      {"metadata": {"original_event_type": event_type, "original_event_id": event_id,
                                    "blurb_content": "thanks!"}},
                      user_name="pin_follower")
            message = self.published()
            self.assertEqual(message["recipients"], [str(self.author["musicbrainz_row_id"])])
            self.assertEqual(message["payload"], {
                "actor": self.actor(self.follower), "recording": self.recording(), "message": "thanks!"})
            self.assertEqual(message["idempotency_key"], f"thanks:{self.follower['id']}:{event_type}:{event_id}")

    def test_notification(self):
        bot = db_user.get_or_create(self.db_conn, 303, "troi-bot")
        r = self.post("user_timeline_event_api_bp.create_user_notification_event", bot,
                      {"metadata": {"message": "<b>hello</b>"}}, user_name="pin_author")
        message = self.published()
        self.assertEqual(message["recipients"], [str(self.author["musicbrainz_row_id"])])
        self.assertEqual(message["payload"], {"actor": self.actor(bot), "message": "<b>hello</b>"})
        self.assertEqual(message["idempotency_key"], f"notification:{r.json['id']}")

    @requests_mock.Mocker()
    def test_cb_review(self, mock_requests):
        with self.app.app_context():
            CritiqueBrainzService().add_new_user(self.author["id"], {
                "access_token": "token", "refresh_token": "refresh", "expires_in": 3600})
        review_id = str(uuid.uuid4())
        mock_requests.post(CRITIQUEBRAINZ_REVIEW_SUBMIT_URL, json={"id": review_id})

        self.post("user_timeline_event_api_bp.create_user_cb_review_event", self.author,
                  {"metadata": {"entity_name": "Album", "entity_id": str(uuid.uuid4()),
                                "entity_type": "release_group", "rating": 4, "language": "en",
                                "text": "Good album, would listen again."}},
                  user_name="pin_author")
        message = self.published()
        self.assertEqual(message["payload"]["entity"], {
            "id": review_id, "name": "Album", "type": "review", "url": f"https://critiquebrainz.org/review/{review_id}"})

    def test_chunks_large_audiences(self):
        with self.app.app_context():
            synapse_client._publish("recording_pin", range(1, 5002), {}, "recording_pin:7")
        bodies = [orjson.loads(c.args[0]) for c in self.producer.publish.call_args_list]
        self.assertEqual([b["idempotency_key"] for b in bodies], ["recording_pin:7", "recording_pin:7:1"])
        self.assertEqual([len(b["recipients"]) for b in bodies], [5000, 1])

    def test_skips_recording_without_names(self):
        self.patch("listenbrainz.synapse_client.fetch_track_metadata_for_items", side_effect=lambda _, items: items)
        self.pin()
        self.producer.publish.assert_not_called()

    def test_off_skips_all_work(self):
        self.patch("listenbrainz.synapse_client._producer_pool", new=None)
        get_followers = self.patch("listenbrainz.db.user_relationship.get_followers_of_user")
        self.pin()
        get_followers.assert_not_called()

    def test_failures_do_not_fail_the_request(self):
        self.pool.acquire.side_effect = ConnectionError("RabbitMQ is down")
        self.post("social_api_v1.follow_user", self.author, {}, user_name="pin_follower")
        self.pool.acquire.assert_called_once()

        self.patch("listenbrainz.db.user_relationship.get_followers_of_user", side_effect=RuntimeError("db timeout"))
        self.pin()
