""" This module tests AudioScrobbler v1.2 compatibility features """

# listenbrainz-server - Server for the ListenBrainz project.
#
# Copyright (C) 2017 Param Singh <paramsingh258@gmail.com>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along
# with this program; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA


import logging
import time
from datetime import datetime, timezone

from werkzeug.exceptions import BadRequest

import listenbrainz.db.user as db_user
from listenbrainz.db.lastfm_session import Session
from listenbrainz.listenstore.timescale_utils import recalculate_all_user_data
from listenbrainz.tests.integration import APICompatIntegrationTestCase
from listenbrainz.webserver import timescale_connection
from listenbrainz.webserver.views.api_compat_deprecated import _get_audioscrobbler_auth_token, _get_session, \
    _to_native_api


class APICompatDeprecatedTestCase(APICompatIntegrationTestCase):

    def setUp(self):
        super(APICompatDeprecatedTestCase, self).setUp()
        self.user = db_user.get_or_create(self.db_conn, 1, 'apicompatoldtestuser')

        self.log = logging.getLogger(__name__)
        self.ls = timescale_connection._ts

    def handshake(self, user_name, auth_token, timestamp):
        """ Makes a request to the handshake endpoint of the AudioScrobbler API and
            returns the response.
        """

        args = {
            'hs': 'true',
            'p': '1.2',
            'c': 'tst',
            'v': '0.1',
            'u': user_name,
            't': timestamp,
            'a': auth_token
        }

        return self.client.get('/', query_string=args)

    def test_handshake(self):
        """ Tests handshake for a user that exists """
        timestamp = int(time.time())
        audioscrobbler_auth_token = _get_audioscrobbler_auth_token(self.user['auth_token'], timestamp)

        r = self.handshake(self.user['musicbrainz_id'], audioscrobbler_auth_token, timestamp)

        self.assert200(r)
        response = r.data.decode('utf-8').split('\n')
        self.assertEqual(len(response), 5)
        self.assertEqual(response[0], 'OK')
        self.assertEqual(len(response[1]), 32)

    def test_handshake_post(self):
        """ Tests POST requests to handshake endpoint """
        ts = int(time.time())
        args = {
            'hs': 'true',
            'p': '1.2',
            'c': 'tst',
            'v': '0.1',
            'u': self.user['musicbrainz_id'],
            't': ts,
            'a': _get_audioscrobbler_auth_token(self.user['auth_token'], ts)
        }

        r = self.client.post('/', query_string=args)

        self.assert200(r)
        response = r.data.decode('utf-8').split('\n')
        self.assertEqual(len(response), 5)
        self.assertEqual(response[0], 'OK')
        self.assertEqual(len(response[1]), 32)

    def test_root_url_when_no_handshake(self):
        """ Tests the root url when there's no handshaking taking place """
        r = self.client.get('/')
        self.assertStatus(r, 302)

    def test_handshake_unknown_user(self):
        """ Tests handshake for user that is not in the db """

        r = self.handshake('', '', '')
        self.assert401(r)

    def test_handshake_invalid_auth(self):
        """ Tests handshake when invalid authorization token is sent """

        r = self.handshake(self.user['musicbrainz_id'], '', int(time.time()))
        self.assert401(r)

    def test_submit_listen(self):
        """ Sends a valid listen after handshaking and checks if it is present in the
            listenstore
        """
        timestamp = int(time.time())
        audioscrobbler_auth_token = _get_audioscrobbler_auth_token(self.user['auth_token'], timestamp)

        r = self.handshake(self.user['musicbrainz_id'], audioscrobbler_auth_token, timestamp)
        self.assert200(r)
        response = r.data.decode('utf-8').split('\n')
        self.assertEqual(response[0], 'OK')

        sid = response[1]
        data = {
            's': sid,
            'a[0]': 'Kishore Kumar',
            't[0]': 'Saamne Ye Kaun Aya',
            'o[0]': 'P',
            'l[0]': 300,
            'b[0]': 'Jawani Diwani',
            'i[0]': int(time.time()),
        }

        r = self.client.post(self.custom_url_for('api_compat_old.submit_listens'), data=data)
        self.assert200(r)
        self.assertEqual(r.data.decode('utf-8'), 'OK\n')

        time.sleep(1)
        recalculate_all_user_data()
        to_ts = datetime.now(timezone.utc)
        with self.app.app_context():
            listens, _, _ = self.ls.fetch_listens(self.user, to_ts=to_ts)
        self.assertEqual(len(listens), 1)

    def test_submit_listen_invalid_sid(self):
        """ Tests endpoint for 400 Bad Request if invalid session id is sent """

        sid = ''
        data = {
            's': sid,
            'a[0]': 'Kishore Kumar',
            't[0]': 'Saamne Ye Kaun Aya',
            'o[0]': 'P',
            'l[0]': 300,
            'b[0]': 'Jawani Diwani',
            'i[0]': int(time.time()),
        }

        r = self.client.post(self.custom_url_for('api_compat_old.submit_listens'), data=data)
        self.assert401(r)
        self.assertEqual(r.data.decode('utf-8'), 'BADSESSION\n')

    def test_submit_listen_invalid_data(self):
        """ Tests endpoint for 400 Bad Request if invalid data is sent """
        timestamp = int(time.time())
        audioscrobbler_auth_token = _get_audioscrobbler_auth_token(self.user['auth_token'], timestamp)

        r = self.handshake(self.user['musicbrainz_id'], audioscrobbler_auth_token, timestamp)
        self.assert200(r)
        response = r.data.decode('utf-8').split('\n')
        self.assertEqual(response[0], 'OK')

        sid = response[1]

        # no artist in data
        data = {
            's': sid,
            't[0]': 'Saamne Ye Kaun Aya',
            'o[0]': 'P',
            'l[0]': 300,
            'b[0]': 'Jawani Diwani',
            'i[0]': int(time.time()),
        }

        r = self.client.post(self.custom_url_for('api_compat_old.submit_listens'), data=data)
        self.assert400(r)
        self.assertEqual(r.data.decode('utf-8').split()[0], 'FAILED')

        # add artist and remove track name
        data['a[0]'] = 'Kishore Kumar'
        del data['t[0]']
        r = self.client.post(self.custom_url_for('api_compat_old.submit_listens'), data=data)
        self.assert400(r)
        self.assertEqual(r.data.decode('utf-8').split()[0], 'FAILED')

        # add track name and remove timestamp
        data['t[0]'] = 'Saamne Ye Kaun Aya'
        del data['i[0]']
        r = self.client.post(self.custom_url_for('api_compat_old.submit_listens'), data=data)
        self.assert400(r)
        self.assertEqual(r.data.decode('utf-8').split()[0], 'FAILED')

        # re-add a timestamp in ns
        data['i[0]'] = int(time.time()) * 10**9
        r = self.client.post(self.custom_url_for('api_compat_old.submit_listens'), data=data)
        self.assert400(r)
        self.assertEqual(r.data.decode('utf-8').split()[0], 'FAILED')

    def test_playing_now(self):
        """ Tests playing now notifications """
        timestamp = int(time.time())
        audioscrobbler_auth_token = _get_audioscrobbler_auth_token(self.user['auth_token'], timestamp)

        r = self.handshake(self.user['musicbrainz_id'], audioscrobbler_auth_token, timestamp)
        self.assert200(r)
        response = r.data.decode('utf-8').split('\n')
        self.assertEqual(response[0], 'OK')

        sid = response[1]
        data = {
            's': sid,
            'a': 'Kishore Kumar',
            't': 'Saamne Ye Kaun Aya',
            'b': 'Jawani Diwani',
        }

        r = self.client.post(self.custom_url_for('api_compat_old.submit_now_playing'), data=data)
        self.assert200(r)
        self.assertEqual(r.data.decode('utf-8'), 'OK\n')

    def test_get_session(self):
        """ Tests _get_session method in api_compat_deprecated """
        s = Session.create_by_user_id(self.db_conn, self.user['id'])
        session = _get_session(self.db_conn, s.sid)
        self.assertEqual(s.sid, session.sid)

    def test_get_session_which_doesnt_exist(self):
        """ Make sure BadRequest is raised when we try to get a session that doesn't exists """
        with self.assertRaises(BadRequest):
            session = _get_session(self.db_conn, '')

    def test_404(self):

        r = self.client.get('/thisurldoesnotexist')
        self.assert404(r)

    def test_to_native_api_now_playing(self):
        """ Tests _to_native_api when used with data sent to the now_playing endpoint """

        data = {
            's': '',
            'a': 'Kishore Kumar',
            't': 'Saamne Ye Kaun Aya',
            'b': 'Jawani Diwani',
        }

        native_data = _to_native_api(data, '')
        self.assertDictEqual(native_data, {
                'track_metadata': {
                    'track_name': 'Saamne Ye Kaun Aya',
                    'artist_name': 'Kishore Kumar',
                    'release_name': 'Jawani Diwani'
                }
            }
        )

        del data['a']
        native_data = _to_native_api(data, '')
        self.assertIsNone(native_data)

        data['a'] = 'Kishore Kumar'
        del data['t']
        native_data = _to_native_api(data, '')
        self.assertIsNone(native_data)

        data['t'] = 'Saamne Ye Kaun Aya'
        del data['b']
        native_data = _to_native_api(data, '')
        self.assertIsNone(native_data)

    def test_to_native_api(self):
        """ Tests _to_native_api with data that is sent to the submission endpoint """
        t = int(time.time())

        data = {
            's': '',
            'a[0]': 'Kishore Kumar',
            't[0]': 'Saamne Ye Kaun Aya',
            'o[0]': 'P',
            'l[0]': 300,
            'b[0]': 'Jawani Diwani',
            'i[0]': t,
            'a[1]': 'Kishore Kumar',
            't[1]': 'Wada Karo',
            'o[1]': 'P',
            'l[1]': 300,
            'b[1]': 'Jawani Diwani',
            'i[1]': t + 10,
        }

        self.assertDictEqual(_to_native_api(data, '[0]'), {
            'listened_at': t,
            'track_metadata': {
                'artist_name': 'Kishore Kumar',
                'track_name':  'Saamne Ye Kaun Aya',
                'release_name': 'Jawani Diwani',
                'additional_info': {
                    'source': 'P',
                    'track_length': 300
                }
            }
        })

        self.assertDictEqual(_to_native_api(data, '[1]'), {
            'listened_at': t + 10,
            'track_metadata': {
                'artist_name': 'Kishore Kumar',
                'track_name':  'Wada Karo',
                'release_name': 'Jawani Diwani',
                'additional_info': {
                    'source': 'P',
                    'track_length': 300
                }
            }
        })

        del data['a[0]']
        self.assertIsNone(_to_native_api(data, '[0]'))

        data['a[0]'] = 'Kishore Kumar'
        del data['t[0]']
        native_data = _to_native_api(data, '[0]')
        self.assertIsNone(native_data)

        data['t[0]'] = 'Saamne Ye Kaun Aya'
        del data['b[0]']
        native_data = _to_native_api(data, '[0]')
        self.assertIsNone(native_data)
