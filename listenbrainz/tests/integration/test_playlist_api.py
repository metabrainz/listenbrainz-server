import time
from unittest import mock
from uuid import UUID

import dateutil.parser
import requests_mock

from data.model.external_service import ExternalServiceType
from listenbrainz.domain.spotify import OAUTH_TOKEN_URL
from listenbrainz.tests.integration import IntegrationTestCase
import listenbrainz.db.user as db_user
import listenbrainz.db.external_service_oauth as db_oauth
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
                    "public": True,
                    "additional_metadata": {"give_you_up": "never"}
                }
            },
            "track": [
                {
                    "identifier": ["https://musicbrainz.org/recording/e8f9b188-f819-4e43-ab0f-4bd26ce9ff56"]
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
        self.user = db_user.get_or_create(self.db_conn, 1, "testuserpleaseignore")
        self.user2 = db_user.get_or_create(self.db_conn, 2, "anothertestuserpleaseignore")
        self.user3 = db_user.get_or_create(self.db_conn, 3, "troi-bot")
        self.user4 = db_user.get_or_create(self.db_conn, 4, "iloveassgaskets")

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

    def test_playlist_create_and_get(self):
        """ Test to ensure creating a playlist works """

        playlist = get_test_data()

        response = self.client.post(
            self.custom_url_for("playlist_api_v1.create_playlist"),
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
            self.custom_url_for("playlist_api_v1.get_playlist", playlist_mbid=playlist_mbid, fetch_metadata="false"),
            headers={"Authorization": "Token {}".format(self.user["auth_token"])}
        )
        self.assert200(response)
        self.assertEqual(response.json["playlist"]["creator"], "testuserpleaseignore")
        self.assertEqual(response.json["playlist"]["identifier"], PLAYLIST_URI_PREFIX + playlist_mbid)
        self.assertEqual(response.json["playlist"]["annotation"], "your lame <i>80s</i> music")
        self.assertEqual(response.json["playlist"]["track"][0]["identifier"],
                         playlist["playlist"]["track"][0]["identifier"])
        self.assertNotIn("additional_metadata", response.json["playlist"]["extension"][PLAYLIST_EXTENSION_URI])
        try:
            dateutil.parser.isoparse(response.json["playlist"]["extension"][PLAYLIST_EXTENSION_URI]["last_modified_at"])
        except ValueError:
            assert False

    def test_playlist_create_with_created_for(self):
        """ Test to ensure creating a playlist for someone else works """

        # Submit a playlist on a different user's behalf
        playlist = get_test_data()
        playlist["playlist"]["extension"][PLAYLIST_EXTENSION_URI]["created_for"] = self.user["musicbrainz_id"]

        response = self.client.post(
            self.custom_url_for("playlist_api_v1.create_playlist"),
            json=playlist,
            headers={"Authorization": "Token {}".format(self.user3["auth_token"])}
        )
        self.assert200(response)
        playlist_mbid = response.json["playlist_mbid"]

        response = self.client.get(
            self.custom_url_for("playlist_api_v1.get_playlist", playlist_mbid=playlist_mbid, fetch_metadata="false"),
            headers={"Authorization": "Token {}".format(self.user["auth_token"])}
        )
        self.assert200(response)
        self.assertEqual(response.json["playlist"]["extension"]
                         [PLAYLIST_EXTENSION_URI]["created_for"], self.user["musicbrainz_id"])
        self.assertEqual(response.json["playlist"]["extension"]
                         [PLAYLIST_EXTENSION_URI]["additional_metadata"],
                         playlist["playlist"]["extension"][PLAYLIST_EXTENSION_URI]["additional_metadata"])

        # Try to submit a playlist on a different users's behalf without the right perms
        # (a user must be part of config. APPROVED_PLAYLIST_BOTS to be able to create playlists
        # on behalf of someone else)
        response = self.client.post(
            self.custom_url_for("playlist_api_v1.create_playlist"),
            json=playlist,
            headers={"Authorization": "Token {}".format(self.user["auth_token"])}
        )
        self.assert403(response)

    def test_playlist_get_non_existent(self):
        """ Test to ensure fetching a non existent playlist gives 404 """

        response = self.client.get(
            self.custom_url_for("playlist_api_v1.get_playlist", playlist_mbid="0ebcde36-1b14-4be5-ad3e-a088caf69134", fetch_metadata="false"),
            headers={"Authorization": "Token {}".format(self.user["auth_token"])}
        )
        self.assert404(response)

    def test_playlist_create_and_get_private(self):
        """ Test to ensure creating a private playlist works """

        playlist = get_test_data()

        playlist["playlist"]["extension"][PLAYLIST_EXTENSION_URI]["public"] = False
        response = self.client.post(
            self.custom_url_for("playlist_api_v1.create_playlist"),
            json=playlist,
            headers={"Authorization": "Token {}".format(self.user["auth_token"])}
        )
        self.assert200(response)
        self.assertEqual(response.json["status"], "ok")
        self.assertNotEqual(response.json["playlist_mbid"], "")

        playlist_mbid = response.json["playlist_mbid"]

        # Test to ensure fetching a private playlist from a non-owner fails with 404
        response = self.client.get(
            self.custom_url_for("playlist_api_v1.get_playlist", playlist_mbid=playlist_mbid, fetch_metadata="false"),
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
            self.custom_url_for("playlist_api_v1.create_playlist"),
            json=playlist,
            headers={"Authorization": "Token {}".format(self.user["auth_token"])}
        )
        self.assert200(response)
        self.assertEqual(response.json["status"], "ok")
        self.assertNotEqual(response.json["playlist_mbid"], "")

        # Make sure the return playlist id is valid
        UUID(response.json["playlist_mbid"])

    def test_playlist_xspf_additional_metadata(self):
        """ Test for checking that additional meta data field is properly constructed and not causing a crash """

        playlist = {
            "playlist": {
                "title": "you're a person",
                "extension": {
                    PLAYLIST_EXTENSION_URI: {
                        "public": True,
                    }
                },
                "additional_metadata": {
                    "note": "a great playlist",
                    "details": {
                         "mood": "varied",
                         "genre": "eclectic",
                         "favorite_track": "Random Song"
                        }
                    }
                }
            }
        response_post = self.client.post(
            self.custom_url_for("playlist_api_v1.create_playlist"),
            json=playlist,
            headers={"Authorization": "Token {}".format(self.user["auth_token"])}
        )
        self.assert200(response_post)
        playlist_mbid = response_post.json["playlist_mbid"]
        r = self.client.get(
            self.custom_url_for("playlist_api_v1.get_playlist_xspf", playlist_mbid=playlist_mbid),
            headers={"Authorization": "Token {}".format(self.user["auth_token"])}
        )
        self.assert200(r)

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
            self.custom_url_for("playlist_api_v1.create_playlist"),
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
            self.custom_url_for("playlist_api_v1.create_playlist"),
            json=playlist,
            headers={"Authorization": "Token {}".format(self.user["auth_token"])}
        )
        self.assert400(response)
        self.assertEqual(
            response.json["error"], "JSPF playlist.extension.https://musicbrainz.org/doc/jspf#playlist.public field must be given.")

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
            self.custom_url_for("playlist_api_v1.create_playlist"),
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
            self.custom_url_for("playlist_api_v1.create_playlist"),
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
            self.custom_url_for("playlist_api_v1.create_playlist"),
            json=playlist,
            headers={"Authorization": "Token {}".format(self.user["auth_token"])}
        )
        self.assert400(response)
        self.assertEqual(
            response.json["error"],
            "JSPF playlist track 0 must contain a identifier field having a fully qualified URI to a"
            " recording_mbid. (e.g. https://musicbrainz.org/recording/8f3471b5-7e6a-48da-86a9-c1c07a0f47ae)"
        )

    def test_playlist_create_with_collaborators(self):
        """ Test to ensure creating a playlist with collaborators works """

        playlist = get_test_data()
        # If the owner is in collaborators, it should be filtered out
        # If a collaborator is listed multiple times, it should only be added once
        playlist["playlist"]["extension"][PLAYLIST_EXTENSION_URI]["collaborators"] = [self.user["musicbrainz_id"],
                                                                                      self.user2["musicbrainz_id"],
                                                                                      self.user2["musicbrainz_id"]]

        response = self.client.post(
            self.custom_url_for("playlist_api_v1.create_playlist"),
            json=playlist,
            headers={"Authorization": "Token {}".format(self.user["auth_token"])}
        )
        self.assert200(response)
        self.assertEqual(response.json["status"], "ok")
        self.assertNotEqual(response.json["playlist_mbid"], "")

        playlist_mbid = response.json["playlist_mbid"]

        response = self.client.get(
            self.custom_url_for("playlist_api_v1.get_playlist", playlist_mbid=playlist_mbid, fetch_metadata="false"),
        )
        self.assert200(response)
        self.assertEqual(response.json["playlist"]["extension"]
                         [PLAYLIST_EXTENSION_URI]["collaborators"], [self.user2["musicbrainz_id"]])

        # Check that this playlist shows up on the collaborators endpoint
        response = self.client.get(
            self.custom_url_for("api_v1.get_playlists_collaborated_on_for_user", playlist_user_name=self.user2["musicbrainz_id"]),
            headers={"Authorization": "Token {}".format(self.user4["auth_token"])},
        )
        self.assert200(response)
        self.assertEqual(response.json["playlist_count"], 1)
        self.assertEqual(response.json["playlists"][0]["playlist"]["extension"]
                         [PLAYLIST_EXTENSION_URI]["collaborators"], [self.user2["musicbrainz_id"]])

        # Check private too

    def test_playlist_edit(self):
        """ Test to ensure editing a playlist works """

        playlist = get_test_data()

        response = self.client.post(
            self.custom_url_for("playlist_api_v1.create_playlist"),
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
            self.custom_url_for("playlist_api_v1.edit_playlist", playlist_mbid=playlist_mbid),
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
            self.custom_url_for("playlist_api_v1.get_playlist", playlist_mbid=playlist_mbid, fetch_metadata="false"),
            headers={"Authorization": "Token {}".format(self.user["auth_token"])}
        )

        self.assertEqual(response.json["playlist"]["title"], "new title")
        self.assertEqual(response.json["playlist"]["annotation"], "new <b>desc</b> noscript")
        self.assertEqual(response.json["playlist"]["extension"]
                         [PLAYLIST_EXTENSION_URI]["public"], False)
        self.assertEqual(response.json["playlist"]["extension"]
                         [PLAYLIST_EXTENSION_URI]["collaborators"], [self.user2["musicbrainz_id"],
                                                                     self.user3["musicbrainz_id"]])

        # Edit again to remove description and collaborators
        response = self.client.post(
            self.custom_url_for("playlist_api_v1.edit_playlist", playlist_mbid=playlist_mbid),
            json={"playlist": {"annotation": "",
                               "extension": {PLAYLIST_EXTENSION_URI: {
                                   "collaborators": []}}}},
            headers={"Authorization": "Token {}".format(self.user["auth_token"])}
        )
        self.assert200(response)
        response = self.client.get(
            self.custom_url_for("playlist_api_v1.get_playlist", playlist_mbid=playlist_mbid, fetch_metadata="false"),
            headers={"Authorization": "Token {}".format(self.user["auth_token"])}
        )

        self.assertEqual(response.json["playlist"]["title"], "new title")
        self.assertNotIn("annotation", response.json["playlist"])
        self.assertEqual(response.json["playlist"]["extension"]
                         [PLAYLIST_EXTENSION_URI]["public"], False)
        self.assertNotIn("collaborators", response.json["playlist"]["extension"][PLAYLIST_EXTENSION_URI])

    def test_playlist_recording_add(self):
        """ Test adding a recording to a playlist works """

        playlist = get_test_data()

        response = self.client.post(
            self.custom_url_for("playlist_api_v1.create_playlist"),
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
                        "identifier": [PLAYLIST_TRACK_URI_PREFIX + "4a77a078-e91a-4522-a409-3b58aa7de3ae"]
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
            self.custom_url_for("playlist_api_v1.add_playlist_item", playlist_mbid=playlist_mbid),
            headers={"Authorization": "Token {}".format(self.user["auth_token"])},
            json=add_recording
        )
        self.assert200(response)

        response = self.client.get(
            self.custom_url_for("playlist_api_v1.get_playlist", playlist_mbid=playlist_mbid, fetch_metadata="false"),
            headers={"Authorization": "Token {}".format(self.user["auth_token"])}
        )
        self.assertEqual(response.json["playlist"]["creator"], "testuserpleaseignore")
        self.assertEqual(response.json["playlist"]["identifier"], PLAYLIST_URI_PREFIX + playlist_mbid)
        self.assertEqual(response.json["playlist"]["track"][0]["identifier"],
                         playlist["playlist"]["track"][0]["identifier"])
        self.assertEqual(response.json["playlist"]["track"][1]["identifier"],
                         add_recording["playlist"]["track"][0]["identifier"])

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
            self.custom_url_for("playlist_api_v1.add_playlist_item", playlist_mbid=playlist_mbid),
            headers={"Authorization": "Token {}".format(self.user["auth_token"])},
            json=add_recording
        )
        self.assert400(response)

    def test_playlist_recording_move(self):

        playlist = {
            "playlist": {
                "title": "1980s flashback jams",
                "track": [
                    {
                        "identifier": [PLAYLIST_TRACK_URI_PREFIX + "e8f9b188-f819-4e43-ab0f-4bd26ce9ff56"]
                    },
                    {
                        "identifier": [PLAYLIST_TRACK_URI_PREFIX + "57ef4803-5181-4b3d-8dd6-8b9d9ca83e2a"]
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
            self.custom_url_for("playlist_api_v1.create_playlist"),
            json=playlist,
            headers={"Authorization": "Token {}".format(self.user["auth_token"])}
        )
        self.assert200(response)
        playlist_mbid = response.json["playlist_mbid"]

        move = {"mbid": "57ef4803-5181-4b3d-8dd6-8b9d9ca83e2a", "from": 1, "to": 0, "count": 1}
        response = self.client.post(
            self.custom_url_for("playlist_api_v1.move_playlist_item", playlist_mbid=playlist_mbid),
            headers={"Authorization": "Token {}".format(self.user["auth_token"])},
            json=move
        )
        self.assert200(response)

        response = self.client.get(
            self.custom_url_for("playlist_api_v1.get_playlist", playlist_mbid=playlist_mbid, fetch_metadata="false"),
            headers={"Authorization": "Token {}".format(self.user["auth_token"])}
        )
        self.assertEqual(response.json["playlist"]["creator"], "testuserpleaseignore")
        self.assertEqual(response.json["playlist"]["identifier"], PLAYLIST_URI_PREFIX + playlist_mbid)
        self.assertEqual(response.json["playlist"]["track"][0]["identifier"],
                         playlist["playlist"]["track"][1]["identifier"])
        self.assertEqual(response.json["playlist"]["track"][1]["identifier"],
                         playlist["playlist"]["track"][0]["identifier"])

    def test_playlist_recording_delete(self):
        playlist = {
            "playlist": {
                "title": "1980s flashback jams",
                "track": [
                    {
                        "identifier": [PLAYLIST_TRACK_URI_PREFIX + "e8f9b188-f819-4e43-ab0f-4bd26ce9ff56"]
                    },
                    {
                        "identifier": [PLAYLIST_TRACK_URI_PREFIX + "57ef4803-5181-4b3d-8dd6-8b9d9ca83e2a"]
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
            self.custom_url_for("playlist_api_v1.create_playlist"),
            json=playlist,
            headers={"Authorization": "Token {}".format(self.user["auth_token"])}
        )
        self.assert200(response)
        playlist_mbid = response.json["playlist_mbid"]

        move = {"index": 0, "count": 1}
        response = self.client.post(
            self.custom_url_for("playlist_api_v1.delete_playlist_item", playlist_mbid=playlist_mbid),
            headers={"Authorization": "Token {}".format(self.user["auth_token"])},
            json=move
        )
        self.assert200(response)

        response = self.client.get(
            self.custom_url_for("playlist_api_v1.get_playlist", playlist_mbid=playlist_mbid, fetch_metadata="false"),
            headers={"Authorization": "Token {}".format(self.user["auth_token"])}
        )
        self.assertEqual(response.json["playlist"]["creator"], "testuserpleaseignore")
        self.assertEqual(response.json["playlist"]["identifier"], PLAYLIST_URI_PREFIX + playlist_mbid)
        self.assertEqual(response.json["playlist"]["track"][0]["identifier"],
                         playlist["playlist"]["track"][1]["identifier"])

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
            self.custom_url_for("playlist_api_v1.create_playlist"),
            json=playlist,
            headers={"Authorization": "Token {}".format(self.user["auth_token"])}
        )
        self.assert200(response)
        playlist_mbid = response.json["playlist_mbid"]

        response = self.client.post(
            self.custom_url_for("playlist_api_v1.delete_playlist", playlist_mbid=playlist_mbid),
            json={},
            headers={"Authorization": "Token {}".format(self.user["auth_token"])}
        )
        self.assert200(response)

        response = self.client.get(
            self.custom_url_for("playlist_api_v1.get_playlist", playlist_mbid=playlist_mbid, fetch_metadata="false"),
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
            self.custom_url_for("playlist_api_v1.create_playlist"),
            json=playlist,
            headers={"Authorization": "Token {}".format(self.user["auth_token"])}
        )
        self.assert200(response)
        playlist_mbid = response.json["playlist_mbid"]

        response = self.client.post(
            self.custom_url_for("playlist_api_v1.copy_playlist", playlist_mbid=playlist_mbid),
            json={},
            headers={"Authorization": "Token {}".format(self.user2["auth_token"])}
        )
        self.assert200(response)
        new_playlist_mbid = response.json["playlist_mbid"]
        self.assertNotEqual(playlist_mbid, new_playlist_mbid)

        response = self.client.get(
            self.custom_url_for("playlist_api_v1.get_playlist", playlist_mbid=new_playlist_mbid, fetch_metadata="false"),
            headers={"Authorization": "Token {}".format(self.user["auth_token"])}
        )
        self.assert200(response)
        self.assertEqual(response.json["playlist"]["identifier"], PLAYLIST_URI_PREFIX + new_playlist_mbid)
        self.assertEqual(response.json["playlist"]["extension"]
                         [PLAYLIST_EXTENSION_URI]["copied_from_mbid"],
                         PLAYLIST_URI_PREFIX + playlist_mbid)
        self.assertEqual(response.json["playlist"]["extension"]
                         [PLAYLIST_EXTENSION_URI]["public"], True)
        self.assertEqual(response.json["playlist"]["title"], "Copy of my stupid playlist")
        self.assertEqual(response.json["playlist"]["creator"], "anothertestuserpleaseignore")
        # Ensure original playlist's collaborators have been scrubbed
        # The serialized JSPF playlist leaves out the "collaborators" key if there are none
        self.assertNotIn("collaborators", response.json["playlist"]["extension"][PLAYLIST_EXTENSION_URI])

        # Now delete the original playlist so that we can test copied from deleted playlist
        response = self.client.post(
            self.custom_url_for("playlist_api_v1.delete_playlist", playlist_mbid=playlist_mbid),
            json={},
            headers={"Authorization": "Token {}".format(self.user["auth_token"])}
        )
        self.assert200(response)

        response = self.client.get(
            self.custom_url_for("playlist_api_v1.get_playlist", playlist_mbid=new_playlist_mbid, fetch_metadata="false"),
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
            self.custom_url_for("playlist_api_v1.create_playlist"),
            json=playlist,
            headers={"Authorization": "Token {}".format(self.user["auth_token"])}
        )
        self.assert200(response)
        playlist_mbid = response.json["playlist_mbid"]

        response = self.client.post(
            self.custom_url_for("playlist_api_v1.copy_playlist", playlist_mbid=playlist_mbid),
            json={},
            headers={"Authorization": "Token {}".format(self.user["auth_token"])}
        )
        self.assert200(response)
        new_playlist_mbid = response.json["playlist_mbid"]
        self.assertNotEqual(playlist_mbid, new_playlist_mbid)

        response = self.client.get(
            self.custom_url_for("playlist_api_v1.get_playlist", playlist_mbid=new_playlist_mbid, fetch_metadata="false"),
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
            self.custom_url_for("playlist_api_v1.create_playlist"),
            json=playlist,
            headers={"Authorization": "Token {}".format(self.user["auth_token"])}
        )
        self.assert200(response)
        playlist_mbid = response.json["playlist_mbid"]

        response = self.client.get(
            self.custom_url_for("playlist_api_v1.get_playlist", playlist_mbid=playlist_mbid, fetch_metadata="false"),
            headers={"Authorization": "Token {}".format(self.user2["auth_token"])},
        )
        self.assert404(response)

        # Add recording to playlist
        response = self.client.post(
            self.custom_url_for("playlist_api_v1.add_playlist_item", offset=0, playlist_mbid=playlist_mbid),
            json={},
            headers={"Authorization": "Token {}".format(self.user2["auth_token"])}
        )
        self.assert404(response)

        # Move recording in playlist
        response = self.client.post(
            self.custom_url_for("playlist_api_v1.move_playlist_item", playlist_mbid=playlist_mbid),
            json={},
            headers={"Authorization": "Token {}".format(self.user2["auth_token"])}
        )
        self.assert404(response)

        # Delete recording in playlist
        response = self.client.post(
            self.custom_url_for("playlist_api_v1.delete_playlist_item", playlist_mbid=playlist_mbid),
            json={},
            headers={"Authorization": "Token {}".format(self.user2["auth_token"])}
        )
        self.assert404(response)

        # Delete a playlist
        response = self.client.post(
            self.custom_url_for("playlist_api_v1.delete_playlist", playlist_mbid=playlist_mbid),
            json={},
            headers={"Authorization": "Token {}".format(self.user2["auth_token"])}
        )
        self.assert404(response)

        # Copy a playlist
        response = self.client.post(
            self.custom_url_for("playlist_api_v1.copy_playlist", playlist_mbid=playlist_mbid),
            json={},
            headers={"Authorization": "Token {}".format(self.user2["auth_token"])}
        )
        self.assert404(response)

    def test_private_playlist_collaborators_access(self):
        """ Test to ensure playlist collaborators can view, copy and add/move/delete tracks """

        # create a private playlist with a collaborator,
        # then try to access it as the collaborator user for all the endpoints
        playlist = get_test_data()
        playlist["playlist"]["extension"][PLAYLIST_EXTENSION_URI]["public"] = False
        playlist["playlist"]["extension"][PLAYLIST_EXTENSION_URI]["collaborators"] = [self.user2["musicbrainz_id"]]
        response = self.client.post(
            self.custom_url_for("playlist_api_v1.create_playlist"),
            json=playlist,
            headers={"Authorization": "Token {}".format(self.user["auth_token"])}
        )
        self.assert200(response)
        playlist_mbid = response.json["playlist_mbid"]

        # Get playlist
        response = self.client.get(
            self.custom_url_for("playlist_api_v1.get_playlist", playlist_mbid=playlist_mbid, fetch_metadata="false"),
            headers={"Authorization": "Token {}".format(self.user2["auth_token"])},
        )
        self.assert200(response)

        # Add recording to playlist
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
            self.custom_url_for("playlist_api_v1.add_playlist_item", playlist_mbid=playlist_mbid),
            headers={"Authorization": "Token {}".format(self.user2["auth_token"])},
            json=add_recording
        )
        self.assert200(response)

        # Move recording in playlist
        move = {"mbid": "57ef4803-5181-4b3d-8dd6-8b9d9ca83e2a", "from": 1, "to": 0, "count": 1}
        response = self.client.post(
            self.custom_url_for("playlist_api_v1.move_playlist_item", playlist_mbid=playlist_mbid),
            headers={"Authorization": "Token {}".format(self.user2["auth_token"])},
            json=move
        )
        self.assert200(response)

        # Delete recording in playlist
        delete = {"index": 0, "count": 1}
        response = self.client.post(
            self.custom_url_for("playlist_api_v1.delete_playlist_item", playlist_mbid=playlist_mbid),
            json=delete,
            headers={"Authorization": "Token {}".format(self.user2["auth_token"])}
        )
        self.assert200(response)

        # Copy a playlist
        response = self.client.post(
            self.custom_url_for("playlist_api_v1.copy_playlist", playlist_mbid=playlist_mbid),
            json={},
            headers={"Authorization": "Token {}".format(self.user2["auth_token"])}
        )
        self.assert200(response)
        new_playlist_mbid = response.json["playlist_mbid"]
        self.assertNotEqual(playlist_mbid, new_playlist_mbid)

        # Collaborators are not authorized to edit or delete the playlist
        # Delete a playlist
        response = self.client.post(
            self.custom_url_for("playlist_api_v1.delete_playlist", playlist_mbid=playlist_mbid),
            json={},
            headers={"Authorization": "Token {}".format(self.user2["auth_token"])}
        )
        self.assert403(response)

        # Edit a playlist
        response = self.client.post(
            self.custom_url_for("playlist_api_v1.edit_playlist", playlist_mbid=playlist_mbid),
            json=playlist,
            headers={"Authorization": "Token {}".format(self.user2["auth_token"])}
        )
        self.assert403(response)

    def test_playlist_get_playlists(self):
        """ Test for checking that unauthorized access to private playlists return 404 """

        # create a public and private playlist, then try various forms of access
        playlist = get_test_data()
        playlist["playlist"]["extension"][PLAYLIST_EXTENSION_URI]["public"] = False
        response = self.client.post(
            self.custom_url_for("playlist_api_v1.create_playlist"),
            json=playlist,
            headers={"Authorization": "Token {}".format(self.user4["auth_token"])}
        )
        self.assert200(response)
        private_playlist_mbid = response.json["playlist_mbid"]

        playlist = get_test_data()
        response = self.client.post(
            self.custom_url_for("playlist_api_v1.create_playlist"),
            json=playlist,
            headers={"Authorization": "Token {}".format(self.user4["auth_token"])}
        )
        self.assert200(response)
        public_playlist_mbid = response.json["playlist_mbid"]

        response = self.client.get(
            self.custom_url_for("api_v1.get_playlists_for_user", playlist_user_name=self.user4["musicbrainz_id"]),
            headers={"Authorization": "Token {}".format(self.user["auth_token"])},
        )
        self.assert200(response)
        self.assertEqual(response.json["playlist_count"], 1)

        response = self.client.get(
            self.custom_url_for("api_v1.get_playlists_for_user", playlist_user_name=self.user4["musicbrainz_id"]),
            headers={"Authorization": "Token {}".format(self.user4["auth_token"])},
        )
        self.assert200(response)
        self.assertEqual(response.json["playlist_count"], 2)
        self.assertEqual(response.json["count"], DEFAULT_NUMBER_OF_PLAYLISTS_PER_CALL)
        self.assertEqual(response.json["offset"], 0)
        self.assertEqual(response.json["playlists"][0]["playlist"]["extension"]
                         [PLAYLIST_EXTENSION_URI]["creator"], self.user4["musicbrainz_id"])
        self.assertEqual(response.json["playlists"][0]["playlist"]["identifier"], PLAYLIST_URI_PREFIX + public_playlist_mbid)
        self.assertEqual(response.json["playlists"][0]["playlist"]["title"], "1980s flashback jams")
        self.assertEqual(response.json["playlists"][0]["playlist"]["annotation"], "your lame <i>80s</i> music")
        self.assertEqual(response.json["playlists"][0]["playlist"]["extension"]
                         [PLAYLIST_EXTENSION_URI]["public"], True)
        try:
            dateutil.parser.isoparse(response.json["playlists"][0]["playlist"]["date"])
        except ValueError:
            assert False
        self.assertEqual(response.json["playlists"][1]["playlist"]["extension"]
                         [PLAYLIST_EXTENSION_URI]["creator"], self.user4["musicbrainz_id"])
        self.assertEqual(response.json["playlists"][1]["playlist"]["identifier"], PLAYLIST_URI_PREFIX + private_playlist_mbid)
        self.assertEqual(response.json["playlists"][1]["playlist"]["title"], "1980s flashback jams")
        self.assertEqual(response.json["playlists"][1]["playlist"]["annotation"], "your lame <i>80s</i> music")
        self.assertEqual(response.json["playlists"][1]["playlist"]["extension"]
                         [PLAYLIST_EXTENSION_URI]["public"], False)
        try:
            dateutil.parser.isoparse(response.json["playlists"][1]["playlist"]["date"])
        except ValueError:
            assert False

        # Test count and offset parameters
        response = self.client.get(
            self.custom_url_for("api_v1.get_playlists_for_user", playlist_user_name=self.user4["musicbrainz_id"], count=1),
            headers={"Authorization": "Token {}".format(self.user4["auth_token"])},
        )
        self.assert200(response)
        self.assertEqual(len(response.json["playlists"]), 1)
        self.assertEqual(response.json["playlist_count"], 2)
        self.assertEqual(response.json["count"], 1)
        self.assertEqual(response.json["offset"], 0)

        response = self.client.get(
            self.custom_url_for("api_v1.get_playlists_for_user", playlist_user_name=self.user4["musicbrainz_id"], offset=1, count=1),
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
            self.custom_url_for("playlist_api_v1.create_playlist"),
            json={}
        )
        self.assert401(response)

        playlist_mbid = "d1ff6a3d-f471-416f-94e7-86778b51fa2b"
        # Add recording to playlist
        response = self.client.post(
            self.custom_url_for("playlist_api_v1.add_playlist_item", offset=0, playlist_mbid=playlist_mbid),
            json={}
        )
        self.assert401(response)

        # Move recording in playlist
        response = self.client.post(
            self.custom_url_for("playlist_api_v1.move_playlist_item", playlist_mbid=playlist_mbid),
            json={}
        )
        self.assert401(response)

        # Delete recording in playlist
        response = self.client.post(
            self.custom_url_for("playlist_api_v1.delete_playlist_item", playlist_mbid=playlist_mbid),
            json={}
        )
        self.assert401(response)

        # Delete a playlist
        response = self.client.post(
            self.custom_url_for("playlist_api_v1.delete_playlist", playlist_mbid=playlist_mbid),
            json={}
        )
        self.assert401(response)

        # Copy a playlist
        response = self.client.post(
            self.custom_url_for("playlist_api_v1.copy_playlist", playlist_mbid=playlist_mbid),
            json={}
        )
        self.assert401(response)

        # Edit a playlist
        response = self.client.post(
            self.custom_url_for("playlist_api_v1.edit_playlist", playlist_mbid=playlist_mbid),
            json={}
        )
        self.assert401(response)

        response = self.client.post(
            self.custom_url_for("playlist_api_v1.export_playlist", playlist_mbid=playlist_mbid, service="spotify"),
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
            self.custom_url_for("playlist_api_v1.create_playlist"),
            json=playlist,
            headers={"Authorization": "Token {}".format(self.user["auth_token"])}
        )
        self.assert200(response)
        playlist_mbid = response.json["playlist_mbid"]

        # Add recording to playlist
        response = self.client.post(
            self.custom_url_for("playlist_api_v1.add_playlist_item", offset=0, playlist_mbid=playlist_mbid),
            json={},
            headers={"Authorization": "Token {}".format(self.user2["auth_token"])}
        )
        self.assert403(response)

        # Move recording in playlist
        response = self.client.post(
            self.custom_url_for("playlist_api_v1.move_playlist_item", playlist_mbid=playlist_mbid),
            json={},
            headers={"Authorization": "Token {}".format(self.user2["auth_token"])}
        )
        self.assert403(response)

        # Delete recording in playlist
        response = self.client.post(
            self.custom_url_for("playlist_api_v1.delete_playlist_item", playlist_mbid=playlist_mbid),
            json={},
            headers={"Authorization": "Token {}".format(self.user2["auth_token"])}
        )
        self.assert403(response)

        # Delete a playlist
        response = self.client.post(
            self.custom_url_for("playlist_api_v1.delete_playlist", playlist_mbid=playlist_mbid),
            json={},
            headers={"Authorization": "Token {}".format(self.user2["auth_token"])}
        )
        self.assert403(response)

        # edit a playlist
        response = self.client.post(
            self.custom_url_for("playlist_api_v1.edit_playlist", playlist_mbid=playlist_mbid),
            json=playlist,
            headers={"Authorization": "Token {}".format(self.user2["auth_token"])}
        )
        self.assert403(response)

    @requests_mock.Mocker()
    @mock.patch("listenbrainz.webserver.views.playlist_api.export_to_spotify")
    @mock.patch("listenbrainz.webserver.views.playlist_api.export_to_apple_music")
    def test_playlist_export(self, mock_requests, mock_export_to_apple_music, mock_export_to_spotify):
        """ Test various error cases related to exporting a playlist to spotify and apple music """
        mock_export_to_spotify.return_value = "spotify_url"
        mock_export_to_apple_music.return_value = "apple_music_url"

        mock_requests.post(OAUTH_TOKEN_URL, status_code=200, json={
            'access_token': 'tokentoken',
            'expires_in': 3600,
            'scope': '',
        })

        playlist = {
            "playlist": {
                "title": "my updated playlist",
                "extension": {
                    PLAYLIST_EXTENSION_URI: {
                        "public": True
                    }
                },
            }
        }

        response = self.client.post(
            self.custom_url_for("playlist_api_v1.create_playlist"),
            json=playlist,
            headers={"Authorization": "Token {}".format(self.user["auth_token"])}
        )
        self.assert200(response)
        playlist_mbid = response.json["playlist_mbid"]

        response = self.client.post(
            self.custom_url_for("playlist_api_v1.export_playlist", playlist_mbid=playlist_mbid, service="lastfm"),
            json=playlist,
            headers={"Authorization": "Token {}".format(self.user["auth_token"])}
        )
        self.assert400(response)
        self.assertEqual(response.json["error"], "Service lastfm is not supported. We currently only support 'spotify' and 'apple_music'.")

        response = self.client.post(
            self.custom_url_for("playlist_api_v1.export_playlist", playlist_mbid=playlist_mbid, service="spotify"),
            json=playlist,
            headers={"Authorization": "Token {}".format(self.user["auth_token"])}
        )
        self.assert400(response)
        self.assertEqual(response.json["error"], "Service spotify is not linked. Please link your spotify account first.")

        db_oauth.save_token(
            self.db_conn,
            user_id=self.user['id'],
            service=ExternalServiceType.SPOTIFY,
            access_token='token',
            refresh_token='refresh_token',
            token_expires_ts=int(time.time()),
            record_listens=True,
            scopes=['user-read-recently-played']
        )

        response = self.client.post(
            self.custom_url_for("playlist_api_v1.export_playlist", playlist_mbid=playlist_mbid, service="spotify"),
            json=playlist,
            headers={"Authorization": "Token {}".format(self.user["auth_token"])}
        )
        self.assert400(response)
        self.assertEqual(
            response.json["error"],
            "Missing scopes playlist-modify-public and playlist-modify-private to export playlists."
            " Please relink your spotify account from ListenBrainz settings with appropriate scopes"
            " to use this feature."
        )

        db_oauth.delete_token(self.db_conn, self.user['id'], ExternalServiceType.SPOTIFY, True)

        db_oauth.save_token(
            self.db_conn,
            user_id=self.user['id'],
            service=ExternalServiceType.SPOTIFY,
            access_token='token',
            refresh_token='refresh_token',
            token_expires_ts=int(time.time()),
            record_listens=True,
            scopes=[
                'streaming',
                'user-read-email',
                'user-read-private',
                'playlist-modify-public',
                'playlist-modify-private',
                'user-read-currently-playing',
                'user-read-recently-played'
            ]
        )
        mock_export_to_spotify.assert_not_called()

        response = self.client.post(
            self.custom_url_for("playlist_api_v1.export_playlist", playlist_mbid=playlist_mbid, service="spotify"),
            json=playlist,
            headers={"Authorization": "Token {}".format(self.user["auth_token"])}
        )
        self.assert200(response)
        self.assertEqual(response.json, {"external_url": "spotify_url"})

        response = self.client.post(
            self.custom_url_for("playlist_api_v1.export_playlist", playlist_mbid=playlist_mbid, service="apple_music"),
            json=playlist,
            headers={"Authorization": "Token {}".format(self.user["auth_token"])}
        )
        self.assert400(response)
        self.assertEqual(response.json["error"], "Service apple_music is not linked. Please link your apple_music account first.")

        db_oauth.save_token(
            self.db_conn,
            user_id=self.user['id'],
            service=ExternalServiceType.APPLE,
            access_token='token',
            refresh_token='refresh_token',
            token_expires_ts=int(time.time()),
            record_listens=True,
            scopes=[]
        )
        mock_export_to_apple_music.assert_not_called()

        response = self.client.post(
            self.custom_url_for("playlist_api_v1.export_playlist", playlist_mbid=playlist_mbid, service="apple_music"),
            json=playlist,
            headers={"Authorization": "Token {}".format(self.user["auth_token"])}
        )
        self.assert200(response)
        self.assertEqual(response.json, {"external_url": "apple_music_url"})
