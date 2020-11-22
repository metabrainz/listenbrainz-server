import ujson
from uuid import UUID
import listenbrainz.db.user as db_user
import listenbrainz.db.playlist as db_playlist

from redis import Redis
from flask import url_for, current_app
from listenbrainz.db.model.playlist import Playlist
from listenbrainz.tests.integration import IntegrationTestCase


class PlaylistAPITestCase(IntegrationTestCase):
    def setUp(self):
        super(PlaylistAPITestCase, self).setUp()
        self.user = db_user.get_or_create(1, "testuserpleaseignore")
        self.user2 = db_user.get_or_create(2, "anothertestuserpleaseignore")

    def tearDown(self):
        r = Redis(host=current_app.config['REDIS_HOST'], port=current_app.config['REDIS_PORT'])
        r.flushall()
        super(PlaylistAPITestCase, self).tearDown()

    def get_test_data(self):
        return {
           "playlist" : {
              "title" : "1980s flashback jams",
              "track" : [
                 {
                    "identifier" : "https://musicbrainz.org/recording/e8f9b188-f819-4e43-ab0f-4bd26ce9ff56"
                 }
              ],
           }
        }

    def test_playlist_create_and_get(self):
        """ Test to ensure creating a playlist works """

        playlist = self.get_test_data()

        response = self.client.post(
            url_for("playlist_api_v1.create_playlist"),
            data=ujson.dumps(playlist),
            headers={"Authorization": "Token {}".format(self.user["auth_token"])},
            content_type="application/json"
        )
        self.assert200(response)
        self.assertEqual(response.json["status"], "ok")
        self.assertNotEqual(response.json["playlist_mbid"], "")

        playlist_mbid = response.json["playlist_mbid"]

        # Make sure the return playlist id is valid
        UUID(response.json["playlist_mbid"])

        # Test to ensure fetching a playlist works
        response = self.client.get(
            url_for("playlist_api_v1.get_playlist", playlist_mbid=playlist_mbid),
            headers={"Authorization": "Token {}".format(self.user["auth_token"])}
        )
        self.assert200(response)
        self.assertEqual(response.json["playlist"]["creator"], "testuserpleaseignore")
        self.assertEqual(response.json["playlist"]["identifier"], playlist_mbid)
        self.assertEqual(response.json["playlist"]["track"][0]["identifier"],
                         playlist["playlist"]["track"][0]["identifier"])

    def test_playlist_get_non_existent(self):
        """ Test to ensure fetching a non existent playlist gives 404 """

        response = self.client.get(
            url_for("playlist_api_v1.get_playlist", playlist_mbid="0ebcde36-1b14-4be5-ad3e-a088caf69134"),
            headers={"Authorization": "Token {}".format(self.user["auth_token"])}
        )
        self.assert404(response)


    def test_playlist_create_and_get_private(self):
        """ Test to ensure creating a private playlist works """

        playlist = self.get_test_data()

        response = self.client.post(
            url_for("playlist_api_v1.create_playlist", public="false"),
            data=ujson.dumps(playlist),
            headers={"Authorization": "Token {}".format(self.user["auth_token"])},
            content_type="application/json"
        )
        self.assert200(response)
        self.assertEqual(response.json["status"], "ok")
        self.assertNotEqual(response.json["playlist_mbid"], "")

        playlist_mbid = response.json["playlist_mbid"]

        # Test to ensure fetching a private playlist from a non-owner fails with 404
        response = self.client.get(
            url_for("playlist_api_v1.get_playlist", playlist_mbid=playlist_mbid),
            headers={"Authorization": "Token {}".format(self.user2["auth_token"])}
        )
        self.assert404(response)


    def test_playlist_create_empty(self):
        """ Test to ensure creating an empty playlist works """

        playlist = {
           "playlist" : {
              "title" : "yer dreams suck!"
           }
        }

        response = self.client.post(
            url_for("playlist_api_v1.create_playlist"),
            data=ujson.dumps(playlist),
            headers={"Authorization": "Token {}".format(self.user["auth_token"])},
            content_type="application/json"
        )
        self.assert200(response)
        self.assertEqual(response.json["status"], "ok")
        self.assertNotEqual(response.json["playlist_mbid"], "")

        # Make sure the return playlist id is valid
        UUID(response.json["playlist_mbid"])


    def test_playlist_unauthorised_submission(self):
        """ Test for checking that unauthorized submissions return 401 """

        playlist = self.get_test_data()

        # request with no authorization header
        response = self.client.post(
            url_for("playlist_api_v1.create_playlist"),
            data=ujson.dumps(playlist),
            content_type="application/json"
        )
        self.assert401(response)

        # request with invalid authorization header
        response = self.client.post(
            url_for("playlist_api_v1.create_playlist"),
            data=ujson.dumps(playlist),
            headers={"Authorization": "Token testtokenplsignore"},
            content_type="application/json"
        )
        self.assert401(response)

    def test_playlist_json_with_missing_keys(self):
        """ Test for checking that submitting JSON with missing keys returns 400 """

        # submit a playlist without title
        playlist = {
           "playlist" : {
              "track" : [
                 {
                    "identifier" : "https://musicbrainz.org/recording/e8f9b188-f819-4e43-ab0f-4bd26ce9ff56"
                 }
              ],
           }
        }

        response = self.client.post(
            url_for("playlist_api_v1.create_playlist"),
            data=ujson.dumps(playlist),
            headers={"Authorization": "Token {}".format(self.user["auth_token"])},
            content_type="application/json"
        )
        self.assert400(response)
        self.assertEqual(response.json["error"], "JSPF playlist must contain a title element with the title of the playlist.")
