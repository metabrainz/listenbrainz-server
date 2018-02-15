""" This module tests Last.fm Scrobbling 2.0 compatibility features """

# listenbrainz-server - Server for the ListenBrainz project.
#
# Copyright (C) 2018 Kartikeya Sharma <09kartikeya@gmail.com>
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


import json
import time
import xmltodict

import listenbrainz.db.user as db_user
from flask import url_for, current_app
from listenbrainz.db.lastfm_session import Session
from listenbrainz.db.lastfm_token import Token
from listenbrainz.db.lastfm_user import User
from listenbrainz.tests.integration import APICompatIntegrationTestCase


class APICompatTestCase(APICompatIntegrationTestCase):

    def setUp(self):
        super(APICompatTestCase, self).setUp()
        self.lb_user = db_user.get_or_create('apicompattestuser')
        self.lfm_user = User(
            self.lb_user['id'],
            self.lb_user['created'],
            self.lb_user['musicbrainz_id'],
            self.lb_user['auth_token'],
        )

    def test_record_listen_now_playing(self):
        """ Tests if listen of type 'nowplaying' is recorded correctly
            if valid information is provided.
        """

        token = Token.generate(self.lfm_user.api_key)
        token.approve(self.lfm_user.name)
        session = Session.create(token)

        data = {
            'method': 'track.updateNowPlaying',
            'api_key': self.lfm_user.api_key,
            'sk': session.sid,
            'artist[0]': 'Kishore Kumar',
            'track[0]': 'Saamne Ye Kaun Aya',
            'album[0]': 'Jawani Diwani',
            'duration[0]': 300,
            'timestamp[0]': int(time.time()),
        }

        r = self.client.post(url_for('api_compat.api_methods'), data=data)
        self.assert200(r)

        response = xmltodict.parse(r.data)
        self.assertEqual(response['lfm']['@status'], 'ok')
        self.assertIsNotNone(response['lfm']['nowplaying'])
