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

import json
import listenbrainz.db.user as db_user
from brainzutils.musicbrainz_db import engine as mb_engine

from hashlib import md5
from time import time

from flask import current_app, Blueprint, request, render_template, redirect
from werkzeug.exceptions import BadRequest
from listenbrainz.db.lastfm_session import Session
from listenbrainz.webserver.errors import APIBadRequest
from listenbrainz.webserver.utils import REJECT_LISTENS_WITHOUT_EMAIL_ERROR
from listenbrainz.webserver.views.api_tools import insert_payload, is_valid_timestamp, LISTEN_TYPE_PLAYING_NOW, \
    is_valid_uuid, check_for_unicode_null_recursively

api_compat_old_bp = Blueprint('api_compat_old', __name__)


@api_compat_old_bp.route('/', methods=['GET', 'POST', 'OPTIONS'])
def handshake():
    """ View to handshake with the client.

        Creates a new session stored in api_compat.session and then later uses it
        to submit listens. We do auth assuming the LB auth_tokens to be
        passwords, so this should work when users enter their LB auth tokens as passwords
        in clients.
    """

    if request.args.get('hs', '') != 'true':
        return redirect('https://listenbrainz.org/lastfm-proxy')

    user = db_user.get_by_mb_id(request.args.get('u'), fetch_email=True)
    if user is None:
        return 'BADAUTH\n', 401

    if mb_engine and current_app.config["REJECT_LISTENS_WITHOUT_USER_EMAIL"] and user["email"] is None:
        return 'BADAUTH ' + REJECT_LISTENS_WITHOUT_EMAIL_ERROR + '\n', 401

    auth_token = request.args.get('a', '')
    timestamp = request.args.get('t', 0)

    correct = _get_audioscrobbler_auth_token(user['auth_token'], timestamp)

    if auth_token != _get_audioscrobbler_auth_token(user['auth_token'], timestamp):
        return 'BADAUTH\n', 401

    session = Session.create_by_user_id(user['id'])
    current_app.logger.info('New session created with id: {}'.format(session.sid))

    return '\n'.join([
        'OK',
        session.sid,
        '{}/np_1.2'.format(current_app.config['LASTFM_PROXY_URL']),
        '{}/protocol_1.2\n'.format(current_app.config['LASTFM_PROXY_URL'])
    ])


@api_compat_old_bp.route('/np_1.2', methods=['POST', 'OPTIONS'])
def submit_now_playing():
    """ Handle now playing notifications sent by clients """

    current_app.logger.info(json.dumps(request.form, indent=4))

    try:
        session = _get_session(request.form.get('s', ''))
    except BadRequest:
        return 'BADSESSION\n', 401

    listen = _to_native_api(request.form, append_key='')
    if listen is None:
        return 'FAILED Invalid data submitted!\n', 400


    listens = [listen]
    user = db_user.get(session.user_id)
    insert_payload(listens, user, LISTEN_TYPE_PLAYING_NOW)

    return 'OK\n'


@api_compat_old_bp.route('/protocol_1.2', methods=['POST', 'OPTIONS'])
def submit_listens():
    """ Submit listens received from clients into the listenstore after validating them. """

    try:
        session = _get_session(request.form.get('s', ''))
    except BadRequest:
        return 'BADSESSION\n', 401

    listens = []
    index = 0
    while True:
        listen = _to_native_api(request.form, append_key='[{}]'.format(index))
        if listen is None:
            break
        else:
            listens.append(listen)
            index += 1

    if not listens:
        return 'FAILED Invalid data submitted!\n', 400

    user = db_user.get(session.user_id)
    insert_payload(listens, user)

    return 'OK\n'


def _to_native_api(data, append_key):
    """ Converts the scrobble submitted with given string appended to keys to the audioscrobbler api into
        a listen of the native api format. Returns None if no scrobble exists with that string appended
        to keys.

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
            'track_metadata': {
                'artist_name': data['a{}'.format(append_key)],
                'track_name': data['t{}'.format(append_key)],
                'release_name': data['b{}'.format(append_key)],
                'additional_info': {}
            }
        }
    except KeyError:
        return None

    # if this is not a now playing request, get the timestamp
    if append_key != '':
        try:
            listen['listened_at'] = int(data['i{}'.format(append_key)])
        except (KeyError, ValueError):
            return None

        # if timestamp is too high, this is an invalid listen
        # in order to make up for possible clock skew, we allow
        # timestamps to be one hour ahead of server time
        if not is_valid_timestamp(listen['listened_at']):
            return None

    if 'o{}'.format(append_key) in data:
        listen['track_metadata']['additional_info']['source'] = data['o{}'.format(append_key)]

    if 'r{}'.format(append_key) in data:
        listen['track_metadata']['additional_info']['rating'] = data['r{}'.format(append_key)]

    if 'n{}'.format(append_key) in data:
        listen['track_metadata']['additional_info']['track_number'] = data['n{}'.format(append_key)]

    if 'm{}'.format(append_key) in data:
        mbid = data['m{}'.format(append_key)]
        if is_valid_uuid(mbid):
            listen['track_metadata']['additional_info']['recording_mbid'] = mbid

    if 'l{}'.format(append_key) in data:
        listen['track_metadata']['additional_info']['track_length'] = data['l{}'.format(append_key)]

    # if there is nothing in the additional info field of the track, remove it
    if listen['track_metadata']['additional_info'] == {}:
        del listen['track_metadata']['additional_info']

    try:
        check_for_unicode_null_recursively(listen)
    except APIBadRequest:
        return None

    return listen


def _get_session(session_id):
    """ Get the session with the passed session id.

        Returns: Session object with given session id
                 If session is not present in db, raises BadRequest
    """

    session = Session.load(session_id)
    if session is None:
        raise BadRequest("Session not found")
    return session


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
