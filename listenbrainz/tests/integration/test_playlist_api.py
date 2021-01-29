from unittest import mock
from uuid import UUID

import dateutil.parser
from flask import url_for, current_app
from redis import Redis
from listenbrainz.tests.integration import IntegrationTestCase
import listenbrainz.db.user as db_user
from listenbrainz.webserver.views.api import DEFAULT_NUMBER_OF_PLAYLISTS_PER_CALL
from listenbrainz.webserver.views import playlist_api
from listenbrainz.webserver.views.playlist_api import PLAYLIST_TRACK_URI_PREFIX, PLAYLIST_URI_PREFIX, PLAYLIST_EXTENSION_URI


# NOTE: This test module includes all the tests for playlist features, even those served from the
#       user API endpoint!

def get_test_data():
    return {
       "playlist": {
          "title": "1980s flashback jams",
          "annotation": "your lame <i>80s</i> music",
          "extension": {
              PLAYLIST_EXTENSION_URI: {
                  "public": True
              }
          },
          "track": [
             {
                "identifier": "https://musicbrainz.org/recording/e8f9b188-f819-4e43-ab0f-4bd26ce9ff56"
             }
          ],
       }
    }


class PlaylistAPITestCase(IntegrationTestCase):
    """
        Base class to properly setup our test environment.
    """

    def setUp(self):
        super(PlaylistAPITestCase, self).setUp()
        self.user = db_user.get_or_create(1, "testuserpleaseignore")
        self.user2 = db_user.get_or_create(2, "anothertestuserpleaseignore")
        self.user3 = db_user.get_or_create(3, "troi-bot")
        self.user4 = db_user.get_or_create(4, "iloveassgaskets")

    def tearDown(self):
        r = Redis(host=current_app.config['REDIS_HOST'], port=current_app.config['REDIS_PORT'])
        r.flushall()
        super(PlaylistAPITestCase, self).tearDown()

    def test_filter_description(self):
        """Check that non-approved html tags are filtered from descriptions"""

        # a href to unapproved domain
        description = """<a href="http://gooogle.com">link to google</a>"""
        result = playlist_api._filter_description_html(description)
        assert result == "<a>link to google</a>"

        # a href to approved domain
        description = """<a href="http://acousticbrainz.org/foo">link to AB</a>"""
        result = playlist_api._filter_description_html(description)
        assert result == description

        # non-approved tag
        description = """<input>input tag</input>"""
        result = playlist_api._filter_description_html(description)
        assert result == "input tag"

        # OK tags
        description = """<b>Your amazing playlist</b><br><ul><li>wow</li><li>such playlist</li></ul>
        <a href="https://listenbrainz.org/user/is/you">more info</a>"""
        result = playlist_api._filter_description_html(description)
        assert result == description

    @mock.patch('listenbrainz.webserver.views.playlist_api.fetch_playlist_recording_metadata')
    def test_playlist_create_and_get(self, mock_fetch_playlist_recording_metadata):
        """ Test to ensure creating a playlist works """

        playlist = get_test_data()

        response = self.client.post(
            url_for("playlist_api_v1.create_playlist"),
            json=playlist,
            headers={"Authorization": "Token {}".format(self.user["auth_token"])}
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
        self.assertEqual(response.json["playlist"]["identifier"], PLAYLIST_URI_PREFIX + playlist_mbid)
        self.assertEqual(response.json["playlist"]["annotation"], "your lame <i>80s</i> music")
        self.assertEqual(response.json["playlist"]["track"][0]["identifier"],
                         playlist["playlist"]["track"][0]["identifier"])
        mock_fetch_playlist_recording_metadata.assert_called_once()
        try:
            dateutil.parser.isoparse(response.json["playlist"]["extension"][PLAYLIST_EXTENSION_URI]["last_modified_at"])
        except ValueError:
            assert False

    @mock.patch('listenbrainz.webserver.views.playlist_api.fetch_playlist_recording_metadata')
    def test_playlist_create_with_created_for(self, mock_fetch_playlist_recording_metadata):
        """ Test to ensure creating a playlist for someone else works """

        # Submit a playlist on a different user's behalf
        playlist = get_test_data()
        playlist["playlist"]["created_for"] = self.user["musicbrainz_id"]

        response = self.client.post(
            url_for("playlist_api_v1.create_playlist"),
            json=playlist,
            headers={"Authorization": "Token {}".format(self.user3["auth_token"])}
        )
        self.assert200(response)
        playlist_mbid = response.json["playlist_mbid"]

        response = self.client.get(
            url_for("playlist_api_v1.get_playlist", playlist_mbid=playlist_mbid),
            headers={"Authorization": "Token {}".format(self.user["auth_token"])}
        )
        self.assert200(response)
        self.assertEqual(response.json["playlist"]["extension"]
                         [PLAYLIST_EXTENSION_URI]["created_for"], self.user["musicbrainz_id"])
        mock_fetch_playlist_recording_metadata.assert_called_once()

        # Try to submit a playlist on a different users's behalf without the right perms
        # (a user must be part of config. APPROVED_PLAYLIST_BOTS to be able to create playlists
        # on behalf of someone else)
        response = self.client.post(
            url_for("playlist_api_v1.create_playlist"),
            json=playlist,
            headers={"Authorization": "Token {}".format(self.user["auth_token"])}
        )
        self.assert403(response)

    def test_playlist_get_non_existent(self):
        """ Test to ensure fetching a non existent playlist gives 404 """

        response = self.client.get(
            url_for("playlist_api_v1.get_playlist", playlist_mbid="0ebcde36-1b14-4be5-ad3e-a088caf69134"),
            headers={"Authorization": "Token {}".format(self.user["auth_token"])}
        )
        self.assert404(response)

    def test_playlist_create_and_get_private(self):
        """ Test to ensure creating a private playlist works """

        playlist = get_test_data()

        playlist["playlist"]["extension"][PLAYLIST_EXTENSION_URI]["public"] = False
        response = self.client.post(
            url_for("playlist_api_v1.create_playlist"),
            json=playlist,
            headers={"Authorization": "Token {}".format(self.user["auth_token"])}
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
           "playlist": {
              "title": "yer dreams suck!",
              "extension": {
                  PLAYLIST_EXTENSION_URI: {
                      "public": True
                  }
              },
           }
        }

        response = self.client.post(
            url_for("playlist_api_v1.create_playlist"),
            json=playlist,
            headers={"Authorization": "Token {}".format(self.user["auth_token"])}
        )
        self.assert200(response)
        self.assertEqual(response.json["status"], "ok")
        self.assertNotEqual(response.json["playlist_mbid"], "")

        # Make sure the return playlist id is valid
        UUID(response.json["playlist_mbid"])

    def test_playlist_json_with_missing_keys(self):
        """ Test for checking that submitting JSON with missing keys returns 400 """

        # submit a playlist without title
        playlist = {
           "playlist": {
              "track": [
                 {
                    "identifier": "https://musicbrainz.org/recording/e8f9b188-f819-4e43-ab0f-4bd26ce9ff56"
                 }
              ],
              "extension": {
                  PLAYLIST_EXTENSION_URI: {
                      "public": True
                  }
              },
           }
        }

        response = self.client.post(
            url_for("playlist_api_v1.create_playlist"),
            json=playlist,
            headers={"Authorization": "Token {}".format(self.user["auth_token"])}
        )
        self.assert400(response)
        self.assertEqual(response.json["error"], "JSPF playlist must contain a title element with the title of the playlist.")

        # submit a playlist without public defined
        playlist = {
           "playlist": {
              "title": "no, you're a douche!",
              "track": [
                 {
                    "identifier": "https://musicbrainz.org/recording/e8f9b188-f819-4e43-ab0f-4bd26ce9ff56"
                 }
              ],
           }
        }

        response = self.client.post(
            url_for("playlist_api_v1.create_playlist"),
            json=playlist,
            headers={"Authorization": "Token {}".format(self.user["auth_token"])}
        )
        self.assert400(response)
        self.assertEqual(response.json["error"], "JSPF playlist.extension.https://musicbrainz.org/doc/jspf#playlist.public field must be given.")

        # submit a playlist with non-boolean public
        playlist = {
            "playlist": {
                "title": "no, you're a douche!",
                "track": [
                    {
                        "identifier": "https://musicbrainz.org/recording/e8f9b188-f819-4e43-ab0f-4bd26ce9ff56"
                    }
                ],
                "extension": {
                    PLAYLIST_EXTENSION_URI: {
                        "public": "yes"
                    }
                },
            }
        }

        response = self.client.post(
            url_for("playlist_api_v1.create_playlist"),
            json=playlist,
            headers={"Authorization": "Token {}".format(self.user["auth_token"])}
        )
        self.assert400(response)
        self.assertEqual(response.json["error"], "JSPF playlist public field must contain a boolean.")

        # submit a playlist with empty collaborator
        playlist = {
            "playlist": {
                "title": "no, you're a douche!",
                "track": [
                    {
                        "identifier": "https://musicbrainz.org/recording/e8f9b188-f819-4e43-ab0f-4bd26ce9ff56"
                    }
                ],
                "extension": {
                    PLAYLIST_EXTENSION_URI: {
                        "public": True,
                        "collaborators": ["one", ""]
                    }
                },
            }
        }

        response = self.client.post(
            url_for("playlist_api_v1.create_playlist"),
            json=playlist,
            headers={"Authorization": "Token {}".format(self.user["auth_token"])}
        )
        self.assert400(response)
        self.assertEqual(response.json["error"],
                         "The collaborators field contains an empty value.")

        # submit a playlist with invalid track identifier
        playlist = {
            "playlist": {
                "title": "no, you're a douche!",
                "track": [
                    {
                        "identifier": "https://someoneelse.com/e8f9b188-f819-4e43-ab0f-4bd26ce9ff56"
                    }
                ],
                "extension": {
                    PLAYLIST_EXTENSION_URI: {
                        "public": True,
                    }
                },
            }
        }

        response = self.client.post(
            url_for("playlist_api_v1.create_playlist"),
            json=playlist,
            headers={"Authorization": "Token {}".format(self.user["auth_token"])}
        )
        self.assert400(response)
        self.assertEqual(response.json["error"],
                         "JSPF playlist track 0 identifier must have the namespace 'https://musicbrainz.org/recording/' prepended to it.")

    @mock.patch('listenbrainz.webserver.views.playlist_api.fetch_playlist_recording_metadata')
    def test_playlist_create_with_collaborators(self, mock_fetch_playlist_recording_metadata):
        """ Test to ensure creating a playlist with collaborators works """

        playlist = get_test_data()
        # If the owner is in collaborators, it should be filtered out
        # If a collaborator is listed multiple times, it should only be added once
        playlist["playlist"]["extension"][PLAYLIST_EXTENSION_URI]["collaborators"] = [self.user["musicbrainz_id"],
                                                                                      self.user2["musicbrainz_id"],
                                                                                      self.user2["musicbrainz_id"]]

        response = self.client.post(
            url_for("playlist_api_v1.create_playlist"),
            json=playlist,
            headers={"Authorization": "Token {}".format(self.user["auth_token"])}
        )
        self.assert200(response)
        self.assertEqual(response.json["status"], "ok")
        self.assertNotEqual(response.json["playlist_mbid"], "")

        playlist_mbid = response.json["playlist_mbid"]

        response = self.client.get(
            url_for("playlist_api_v1.get_playlist", playlist_mbid=playlist_mbid),
        )
        self.assert200(response)
        self.assertEqual(response.json["playlist"]["extension"]
                         [PLAYLIST_EXTENSION_URI]["collaborators"], [self.user2["musicbrainz_id"]])
        mock_fetch_playlist_recording_metadata.assert_called_once()

        # Check that this playlist shows up on the collaborators endpoint
        response = self.client.get(
            url_for("api_v1.get_playlists_collaborated_on_for_user", playlist_user_name=self.user2["musicbrainz_id"]),
            headers={"Authorization": "Token {}".format(self.user4["auth_token"])},
        )
        self.assert200(response)
        self.assertEqual(response.json["playlist_count"], 1)
        self.assertEqual(response.json["playlists"][0]["playlist"]["extension"] \
                         [PLAYLIST_EXTENSION_URI]["collaborators"], [self.user2["musicbrainz_id"]])

        # Check private too

    @mock.patch('listenbrainz.webserver.views.playlist_api.fetch_playlist_recording_metadata')
    def test_playlist_edit(self, mock_fetch_playlist_recording_metadata):
        """ Test to ensure editing a playlist works """

        playlist = get_test_data()

        response = self.client.post(
            url_for("playlist_api_v1.create_playlist"),
            json=playlist,
            headers={"Authorization": "Token {}".format(self.user["auth_token"])}
        )
        self.assert200(response)
        self.assertEqual(response.json["status"], "ok")
        self.assertNotEqual(response.json["playlist_mbid"], "")

        playlist_mbid = response.json["playlist_mbid"]

        # Test to ensure posting a playlist works
        # Owner is in collaborators, should be filtered out
        response = self.client.post(
            url_for("playlist_api_v1.edit_playlist", playlist_mbid=playlist_mbid),
            json={"playlist": {"title": "new title",
                               "annotation": "new <b>desc</b> <script>noscript</script>",
                               "extension": {PLAYLIST_EXTENSION_URI: {"public": False,
                                                                      "collaborators": [self.user["musicbrainz_id"],
                                                                                        self.user2["musicbrainz_id"],
                                                                                        self.user3["musicbrainz_id"]]}
                                             }}},
            headers={"Authorization": "Token {}".format(self.user["auth_token"])}
        )
        self.assert200(response)

        response = self.client.get(
            url_for("playlist_api_v1.get_playlist", playlist_mbid=playlist_mbid),
            headers={"Authorization": "Token {}".format(self.user["auth_token"])}
        )

        self.assertEqual(response.json["playlist"]["title"], "new title")
        self.assertEqual(response.json["playlist"]["annotation"], "new <b>desc</b> noscript")
        self.assertEqual(response.json["playlist"]["extension"]
                         [PLAYLIST_EXTENSION_URI]["public"], False)
        self.assertEqual(response.json["playlist"]["extension"]
                         [PLAYLIST_EXTENSION_URI]["collaborators"], [self.user2["musicbrainz_id"],
                                                                     self.user3["musicbrainz_id"]])
        mock_fetch_playlist_recording_metadata.assert_called_once()

        # Edit again to remove description and collaborators
        response = self.client.post(
            url_for("playlist_api_v1.edit_playlist", playlist_mbid=playlist_mbid),
            json={"playlist": {"annotation": "",
                               "extension": {PLAYLIST_EXTENSION_URI: {
                                   "collaborators": []}}}},
            headers={"Authorization": "Token {}".format(self.user["auth_token"])}
        )
        self.assert200(response)
        response = self.client.get(
            url_for("playlist_api_v1.get_playlist", playlist_mbid=playlist_mbid),
            headers={"Authorization": "Token {}".format(self.user["auth_token"])}
        )

        self.assertEqual(response.json["playlist"]["title"], "new title")
        self.assertNotIn("annotation", response.json["playlist"])
        self.assertEqual(response.json["playlist"]["extension"]
                         [PLAYLIST_EXTENSION_URI]["public"], False)
        self.assertNotIn("collaborators", response.json["playlist"]["extension"][PLAYLIST_EXTENSION_URI])

    @mock.patch('listenbrainz.webserver.views.playlist_api.fetch_playlist_recording_metadata')
    def test_playlist_recording_add(self, mock_fetch_playlist_recording_metadata):
        """ Test adding a recording to a playlist works """

        playlist = get_test_data()

        response = self.client.post(
            url_for("playlist_api_v1.create_playlist"),
            json=playlist,
            headers={"Authorization": "Token {}".format(self.user["auth_token"])}
        )
        self.assert200(response)
        playlist_mbid = response.json["playlist_mbid"]

        # Add a track to the playlist
        add_recording = {
           "playlist": {
              "track": [
                 {
                    "identifier": PLAYLIST_TRACK_URI_PREFIX + "4a77a078-e91a-4522-a409-3b58aa7de3ae"
                 }
              ],
              "extension": {
                  PLAYLIST_EXTENSION_URI: {
                      "public": True
                  }
              },
           }
        }
        response = self.client.post(
            url_for("playlist_api_v1.add_playlist_item", playlist_mbid=playlist_mbid),
            headers={"Authorization": "Token {}".format(self.user["auth_token"])},
            json=add_recording
        )
        self.assert200(response)

        response = self.client.get(
            url_for("playlist_api_v1.get_playlist", playlist_mbid=playlist_mbid),
            headers={"Authorization": "Token {}".format(self.user["auth_token"])}
        )
        self.assertEqual(response.json["playlist"]["creator"], "testuserpleaseignore")
        self.assertEqual(response.json["playlist"]["identifier"], PLAYLIST_URI_PREFIX + playlist_mbid)
        self.assertEqual(response.json["playlist"]["track"][0]["identifier"],
                         playlist["playlist"]["track"][0]["identifier"])
        self.assertEqual(response.json["playlist"]["track"][1]["identifier"],
                         add_recording["playlist"]["track"][0]["identifier"])
        mock_fetch_playlist_recording_metadata.assert_called_once()

        # Add an invalid track id to the playlist
        add_recording = {
           "playlist": {
              "track": [
                 {
                    "identifier": "4a77a078-e91a-4522-a409-3b58aa7de3ae"
                 }
              ],
           }
        }
        response = self.client.post(
            url_for("playlist_api_v1.add_playlist_item", playlist_mbid=playlist_mbid),
            headers={"Authorization": "Token {}".format(self.user["auth_token"])},
            json=add_recording
        )
        self.assert400(response)

    @mock.patch('listenbrainz.webserver.views.playlist_api.fetch_playlist_recording_metadata')
    def test_playlist_recording_move(self, mock_fetch_playlist_recording_metadata):

        playlist = {
           "playlist": {
              "title": "1980s flashback jams",
              "track": [
                 {
                    "identifier": PLAYLIST_TRACK_URI_PREFIX + "e8f9b188-f819-4e43-ab0f-4bd26ce9ff56"
                 },
                 {
                    "identifier": PLAYLIST_TRACK_URI_PREFIX + "57ef4803-5181-4b3d-8dd6-8b9d9ca83e2a"
                 }
              ],
              "extension": {
                  PLAYLIST_EXTENSION_URI: {
                      "public": True
                  }
              },
           }
        }

        response = self.client.post(
            url_for("playlist_api_v1.create_playlist"),
            json=playlist,
            headers={"Authorization": "Token {}".format(self.user["auth_token"])}
        )
        self.assert200(response)
        playlist_mbid = response.json["playlist_mbid"]

        move = {"mbid": "57ef4803-5181-4b3d-8dd6-8b9d9ca83e2a", "from": 1, "to": 0, "count": 1}
        response = self.client.post(
            url_for("playlist_api_v1.move_playlist_item", playlist_mbid=playlist_mbid),
            headers={"Authorization": "Token {}".format(self.user["auth_token"])},
            json=move
        )
        self.assert200(response)

        response = self.client.get(
            url_for("playlist_api_v1.get_playlist", playlist_mbid=playlist_mbid),
            headers={"Authorization": "Token {}".format(self.user["auth_token"])}
        )
        self.assertEqual(response.json["playlist"]["creator"], "testuserpleaseignore")
        self.assertEqual(response.json["playlist"]["identifier"], PLAYLIST_URI_PREFIX + playlist_mbid)
        self.assertEqual(response.json["playlist"]["track"][0]["identifier"],
                         playlist["playlist"]["track"][1]["identifier"])
        self.assertEqual(response.json["playlist"]["track"][1]["identifier"],
                         playlist["playlist"]["track"][0]["identifier"])
        mock_fetch_playlist_recording_metadata.assert_called_once()

    @mock.patch('listenbrainz.webserver.views.playlist_api.fetch_playlist_recording_metadata')
    def test_playlist_recording_delete(self, mock_fetch_playlist_recording_metadata):
        playlist = {
           "playlist": {
              "title": "1980s flashback jams",
              "track": [
                 {
                    "identifier": PLAYLIST_TRACK_URI_PREFIX + "e8f9b188-f819-4e43-ab0f-4bd26ce9ff56"
                 },
                 {
                    "identifier": PLAYLIST_TRACK_URI_PREFIX + "57ef4803-5181-4b3d-8dd6-8b9d9ca83e2a"
                 }
              ],
              "extension": {
                  PLAYLIST_EXTENSION_URI: {
                      "public": True
                  }
              },
           }
        }

        response = self.client.post(
            url_for("playlist_api_v1.create_playlist"),
            json=playlist,
            headers={"Authorization": "Token {}".format(self.user["auth_token"])}
        )
        self.assert200(response)
        playlist_mbid = response.json["playlist_mbid"]

        move = {"index": 0, "count": 1}
        response = self.client.post(
            url_for("playlist_api_v1.delete_playlist_item", playlist_mbid=playlist_mbid),
            headers={"Authorization": "Token {}".format(self.user["auth_token"])},
            json=move
        )
        self.assert200(response)

        response = self.client.get(
            url_for("playlist_api_v1.get_playlist", playlist_mbid=playlist_mbid),
            headers={"Authorization": "Token {}".format(self.user["auth_token"])}
        )
        self.assertEqual(response.json["playlist"]["creator"], "testuserpleaseignore")
        self.assertEqual(response.json["playlist"]["identifier"], PLAYLIST_URI_PREFIX + playlist_mbid)
        self.assertEqual(response.json["playlist"]["track"][0]["identifier"],
                         playlist["playlist"]["track"][1]["identifier"])
        mock_fetch_playlist_recording_metadata.assert_called_once()

    def test_playlist_delete_playlist(self):

        playlist = {
           "playlist": {
              "title": "yer dreams suck!",
              "extension": {
                  PLAYLIST_EXTENSION_URI: {
                      "public": True
                  }
              },
           }
        }

        response = self.client.post(
            url_for("playlist_api_v1.create_playlist"),
            json=playlist,
            headers={"Authorization": "Token {}".format(self.user["auth_token"])}
        )
        self.assert200(response)
        playlist_mbid = response.json["playlist_mbid"]

        response = self.client.post(
            url_for("playlist_api_v1.delete_playlist", playlist_mbid=playlist_mbid),
            json={},
            headers={"Authorization": "Token {}".format(self.user["auth_token"])}
        )
        self.assert200(response)

        response = self.client.get(
            url_for("playlist_api_v1.get_playlist", playlist_mbid=playlist_mbid),
            headers={"Authorization": "Token {}".format(self.user["auth_token"])}
        )
        self.assert404(response)

    def test_playlist_copy_public_playlist(self):

        playlist = {
           "playlist": {
              "title": "my stupid playlist",
              "extension": {
                  PLAYLIST_EXTENSION_URI: {
                      "public": True,
                      "collaborators": [self.user2["musicbrainz_id"],
                                        self.user3["musicbrainz_id"]]
                  }
              },
           }
        }

        response = self.client.post(
            url_for("playlist_api_v1.create_playlist"),
            json=playlist,
            headers={"Authorization": "Token {}".format(self.user["auth_token"])}
        )
        self.assert200(response)
        playlist_mbid = response.json["playlist_mbid"]

        response = self.client.post(
            url_for("playlist_api_v1.copy_playlist", playlist_mbid=playlist_mbid),
            json={},
            headers={"Authorization": "Token {}".format(self.user2["auth_token"])}
        )
        self.assert200(response)
        new_playlist_mbid = response.json["playlist_mbid"]
        self.assertNotEqual(playlist_mbid, new_playlist_mbid)

        response = self.client.get(
            url_for("playlist_api_v1.get_playlist", playlist_mbid=new_playlist_mbid),
            headers={"Authorization": "Token {}".format(self.user["auth_token"])}
        )
        self.assert200(response)
        self.assertEqual(response.json["playlist"]["identifier"], PLAYLIST_URI_PREFIX + new_playlist_mbid)
        self.assertEqual(response.json["playlist"]["extension"] \
                         [PLAYLIST_EXTENSION_URI]["copied_from_mbid"], \
                         PLAYLIST_URI_PREFIX + playlist_mbid)
        self.assertEqual(response.json["playlist"]["extension"] \
                         [PLAYLIST_EXTENSION_URI]["public"], True)
        self.assertEqual(response.json["playlist"]["title"], "Copy of my stupid playlist")
        self.assertEqual(response.json["playlist"]["creator"], "anothertestuserpleaseignore")
        # Ensure original playlist's collaborators have been scrubbed
        self.assertEqual(response.json["playlist"]["extension"]
                         [PLAYLIST_EXTENSION_URI]["collaborators"], [])

        # Now delete the original playlist so that we can test copied from deleted playlist
        response = self.client.post(
            url_for("playlist_api_v1.delete_playlist", playlist_mbid=playlist_mbid),
            json={},
            headers={"Authorization": "Token {}".format(self.user["auth_token"])}
        )
        self.assert200(response)

        response = self.client.get(
            url_for("playlist_api_v1.get_playlist", playlist_mbid=new_playlist_mbid),
            headers={"Authorization": "Token {}".format(self.user["auth_token"])}
        )
        self.assert200(response)
        self.assertEqual(response.json["playlist"]["extension"][PLAYLIST_EXTENSION_URI]["copied_from_deleted"], True)


    def test_playlist_copy_private_playlist(self):

        playlist = {
           "playlist": {
              "title": "my stupid playlist",
              "extension": {
                  PLAYLIST_EXTENSION_URI: {
                      "public": False
                  }
              },
           }
        }

        response = self.client.post(
            url_for("playlist_api_v1.create_playlist"),
            json=playlist,
            headers={"Authorization": "Token {}".format(self.user["auth_token"])}
        )
        self.assert200(response)
        playlist_mbid = response.json["playlist_mbid"]

        response = self.client.post(
            url_for("playlist_api_v1.copy_playlist", playlist_mbid=playlist_mbid),
            json={},
            headers={"Authorization": "Token {}".format(self.user["auth_token"])}
        )
        self.assert200(response)
        new_playlist_mbid = response.json["playlist_mbid"]
        self.assertNotEqual(playlist_mbid, new_playlist_mbid)

        response = self.client.get(
            url_for("playlist_api_v1.get_playlist", playlist_mbid=new_playlist_mbid),
            headers={"Authorization": "Token {}".format(self.user["auth_token"])}
        )
        self.assert200(response)
        self.assertEqual(response.json["playlist"]["extension"][PLAYLIST_EXTENSION_URI]["public"], False)
        self.assertEqual(response.json["playlist"]["title"], "Copy of my stupid playlist")
        self.assertEqual(response.json["playlist"]["creator"], "testuserpleaseignore")

    def test_playlist_private_access(self):
        """ Test for checking that unauthorized access to private playlists return 404 """

        # create a private playlist, then try to access it from the wrong user for all the endpoints
        playlist = get_test_data()
        playlist["playlist"]["extension"][PLAYLIST_EXTENSION_URI]["public"] = False
        response = self.client.post(
            url_for("playlist_api_v1.create_playlist"),
            json=playlist,
            headers={"Authorization": "Token {}".format(self.user["auth_token"])}
        )
        self.assert200(response)
        playlist_mbid = response.json["playlist_mbid"]

        response = self.client.get(
            url_for("playlist_api_v1.get_playlist", playlist_mbid=playlist_mbid),
            headers={"Authorization": "Token {}".format(self.user2["auth_token"])},
        )
        self.assert404(response)

        # Add recording to playlist
        response = self.client.post(
            url_for("playlist_api_v1.add_playlist_item", offset=0, playlist_mbid=playlist_mbid),
            json={},
            headers={"Authorization": "Token {}".format(self.user2["auth_token"])}
        )
        self.assert404(response)

        # Move recording in playlist
        response = self.client.post(
            url_for("playlist_api_v1.move_playlist_item", playlist_mbid=playlist_mbid),
            json={},
            headers={"Authorization": "Token {}".format(self.user2["auth_token"])}
        )
        self.assert404(response)

        # Delete recording in playlist
        response = self.client.post(
            url_for("playlist_api_v1.delete_playlist_item", playlist_mbid=playlist_mbid),
            json={},
            headers={"Authorization": "Token {}".format(self.user2["auth_token"])}
        )
        self.assert404(response)

        # Delete a playlist
        response = self.client.post(
            url_for("playlist_api_v1.delete_playlist", playlist_mbid=playlist_mbid),
            json={},
            headers={"Authorization": "Token {}".format(self.user2["auth_token"])}
        )
        self.assert404(response)

        # Copy a playlist
        response = self.client.post(
            url_for("playlist_api_v1.copy_playlist", playlist_mbid=playlist_mbid),
            json={},
            headers={"Authorization": "Token {}".format(self.user2["auth_token"])}
        )
        self.assert404(response)

    def test_playlist_get_playlists(self):
        """ Test for checking that unauthorized access to private playlists return 404 """

        # create a public and private playlist, then try various forms of access
        playlist = get_test_data()
        playlist["playlist"]["extension"][PLAYLIST_EXTENSION_URI]["public"] = False
        response = self.client.post(
            url_for("playlist_api_v1.create_playlist"),
            json=playlist,
            headers={"Authorization": "Token {}".format(self.user4["auth_token"])}
        )
        self.assert200(response)
        private_playlist_mbid = response.json["playlist_mbid"]

        playlist = get_test_data()
        response = self.client.post(
            url_for("playlist_api_v1.create_playlist"),
            json=playlist,
            headers={"Authorization": "Token {}".format(self.user4["auth_token"])}
        )
        self.assert200(response)
        public_playlist_mbid = response.json["playlist_mbid"]

        response = self.client.get(
            url_for("api_v1.get_playlists_for_user", playlist_user_name=self.user4["musicbrainz_id"]),
            headers={"Authorization": "Token {}".format(self.user["auth_token"])},
        )
        self.assert200(response)
        self.assertEqual(response.json["playlist_count"], 1)

        response = self.client.get(
            url_for("api_v1.get_playlists_for_user", playlist_user_name=self.user4["musicbrainz_id"]),
            headers={"Authorization": "Token {}".format(self.user4["auth_token"])},
        )
        self.assert200(response)
        self.assertEqual(response.json["playlist_count"], 2)
        self.assertEqual(response.json["count"], DEFAULT_NUMBER_OF_PLAYLISTS_PER_CALL)
        self.assertEqual(response.json["offset"], 0)
        self.assertEqual(response.json["playlists"][0]["playlist"]["extension"] \
                         [PLAYLIST_EXTENSION_URI]["creator"], self.user4["musicbrainz_id"])
        self.assertEqual(response.json["playlists"][0]["playlist"]["identifier"], PLAYLIST_URI_PREFIX + public_playlist_mbid)
        self.assertEqual(response.json["playlists"][0]["playlist"]["title"], "1980s flashback jams")
        self.assertEqual(response.json["playlists"][0]["playlist"]["annotation"], "your lame <i>80s</i> music")
        self.assertEqual(response.json["playlists"][0]["playlist"]["extension"] \
                         [PLAYLIST_EXTENSION_URI]["public"], True)
        try:
            dateutil.parser.isoparse(response.json["playlists"][0]["playlist"]["date"])
        except ValueError:
            assert False
        self.assertEqual(response.json["playlists"][1]["playlist"]["extension"] \
                         [PLAYLIST_EXTENSION_URI]["creator"], self.user4["musicbrainz_id"])
        self.assertEqual(response.json["playlists"][1]["playlist"]["identifier"], PLAYLIST_URI_PREFIX + private_playlist_mbid)
        self.assertEqual(response.json["playlists"][1]["playlist"]["title"], "1980s flashback jams")
        self.assertEqual(response.json["playlists"][1]["playlist"]["annotation"], "your lame <i>80s</i> music")
        self.assertEqual(response.json["playlists"][1]["playlist"]["extension"] \
                         [PLAYLIST_EXTENSION_URI]["public"], False)
        try:
            dateutil.parser.isoparse(response.json["playlists"][1]["playlist"]["date"])
        except ValueError:
            assert False

        # Test count and offset parameters
        response = self.client.get(
            url_for("api_v1.get_playlists_for_user", playlist_user_name=self.user4["musicbrainz_id"], count=1),
            headers={"Authorization": "Token {}".format(self.user4["auth_token"])},
        )
        self.assert200(response)
        self.assertEqual(len(response.json["playlists"]), 1)
        self.assertEqual(response.json["playlist_count"], 2)
        self.assertEqual(response.json["count"], 1)
        self.assertEqual(response.json["offset"], 0)

        response = self.client.get(
            url_for("api_v1.get_playlists_for_user", playlist_user_name=self.user4["musicbrainz_id"], offset=1, count=1),
            headers={"Authorization": "Token {}".format(self.user4["auth_token"])},
        )
        self.assert200(response)
        self.assertEqual(len(response.json["playlists"]), 1)
        self.assertEqual(response.json["playlist_count"], 2)
        self.assertEqual(response.json["count"], 1)
        self.assertEqual(response.json["offset"], 1)


    def test_playlist_unauthorized_access(self):
        """ Test for checking that unauthorized access return 401 """

        response = self.client.post(
            url_for("playlist_api_v1.create_playlist"),
            json={}
        )
        self.assert401(response)

        playlist_mbid = "d1ff6a3d-f471-416f-94e7-86778b51fa2b"
        # Add recording to playlist
        response = self.client.post(
            url_for("playlist_api_v1.add_playlist_item", offset=0, playlist_mbid=playlist_mbid),
            json={}
        )
        self.assert401(response)

        # Move recording in playlist
        response = self.client.post(
            url_for("playlist_api_v1.move_playlist_item", playlist_mbid=playlist_mbid),
            json={}
        )
        self.assert401(response)

        # Delete recording in playlist
        response = self.client.post(
            url_for("playlist_api_v1.delete_playlist_item", playlist_mbid=playlist_mbid),
            json={}
        )
        self.assert401(response)

        # Delete a playlist
        response = self.client.post(
            url_for("playlist_api_v1.delete_playlist", playlist_mbid=playlist_mbid),
            json={}
        )
        self.assert401(response)

        # Copy a playlist
        response = self.client.post(
            url_for("playlist_api_v1.copy_playlist", playlist_mbid=playlist_mbid),
            json={}
        )
        self.assert401(response)

        # Edit a playlist
        response = self.client.post(
            url_for("playlist_api_v1.edit_playlist", playlist_mbid=playlist_mbid),
            json={}
        )
        self.assert401(response)

    def test_playlist_invalid_user(self):
        """ Test for checking that forbidden access returns 403 """

        playlist = {
           "playlist": {
              "title": "my stupid playlist",
              "extension": {
                  PLAYLIST_EXTENSION_URI: {
                      "public": True
                  }
              },
           }
        }

        response = self.client.post(
            url_for("playlist_api_v1.create_playlist"),
            json=playlist,
            headers={"Authorization": "Token {}".format(self.user["auth_token"])}
        )
        self.assert200(response)
        playlist_mbid = response.json["playlist_mbid"]

        # Add recording to playlist
        response = self.client.post(
            url_for("playlist_api_v1.add_playlist_item", offset=0, playlist_mbid=playlist_mbid),
            json={},
            headers={"Authorization": "Token {}".format(self.user2["auth_token"])}
        )
        self.assert403(response)

        # Move recording in playlist
        response = self.client.post(
            url_for("playlist_api_v1.move_playlist_item", playlist_mbid=playlist_mbid),
            json={},
            headers={"Authorization": "Token {}".format(self.user2["auth_token"])}
        )
        self.assert403(response)

        # Delete recording in playlist
        response = self.client.post(
            url_for("playlist_api_v1.delete_playlist_item", playlist_mbid=playlist_mbid),
            json={},
            headers={"Authorization": "Token {}".format(self.user2["auth_token"])}
        )
        self.assert403(response)

        # Delete a playlist
        response = self.client.post(
            url_for("playlist_api_v1.delete_playlist", playlist_mbid=playlist_mbid),
            json={},
            headers={"Authorization": "Token {}".format(self.user2["auth_token"])}
        )
        self.assert403(response)

        # edit a playlist
        response = self.client.post(
            url_for("playlist_api_v1.edit_playlist", playlist_mbid=playlist_mbid),
            json=playlist,
            headers={"Authorization": "Token {}".format(self.user2["auth_token"])}
        )
        self.assert403(response)
