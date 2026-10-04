import json
import uuid
from types import SimpleNamespace
from unittest.mock import ANY, patch

import listenbrainz.db.user as db_user
import listenbrainz.db.user_artist_relationship as db_user_artist_relationship
from listenbrainz.tests.integration import IntegrationTestCase


class SocialAPITestCase(IntegrationTestCase):

    def setUp(self):
        super().setUp()
        self.user = db_user.get_or_create(self.db_conn, 1, "testuserpleaseignore")
        db_user.agree_to_gdpr(self.db_conn, self.user["musicbrainz_id"])
        self.artist_mbid = str(uuid.uuid4())

    def _follow(self, mbid, token):
        return self.client.post(
            self.custom_url_for("social_api_v1.follow_artist"),
            data=json.dumps({"artist_mbid": mbid}),
            headers={"Authorization": "Token %s" % token},
            content_type="application/json",
        )

    def _unfollow(self, mbid, token):
        return self.client.post(
            self.custom_url_for("social_api_v1.unfollow_artist"),
            data=json.dumps({"artist_mbid": mbid}),
            headers={"Authorization": "Token %s" % token},
            content_type="application/json",
        )

    def test_follow_artist(self):
        resp = self._follow(self.artist_mbid, self.user["auth_token"])
        self.assert200(resp)
        self.assertEqual(resp.json, {"status": "ok"})

    def test_follow_artist_invalid_mbid(self):
        resp = self._follow("not-a-uuid", self.user["auth_token"])
        self.assert400(resp)

    def test_follow_artist_no_body(self):
        resp = self.client.post(
            self.custom_url_for("social_api_v1.follow_artist"),
            headers={"Authorization": "Token %s" % self.user["auth_token"]},
            content_type="application/json",
        )
        self.assert400(resp)

    def test_follow_artist_unauthorized(self):
        resp = self.client.post(
            self.custom_url_for("social_api_v1.follow_artist"),
            data=json.dumps({"artist_mbid": self.artist_mbid}),
            content_type="application/json",
        )
        self.assert401(resp)

    def test_follow_artist_twice_leads_to_error(self):
        resp1 = self._follow(self.artist_mbid, self.user["auth_token"])
        self.assert200(resp1)
        resp2 = self._follow(self.artist_mbid, self.user["auth_token"])
        self.assert400(resp2)

        rows = db_user_artist_relationship.get_followed_artist_mbids(self.db_conn, self.user["id"])
        self.assertEqual(len(rows), 1)

    def test_unfollow_artist(self):
        self._follow(self.artist_mbid, self.user["auth_token"])
        resp = self._unfollow(self.artist_mbid, self.user["auth_token"])
        self.assert200(resp)
        self.assertEqual(resp.json, {"status": "ok"})
        rows = db_user_artist_relationship.get_followed_artist_mbids(self.db_conn, self.user["id"])
        self.assertEqual(len(rows), 0)

    def test_unfollow_artist_not_following(self):
        resp = self._unfollow(self.artist_mbid, self.user["auth_token"])
        self.assert200(resp)
        self.assertEqual(resp.json, {"status": "ok"})

    def test_get_followed_artists_empty(self):
        resp = self.client.get(
            self.custom_url_for("social_api_v1.get_followed_artists", user_name=self.user["musicbrainz_id"])
        )
        self.assert200(resp)
        data = resp.json
        self.assertEqual(data["followed_artists"], [])
        self.assertEqual(data["count"], 0)
        self.assertEqual(data["user"], self.user["musicbrainz_id"])

    def test_get_followed_artists(self):
        self._follow(self.artist_mbid, self.user["auth_token"])
        resp = self.client.get(
            self.custom_url_for("social_api_v1.get_followed_artists", user_name=self.user["musicbrainz_id"])
        )
        self.assert200(resp)
        data = resp.json
        self.assertIn(self.artist_mbid, data["followed_artists"])
        self.assertEqual(data["count"], 1)

    def test_get_followed_artists_user_not_found(self):
        resp = self.client.get(
            self.custom_url_for("social_api_v1.get_followed_artists", user_name="doesnotexist_xyz")
        )
        self.assert404(resp)

    def test_get_followed_artists_large_count(self):
        resp = self.client.get(
            self.custom_url_for("social_api_v1.get_followed_artists",
                                user_name=self.user["musicbrainz_id"], count=9999)
        )
        self.assert200(resp)

    def test_get_artist_follow_status(self):
        self._follow(self.artist_mbid, self.user["auth_token"])
        resp = self.client.get(
            self.custom_url_for("social_api_v1.get_artist_follow_status",
                                user_name=self.user["musicbrainz_id"], artist_mbid=self.artist_mbid)
        )
        self.assert200(resp)
        self.assertEqual(resp.json, {
            "artist_mbid": self.artist_mbid,
            "following": True,
            "user": self.user["musicbrainz_id"],
        })

    def test_get_artist_follow_status_not_following(self):
        resp = self.client.get(
            self.custom_url_for("social_api_v1.get_artist_follow_status",
                                user_name=self.user["musicbrainz_id"], artist_mbid=self.artist_mbid)
        )
        self.assert200(resp)
        self.assertFalse(resp.json["following"])

    def test_get_artist_follow_status_invalid_mbid(self):
        resp = self.client.get(
            self.custom_url_for("social_api_v1.get_artist_follow_status",
                                user_name=self.user["musicbrainz_id"], artist_mbid="not-a-uuid")
        )
        self.assert400(resp)

    def test_get_artist_follow_status_user_not_found(self):
        resp = self.client.get(
            self.custom_url_for("social_api_v1.get_artist_follow_status",
                                user_name="doesnotexist_xyz", artist_mbid=self.artist_mbid)
        )
        self.assert404(resp)

    def test_get_events_for_followed_artists_no_follows(self):
        resp = self.client.get(
            self.custom_url_for("social_api_v1.get_events_for_followed_artists",
                                user_name=self.user["musicbrainz_id"])
        )
        self.assert200(resp)
        payload = resp.json["payload"]
        self.assertEqual(payload["events"], [])
        self.assertEqual(payload["count"], 0)
        self.assertEqual(payload["user"], self.user["musicbrainz_id"])

    def test_get_events_for_followed_artists_none_upcoming(self):
        self._follow(self.artist_mbid, self.user["auth_token"])
        resp = self.client.get(
            self.custom_url_for("social_api_v1.get_events_for_followed_artists",
                                user_name=self.user["musicbrainz_id"])
        )
        self.assert200(resp)
        payload = resp.json["payload"]
        self.assertEqual(payload["events"], [])
        self.assertEqual(payload["count"], 0)
        self.assertEqual(payload["offset"], 0)
        self.assertEqual(payload["user"], self.user["musicbrainz_id"])

    def test_get_events_for_followed_artists_user_not_found(self):
        resp = self.client.get(
            self.custom_url_for("social_api_v1.get_events_for_followed_artists",
                                user_name="doesnotexist_xyz")
        )
        self.assert404(resp)

    def test_get_events_for_followed_artists_large_count(self):
        resp = self.client.get(
            self.custom_url_for("social_api_v1.get_events_for_followed_artists",
                                user_name=self.user["musicbrainz_id"], count=9999)
        )
        self.assert200(resp)

    @patch("listenbrainz.db.event_feed.get_upcoming_events_for_artists", return_value=[])
    def test_get_events_for_followed_artists_window(self, mock_events):
        self._follow(self.artist_mbid, self.user["auth_token"])
        resp = self.client.get(
            self.custom_url_for("social_api_v1.get_events_for_followed_artists",
                                user_name=self.user["musicbrainz_id"], days=30, past="true", cancelled="true")
        )
        self.assert200(resp)
        mock_events.assert_called_with(ANY, [self.artist_mbid], 25, 0, days=30, past=True, future=True, cancelled=True)

    def test_get_events_for_followed_artists_invalid_window(self):
        resp = self.client.get(
            self.custom_url_for("social_api_v1.get_events_for_followed_artists",
                                user_name=self.user["musicbrainz_id"], past="true")
        )
        self.assert400(resp)

    @patch("listenbrainz.db.stats.get", return_value=None)
    def test_get_events_for_listened_artists_no_stats(self, mock_stats):
        resp = self.client.get(
            self.custom_url_for("social_api_v1.get_events_for_listened_artists",
                                user_name=self.user["musicbrainz_id"])
        )
        self.assert200(resp)
        payload = resp.json["payload"]
        self.assertEqual(payload["events"], [])
        self.assertEqual(payload["count"], 0)
        self.assertEqual(payload["offset"], 0)
        self.assertEqual(payload["user"], self.user["musicbrainz_id"])

    @patch("listenbrainz.db.event_feed.add_performers_to_events")
    @patch("listenbrainz.db.event_feed.get_upcoming_events_for_artists", return_value=[])
    @patch("listenbrainz.db.stats.get")
    def test_get_events_for_listened_artists(self, mock_stats, mock_events, mock_add_performers):
        other_artist_mbid = str(uuid.uuid4())
        mock_stats.return_value = SimpleNamespace(data=[
            SimpleNamespace(artist_mbid=self.artist_mbid, listen_count=40),
            SimpleNamespace(artist_mbid=other_artist_mbid, listen_count=7),
            SimpleNamespace(artist_mbid=None, listen_count=100),
        ])
        mock_add_performers.return_value = [
            {"event_name": "Both", "performers": [{"artist_mbid": other_artist_mbid}, {"artist_mbid": self.artist_mbid}]},
            {"event_name": "Neither", "performers": [{"artist_mbid": str(uuid.uuid4())}]},
        ]

        resp = self.client.get(
            self.custom_url_for("social_api_v1.get_events_for_listened_artists",
                                user_name=self.user["musicbrainz_id"], days=90)
        )
        self.assert200(resp)
        mock_stats.assert_called_with(self.user["id"], "artists", "all_time", ANY)
        mock_events.assert_called_with(
            ANY, [self.artist_mbid, other_artist_mbid], 25, 0, days=90, past=False, future=True, cancelled=False
        )
        events = resp.json["payload"]["events"]
        self.assertEqual([40, 0], [event["user_listen_count"] for event in events])

    def test_get_events_for_listened_artists_user_not_found(self):
        resp = self.client.get(
            self.custom_url_for("social_api_v1.get_events_for_listened_artists", user_name="doesnotexist_xyz")
        )
        self.assert404(resp)
