import json
import logging
import time
from datetime import datetime, timezone
from unittest import mock
from urllib.parse import quote_plus
import orjson
from brainzutils import cache
from sqlalchemy import text

import listenbrainz.db.user as db_user
from data.model.external_service import ExternalServiceType
from listenbrainz.db import external_service_oauth as db_oauth, timescale
from listenbrainz.listenstore.tests.util import create_test_data_for_timescalelistenstore
from listenbrainz.listenstore.timescale_listenstore import EPOCH
from listenbrainz.tests.integration import IntegrationTestCase
from listenbrainz.webserver import timescale_connection
from listenbrainz.webserver.login import User


class UserViewsTestCase(IntegrationTestCase):
    def setUp(self):
        super(UserViewsTestCase, self).setUp()

        self.log = logging.getLogger(__name__)
        self.logstore = timescale_connection._ts

        user = db_user.get_or_create(self.db_conn, 1, 'iliekcomputers')
        db_user.agree_to_gdpr(self.db_conn, user['musicbrainz_id'])

        # fetch again so that gdpr agreed time is set
        user = db_user.get(self.db_conn, user['id'])
        self.user = User.from_dbrow(user)

        weirduser = db_user.get_or_create(
            self.db_conn, 2, '</weird?\\user_name>')
        self.weirduser = User.from_dbrow(weirduser)

        abuser = db_user.get_or_create(self.db_conn, 3, 'abuser')
        self.abuser = User.from_dbrow(abuser)
        self.ts_conn = timescale.engine.connect()

    def tearDown(self):
        self.ts_conn.close()
        self.logstore = None
        super().tearDown()

    def test_redirects_logged_out(self):
        my_listens_url = self.custom_url_for("redirect.index", path="")
        # Not logged in
        response = self.client.get(my_listens_url)
        self.assertRedirects(response, self.custom_url_for("login.index", next=my_listens_url))

    def test_user_redirects(self):
        response = self.client.get('/user/iliekcomputers/')
        self.assert200(response)
        response = self.client.get('/user/iliekcomputers')
        self.assertRedirects(response, '/user/iliekcomputers/', permanent=True)

        response = self.client.get('/user/iliekcomputers/charts/')
        self.assert200(response)
        response = self.client.get('/user/iliekcomputers/charts')
        self.assertRedirects(response, '/user/iliekcomputers/charts/', permanent=True)

        response = self.client.get('/user/iliekcomputers/stats/')
        self.assert200(response)
        response = self.client.get('/user/iliekcomputers/stats')
        self.assertRedirects(response, '/user/iliekcomputers/stats/', permanent=True)

    def test_user_page(self):
        response = self.client.get(self.custom_url_for('user.index', path="", user_name=self.user.musicbrainz_id))
        self.assert200(response)

    def test_spotify_token_access_no_login(self):
        db_oauth.save_token(self.db_conn, user_id=self.user.id, service=ExternalServiceType.SPOTIFY,
                            access_token='token', refresh_token='refresh',
                            token_expires_ts=int(time.time()) + 1000, record_listens=True,
                            scopes=['user-read-recently-played', 'streaming'])

        response = self.client.get(self.custom_url_for('user.index', path="", user_name=self.user.musicbrainz_id))
        self.assert200(response)
        self.assertTemplateUsed('index.html')
        props = orjson.loads(self.get_context_variable("global_props"))
        self.assertDictEqual(props['spotify'], {})

    def test_spotify_token_access_unlinked(self):
        self.temporary_login(self.user.login_id)
        response = self.client.get(self.custom_url_for('user.index', path="", user_name=self.user.musicbrainz_id))
        self.assert200(response)
        props = orjson.loads(self.get_context_variable("global_props"))
        self.assertDictEqual(props['spotify'], {})

    def test_spotify_token_access(self):
        db_oauth.save_token(self.db_conn, user_id=self.user.id, service=ExternalServiceType.SPOTIFY,
                            access_token='token', refresh_token='refresh',
                            token_expires_ts=int(time.time()) + 1000, record_listens=True,
                            scopes=['user-read-recently-played', 'streaming'])

        self.temporary_login(self.user.login_id)

        response = self.client.get(self.custom_url_for('user.index', path="", user_name=self.user.musicbrainz_id))
        self.assert200(response)

        props = orjson.loads(self.get_context_variable("global_props"))
        self.assertDictEqual(props['spotify'], {
            'access_token': 'token',
            'permission': ['user-read-recently-played', 'streaming'],
        })

        response = self.client.get(self.custom_url_for('user.index', path="", user_name=self.weirduser.musicbrainz_id))
        self.assert200(response)
        props = orjson.loads(self.get_context_variable("global_props"))
        self.assertDictEqual(props['spotify'], {
            'access_token': 'token',
            'permission': ['user-read-recently-played', 'streaming'],
        })

    @mock.patch('listenbrainz.webserver.views.user.db_user_relationship.is_following_user')
    def test_logged_in_user_follows_user_props(self, mock_is_following_user):
        response = self.client.get(self.custom_url_for('user.index', path="", user_name=self.user.musicbrainz_id))
        self.assert200(response)
        self.assertTemplateUsed('index.html')

        self.temporary_login(self.user.login_id)
        mock_is_following_user.return_value = False
        response = self.client.get(self.custom_url_for('user.index', path="", user_name=self.user.musicbrainz_id))
        self.assert200(response)

    def _create_test_data(self, user_name):
        min_ts = -1
        max_ts = -1
        self.test_data = create_test_data_for_timescalelistenstore(user_name, 1)
        for listen in self.test_data:
            if min_ts < 0 or listen.ts_since_epoch < min_ts:
                min_ts = listen.ts_since_epoch
            if max_ts < 0 or listen.ts_since_epoch > max_ts:
                max_ts = listen.ts_since_epoch

        self.logstore.insert(self.test_data)
        return min_ts, max_ts

    def test_username_case(self):
        """Tests that the username in URL is case insensitive"""
        self._create_test_data('iliekcomputers')

        response1 = self.client.get(self.custom_url_for('user.index', path="", user_name='iliekcomputers'))
        self.assertContext('user', self.user)
        response2 = self.client.get(self.custom_url_for('user.index', path="", user_name='IlieKcomPUteRs'))
        self.assertContext('user', self.user)
        self.assert200(response1)
        self.assert200(response2)
    
    def test_weird_usernames(self):
        """Tests that the username parsing allows the full range of MusicBrainz usernames
        This includes encoded slashes (%2F), question marks (%3F)"""
        encoded_username = quote_plus(
            self.weirduser.musicbrainz_id)
        # First test get request
        response = self.client.get(self.custom_url_for('user.index', path="", user_name=self.weirduser.musicbrainz_id))
        self.assert200(response)
        self.assertContext('user', self.weirduser)
        # Now the same with encoded username
        response = self.client.get(f"/user/{encoded_username}/")
        self.assert200(response)
        self.assertContext('user', self.weirduser)
        # Then test post request to get user data
        response = self.client.post(f"/user/{encoded_username}/")
        self.assert200(response)
        parsed_response = orjson.loads(response.data)
        # Check username is equal to unencoded name
        self.assertDictEqual(parsed_response['user'], {
                             'id': self.weirduser.id, 'name': self.weirduser.musicbrainz_id})

    @mock.patch('listenbrainz.webserver.timescale_connection._ts.fetch_listens')
    def test_ts_filters(self, timescale):
        """Check that max_ts and min_ts are passed to timescale """
        user = self.user.to_dict()
        timescale.return_value = ([], EPOCH, EPOCH)

        self.client.post(self.custom_url_for('user.profile', user_name='iliekcomputers'))
        req_call = mock.call(user, None, None, 25)
        timescale.assert_has_calls([req_call])
        timescale.reset_mock()

        # max_ts query param -> to_ts timescale param
        self.client.post(self.custom_url_for('user.profile', user_name='iliekcomputers'),
                        query_string={'max_ts': 1520946000})
        req_call = mock.call(user, None, datetime.fromtimestamp(1520946000, timezone.utc), 25)
        timescale.assert_has_calls([req_call])
        timescale.reset_mock()

        # min_ts query param -> from_ts timescale param
        self.client.post(self.custom_url_for('user.profile', user_name='iliekcomputers'),
                        query_string={'min_ts': 1520941000})
        req_call = mock.call(user, datetime.fromtimestamp(1520941000, timezone.utc), None, 25)
        timescale.assert_has_calls([req_call])
        timescale.reset_mock()

        # clear listens cache
        cache._r.flushdb()
        # If max_ts and min_ts set, only max_ts is used
        self.client.post(self.custom_url_for('user.profile', user_name='iliekcomputers'),
                        query_string={'min_ts': 1520941000, 'max_ts': 1520946000})
        req_call = mock.call(user, None, datetime.fromtimestamp(1520946000, timezone.utc), 25)
        timescale.assert_has_calls([req_call])

    @mock.patch('listenbrainz.webserver.timescale_connection._ts.fetch_listens')
    def test_ts_filters_errors(self, timescale):
        """If max_ts and min_ts are not integers, show an error page"""
        (min_ts, max_ts) = self._create_test_data('iliekcomputers')

        response = self.client.post(self.custom_url_for('user.profile', user_name='iliekcomputers'),
                                   query_string={'max_ts': 'a'})
        self.assert400(response)
        self.assertIn("Incorrect max_ts timestamp argument: a", response.json["error"])

        response = self.client.post(self.custom_url_for('user.profile', user_name='iliekcomputers'),
                                   query_string={'min_ts': 'b'})
        self.assert400(response)
        self.assertIn("Incorrect min_ts timestamp argument: b", response.json["error"])

        timescale.assert_not_called()

    def test_report_abuse(self):
        # Assert user is not already reported by current user
        already_reported_user = db_user.is_user_reported(self.db_conn, self.user.id, self.abuser.id)
        self.assertFalse(already_reported_user)

        self.temporary_login(self.user.login_id)
        # Assert reporting works
        data = {
            'reason': 'This user is cramping my style and I dont like it'
        }
        response = self.client.post(
            self.custom_url_for('user.report_abuse', user_name=self.abuser.musicbrainz_id),
            json=data,
        )
        self.assert200(response, "%s has been reported successfully." % self.abuser.musicbrainz_id)
        already_reported_user = db_user.is_user_reported(self.db_conn, self.user.id, self.abuser.id)
        self.assertTrue(already_reported_user)

        # Assert a user cannot report themselves
        response = self.client.post(
            self.custom_url_for('user.report_abuse', user_name=self.user.musicbrainz_id),
            json=data,
        )
        self.assert400(response, "You cannot report yourself.")
        already_reported_user = db_user.is_user_reported(self.db_conn, self.user.id, self.user.id)
        self.assertFalse(already_reported_user)

        # Assert reason must be of type string
        data = {
            'reason': {'youDoneGoofed': 1234}
        }
        response = self.client.post(
            self.custom_url_for('user.report_abuse', user_name=self.abuser.musicbrainz_id),
            json=data,
        )
        self.assert400(response, "Reason must be a string.")

    def test_user_pins(self):
        self.ts_conn.execute(text("""
            INSERT INTO mapping.mb_metadata_cache
                               (recording_mbid, recording_id, artist_mbids, artist_ids, release_mbid, release_id, recording_data, artist_data, tag_data, release_data, dirty)
                VALUES ('1fe669c9-5a2b-4dcb-9e95-77480d1e732e'
                      , 1
                      , '{5b24fbab-c58f-4c37-a59d-ab232e2d98c4}'::UUID[]
                      , '{1}'::INTEGER[]
                      , '607cc05a-e462-4f39-91b5-e9322544e0a6'
                      , 1
                      , '{"name": "The Final Confrontation, Part 1", "rels": [], "length": 312000}'
                      , '{"name": "Danny Elfman", "artist_credit_id": 204, "artists": [{"area": "United States", "rels": {"youtube": "https://www.youtube.com/channel/UCjhIy2xUURhJvN0S7s_ztuw", "wikidata": "https://www.wikidata.org/wiki/Q193338", "streaming": "https://music.apple.com/gb/artist/486493", "free streaming": "https://www.deezer.com/artist/760", "social network": "https://www.instagram.com/dannyelfman/", "official homepage": "https://www.dannyelfman.com/", "purchase for download": "https://itunes.apple.com/us/artist/id486493"}, "type": "Person", "gender": "Male", "begin_year": 1953, "name": "Danny Elfman", "join_phrase": ""}]}'
                      , '{"artist": [], "recording": [], "release_group": []}'
                      , '{"mbid": "607cc05a-e462-4f39-91b5-e9322544e0a6", "name": "Danny Elfman & Tim Burton 25th Anniversary Music Box", "year": 2011}'
                      , 'f'
                       );

            INSERT INTO mbid_mapping (recording_msid, recording_mbid, match_type)
             VALUES (
                'b7ffd2af-418f-4be2-bdd1-22f8b48613da'
              , '1fe669c9-5a2b-4dcb-9e95-77480d1e732e'
              , 'exact_match'
            );
        """))
        self.ts_conn.commit()

        pinned_rec = {
            "recording_msid": "b7ffd2af-418f-4be2-bdd1-22f8b48613da",
            "recording_mbid": "1fe669c9-5a2b-4dcb-9e95-77480d1e732e",
            "blurb_content": "Amazing first recording"
        }
        response = self.client.post(
            self.custom_url_for("pinned_rec_api_bp_v1.pin_recording_for_user"),
            data=json.dumps(pinned_rec),
            headers={"Authorization": f"Token {self.user.auth_token}"},
            content_type="application/json",
        )
        self.assert200(response)
        submitted_pin = response.json["pinned_recording"]
        submitted_pin["track_metadata"] = {
            "track_name": "The Final Confrontation, Part 1",
            "artist_name": "Danny Elfman",
            "release_name": "Danny Elfman & Tim Burton 25th Anniversary Music Box",
            "additional_info": {
                "recording_msid": "b7ffd2af-418f-4be2-bdd1-22f8b48613da"
            },
            "mbid_mapping": {
                "recording_mbid": "1fe669c9-5a2b-4dcb-9e95-77480d1e732e",
                "release_mbid": "607cc05a-e462-4f39-91b5-e9322544e0a6",
                "artist_mbids": ["5b24fbab-c58f-4c37-a59d-ab232e2d98c4"],
                "artists": [
                    {
                        "artist_credit_name": "Danny Elfman",
                        "join_phrase": "",
                        "artist_mbid": "5b24fbab-c58f-4c37-a59d-ab232e2d98c4"
                    }
                ]
            }
        }

        response = self.client.post(self.custom_url_for('user.taste', user_name=self.user.musicbrainz_id))
        self.assert200(response)

        json_response = response.json
        self.assertEqual(json_response["pins"], [submitted_pin])
