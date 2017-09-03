""" This module adds compatibility for clients using the deprecated AudioScrobbler 1.2
    protocol.

    See the protocol details here: http://www.audioscrobbler.net/development/protocol/
"""

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

import listenbrainz.config as config
import listenbrainz.db.user as db_user

from hashlib import md5
from time import time

from flask import Blueprint, request, render_template
from listenbrainz.db.lastfm_session import Session
from listenbrainz.webserver.views.api_tools import insert_payload


api_compat_old_bp = Blueprint('api_compat_old', __name__)


@api_compat_old_bp.route('/')
def handshake():
    """ View to handshake with the client.

        Creates a new session stored in api_compat.session and then later uses it
        to submit listens. We do auth assuming the LB auth_tokens to be
        passwords, so this should work when users enter their LB auth tokens as passwords
        in clients.
    """

    if not request.args.get('hs', '') == 'true':
        return render_template('api_compat/index.html')

    user = db_user.get_by_mb_id(request.args.get('u'))
    if user is None:
        return 'BADAUTH\n', 401

    auth_token = request.args.get('a', '')
    timestamp = request.args.get('t', 0)

    correct = _get_audioscrobbler_auth_token(user['auth_token'], timestamp)

    if auth_token != _get_audioscrobbler_auth_token(user['auth_token'], timestamp):
        return 'BADAUTH\n', 401

    session = Session.create_by_user_id(user['id'])

    return '\n'.join([
        'OK',
        session.sid,
        '{}/np_1.2'.format(config.LASTFM_PROXY_URL),
        '{}/protocol_1.2'.format(config.LASTFM_PROXY_URL)
    ])


@api_compat_old_bp.route('/protocol_1.2', methods=['POST', 'OPTIONS'])
@api_compat_old_bp.route('/np_1.2', methods=['POST', 'OPTIONS'] )
def submit_listens():
    """ Submit listens received from clients into the listenstore after validating them. """


    session = Session.load(request.form.get('s', ''))
    if session is None:
        return "BADSESSION\n", 401

    listens = []
    index = 0
    while True:
        listen = _to_native_api(request.form, index)
        if listen is None:
            break
        else:
            listens.append(listen)
            index += 1

    if not listens:
        return "FAILED No data submitted!\n", 400



    user = db_user.get(session.user_id)
    insert_payload(listens, user)

    return "OK\n"


def _to_native_api(data, index):
    """ Converts the scrobble submitted at given index to the audioscrobbler api into
        a listen of the native api format. Returns None if no scrobble exists at that
        index.

        Returns: dict of form
            {
                'listened_at': (int)
                'track_metadata': {
                    'artist_name': (str),
                    'track_name': (str)
                }
            }
    """

    try:
        listen = {
            'listened_at': data['i[{}]'.format(index)],
            'track_metadata': {
                'artist_name': data['a[{}]'.format(index)],
                'track_name': data['t[{}]'.format(index)],
                'release_name': data['b[{}]'.format(index)],
                'additional_info': {
                    'source': data['o[{}]'.format(index)]
                }
            }
        }
    except KeyError:
        return None

    if 'r[{}]'.format(index) in data:
        listen['track_metadata']['additional_info']['rating'] = data['r[{}]'.format(index)]

    if 'n[{}]'.format(index) in data:
        listen['track_metadata']['additional_info']['track_number'] = data['n[{}]'.format(index)]

    if 'm[{}]'.format(index) in data:
        listen['track_metadata']['additional_info']['recording_mbid'] = data['m[{}]'.format(index)]

    return listen

def _get_audioscrobbler_auth_token(lb_auth_token, timestamp):
    """ Gets the correct auth token for checking against the token sent by client
        during handshake.

        The token is calculated using the formula:

            md5(md5(password) + timestamp)

        where md5 returns the md5sum with hex characters in lowercase and + is the
        concatenation operator.

        We use auth_token as password here, so users can just put their LB auth tokens
        as passwords in clients and it should work.
    """

    token_md5 = md5(lb_auth_token.encode('utf-8')).hexdigest()
    concatenated = '{}{}'.format(token_md5, timestamp)
    return md5(concatenated.encode('utf-8')).hexdigest()
