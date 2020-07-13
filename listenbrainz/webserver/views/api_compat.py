
import time
import json
import re
import listenbrainz.db.user as db_user
from collections import defaultdict
from yattag import Doc
import yattag
from flask import Blueprint, request, render_template
from flask_login import login_required, current_user
from listenbrainz.webserver.external import messybrainz
from listenbrainz.webserver.rate_limiter import ratelimit
from listenbrainz.webserver.errors import InvalidAPIUsage, CompatError
import xmltodict
from listenbrainz.webserver.views.api_tools import insert_payload, validate_listen
from listenbrainz.db.lastfm_user import User
from listenbrainz.db.lastfm_session import Session
from listenbrainz.db.lastfm_token import Token
import calendar
from datetime import datetime
from listenbrainz.webserver.timescale_connection import _ts

api_bp = Blueprint('api_compat', __name__)


@api_bp.route('/api/auth/', methods=['GET'])
@ratelimit()
@login_required
def api_auth():
    """ Renders the token activation page.
    """
    token = request.args['token']
    return render_template(
        "user/auth.html",
        user_id=current_user.musicbrainz_id,
        token=token
    )


@api_bp.route('/api/auth/', methods=['POST'])
@ratelimit()
@login_required
def api_auth_approve():
    """ Authenticate the user token provided.
    """
    user = User.load_by_name(current_user.musicbrainz_id)
    if "token" not in request.form:
        return render_template(
            "user/auth.html",
            user_id=current_user.musicbrainz_id,
            msg="Missing required parameters. Please provide correct parameters and try again."
        )
    token = Token.load(request.form['token'])
    if not token:
        return render_template(
            "user/auth.html",
            user_id=current_user.musicbrainz_id,
            msg="Either this token is already used or invalid. Please try again."
        )
    if token.user:
        return render_template(
            "user/auth.html",
            user_id=current_user.musicbrainz_id,
            msg="This token is already approved. Please check the token and try again."
        )
    if token.has_expired():
        return render_template(
            "user/auth.html",
            user_id=current_user.musicbrainz_id,
            msg="This token has expired. Please create a new token and try again."
        )
    token.approve(user.name)
    return render_template(
        "user/auth.html",
        user_id=current_user.musicbrainz_id,
        msg="Token %s approved for user %s, press continue in client." % (token.token, current_user.musicbrainz_id)
    )


@api_bp.route('/2.0/', methods=['POST', 'GET'])
@ratelimit()
def api_methods():
    """ Receives both (GET & POST)-API calls and redirects them to appropriate methods.
    """
    data = request.args if request.method == 'GET' else request.form
    method = data['method'].lower()

    if method in ('track.updatenowplaying', 'track.scrobble'):
        return record_listens(request, data)
    elif method == 'auth.getsession':
        return get_session(request, data)
    elif method == 'auth.gettoken':
        return get_token(request, data)
    elif method == 'user.getinfo':
        return user_info(request, data)
    elif method == 'auth.getsessioninfo':
        return session_info(request, data)
    else:
        # Invalid Method
        raise InvalidAPIUsage(CompatError.INVALID_METHOD, output_format=data.get('format', "xml"))


def session_info(request, data):
    try:
        sk = data['sk']
        api_key = data['api_key']
        output_format = data.get('format', 'xml')
        username = data['username']
    except KeyError:
        raise InvalidAPIUsage(CompatError.INVALID_PARAMETERS, output_format=output_format)        # Missing Required Params

    session = Session.load(sk)
    if (not session) or User.load_by_name(username).id != session.user.id:
        raise InvalidAPIUsage(CompatError.INVALID_SESSION_KEY, output_format=output_format)       # Invalid Session KEY

    print("SESSION INFO for session %s, user %s" % (session.id, session.user.name))

    doc, tag, text = Doc().tagtext()
    with tag('lfm', status='ok'):
        with tag('application'):
            with tag('session'):
                with tag('name'):
                    text(session.user.name)
                with tag('key'):
                    text(session.id)
                with tag('subscriber'):
                    text('0')
                with tag('country'):
                    text('US')

    return format_response('<?xml version="1.0" encoding="utf-8"?>\n' + yattag.indent(doc.getvalue()),
                           output_format)


def get_token(request, data):
    """ Issue a token to user after verying his API_KEY
    """
    output_format = data.get('format', 'xml')
    api_key = data.get('api_key')

    if not api_key:
        raise InvalidAPIUsage(CompatError.INVALID_PARAMETERS, output_format=output_format)   # Missing required params
    if not Token.is_valid_api_key(api_key):
        raise InvalidAPIUsage(CompatError.INVALID_API_KEY, output_format=output_format)      # Invalid API_KEY

    token = Token.generate(api_key)

    doc, tag, text = Doc().tagtext()
    with tag('lfm', status='ok'):
        with tag('token'):
            text(token.token)
    return format_response('<?xml version="1.0" encoding="utf-8"?>\n' + yattag.indent(doc.getvalue()),
                           output_format)


def get_session(request, data):
    """ Create new session after validating the API_key and token.
    """
    output_format = data.get('format', 'xml')
    try:
        api_key = data['api_key']
        token = Token.load(data['token'], api_key)
    except KeyError:
        raise InvalidAPIUsage(CompatError.INVALID_PARAMETERS, output_format=output_format)   # Missing Required Params

    if not token:
        if not Token.is_valid_api_key(api_key):
            raise InvalidAPIUsage(CompatError.INVALID_API_KEY, output_format=output_format)  # Invalid API_key
        raise InvalidAPIUsage(CompatError.INVALID_TOKEN, output_format=output_format)        # Invalid token
    if token.has_expired():
        raise InvalidAPIUsage(CompatError.TOKEN_EXPIRED, output_format=output_format)        # Token expired
    if not token.user:
        raise InvalidAPIUsage(CompatError.UNAUTHORIZED_TOKEN, output_format=output_format)   # Unauthorized token

    session = Session.create(token)

    doc, tag, text = Doc().tagtext()
    with tag('lfm', status='ok'):
        with tag('session'):
            with tag('name'):
                text(session.user.name)
            with tag('key'):
                text(session.sid)
            with tag('subscriber'):
                text('0')

    return format_response('<?xml version="1.0" encoding="utf-8"?>\n' + yattag.indent(doc.getvalue()),
                           data.get('format', "xml"))


def _to_native_api(lookup, method="track.scrobble", output_format="xml"):
    """ Converts the list of listens received in the new Last.fm submission format
        to the native ListenBrainz API format.
        Returns: type_of_listen and listen_payload
    """
    listen_type = 'listens'
    if method == 'track.updateNowPlaying':
        listen_type = 'playing_now'
        if len(list(lookup.keys())) != 1:
            raise InvalidAPIUsage(CompatError.INVALID_PARAMETERS, output_format=output_format)       # Invalid parameters

    listens = []
    for ind, data in lookup.items():
        listen = {
            'track_metadata': {
                'additional_info': {}
            }
        }
        if 'artist' in data:
            listen['track_metadata']['artist_name'] = data['artist']
        if 'track' in data:
            listen['track_metadata']['track_name'] = data['track']
        if 'timestamp' in data:
            listen['listened_at'] = data['timestamp']
        if 'album' in data:
            listen['track_metadata']['release_name'] = data['album']
        if 'context' in data:
            listen['track_metadata']['additional_info']['context'] = data['context']
        if 'streamId' in data:
            listen['track_metadata']['additional_info']['stream_id'] = data['streamId']
        if 'trackNumber' in data:
            listen['track_metadata']['additional_info']['tracknumber'] = data['trackNumber']
        if 'mbid' in data:
            listen['track_metadata']['release_mbid'] = data['mbid']
        if 'duration' in data:
            listen['track_metadata']['additional_info']['duration'] = data['duration']
        # Choosen_by_user is 1 by default
        listen['track_metadata']['additional_info']['choosen_by_user'] = data.get('choosenByUser', 1)
        listens.append(listen)

    return listen_type, listens


def record_listens(request, data):
    """ Submit the listen in the lastfm format to be inserted in db.
        Accepts listens for both track.updateNowPlaying and track.scrobble methods.
    """
    output_format = data.get('format', 'xml')
    try:
        sk, api_key = data['sk'], data['api_key']
    except KeyError:
        raise InvalidAPIUsage(CompatError.INVALID_PARAMETERS, output_format=output_format)    # Invalid parameters

    session = Session.load(sk)
    if not session:
        if not Token.is_valid_api_key(api_key):
            raise InvalidAPIUsage(CompatError.INVALID_API_KEY, output_format=output_format)   # Invalid API_KEY
        raise InvalidAPIUsage(CompatError.INVALID_SESSION_KEY, output_format=output_format)   # Invalid Session KEY

    lookup = defaultdict(dict)
    for key, value in data.items():
        if key in ["sk", "token", "api_key", "method", "api_sig"]:
            continue
        matches = re.match('(.*)\[(\d+)\]', key)
        if matches:
            key = matches.group(1)
            number = matches.group(2)
        else:
            number = 0
        lookup[number][key] = value

    if request.form['method'].lower() == 'track.updatenowplaying':
        for i, listen in lookup.items():
            if 'timestamp' not in listen:
                listen['timestamp'] = calendar.timegm(datetime.now().utctimetuple())

    # Convert to native payload then submit 'em after validation.
    listen_type, native_payload = _to_native_api(lookup, data['method'], output_format)
    for listen in native_payload:
        validate_listen(listen, listen_type)

    user = db_user.get(session.user_id)
    augmented_listens = insert_payload(native_payload, user, listen_type=listen_type)

    # With corrections than the original submitted listen.
    doc, tag, text = Doc().tagtext()
    with tag('lfm', status='ok'):
        if listen_type == 'playing_now':
            doc.asis(create_response_for_single_listen(list(lookup.values())[0], augmented_listens[0], listen_type))
        else:
            accepted_listens = len(lookup.values())
            # Currently LB accepts all the listens and ignores none
            with tag('scrobbles', accepted=accepted_listens, ignored='0'):
                for original_listen, augmented_listen in zip(list(lookup.values()), augmented_listens):
                    doc.asis(create_response_for_single_listen(original_listen, augmented_listen, listen_type))

    return format_response('<?xml version="1.0" encoding="utf-8"?>\n' + yattag.indent(doc.getvalue()),
                           output_format)


def create_response_for_single_listen(original_listen, augmented_listen, listen_type):
    """Create XML response for a single listen.

    Args:
        original_listen (dict): Original submitted listen.
        augmented_listen (dict): Augmented(corrected) listen.
        listen_type (string): Type of listen ('playing_now' or 'listens').

    Returns:
        XML response for a single listen.
        If listen is of type 'playing_now' response is as described in following link
        https://www.last.fm/api/show/track.updateNowPlaying
        Otherwise response is as described in following link
        https://www.last.fm/api/show/track.scrobble .
    """
    corrected = defaultdict(lambda: '0')

    track = augmented_listen['track_metadata']['track_name']
    if original_listen['track'] != augmented_listen['track_metadata']['track_name']:
        corrected['track'] = '1'

    artist = augmented_listen['track_metadata']['artist_name']
    if original_listen['artist'] != augmented_listen['track_metadata']['artist_name']:
        corrected['artist'] = '1'

    ts = augmented_listen['listened_at']

    albumArtist = artist
    if original_listen.get('albumArtist', original_listen['artist']) != artist:
        corrected['albumArtist'] = '1'

    album = augmented_listen['track_metadata'].get('release_name', '')
    if original_listen.get('album', '') != album:
        corrected['album'] = '1'

    doc, tag, text = Doc().tagtext()
    with tag('nowplaying' if listen_type == 'playing_now' else 'scrobble'):
        with tag('track', corrected=corrected['track']):
            text(track)
        with tag('artist', corrected=corrected['artist']):
            text(artist)
        with tag('album', corrected=corrected['album']):
            text(album)
        with tag('albumArtist', corrected=corrected['albumArtist']):
            text(albumArtist)
        with tag('timestamp'):
            text(ts)
        with tag('ignoredMessage', code="0"):
            text('')

    return doc.getvalue()


def format_response(data, format="xml"):
    """ Convert the XML response to required format.
        NOTE: The order of attributes may change while converting from XML to other formats.
        NOTE: The rendering format for the error does not follow these rules and has been managed separately
              in the error handlers.
        The response is a translation of the XML response format, converted according to the
        following rules:

        1. Attributes are expressed as string member values with the attribute name as key.
        2. Element child nodes are expressed as object members values with the node name as key.
        3. Text child nodes are expressed as string values, unless the element also contains
           attributes, in which case the text node is expressed as a string member value with the
           key #text.
        4. Repeated child nodes will be grouped as an array member with the shared node name as key.

        (The #text notation is rarely used in XML responses.)
    """
    if format == 'xml':
        return data
    elif format == 'json':
        # Remove the <lfm> tag and its attributes
        jsonData = xmltodict.parse(data)['lfm']
        for k in jsonData.keys():
            if k[0] == '@':
                jsonData.pop(k)

        def remove_attrib_prefix(data):
            """ Filter the JSON response to merge some attributes and clean dict.
                NOTE: This won't keep the dict ordered !!
            """
            if not isinstance(data, dict):
                return data
            for k in list(data.keys()):
                if k[0] == "@":
                    data[k[1:]] = data.pop(k)
                elif isinstance(data[k], str):
                    continue
                elif isinstance(data[k], list):
                    for ind, item in enumerate(data[k]):
                        data[k][ind] = remove_attrib_prefix(item)
                elif isinstance(data[k], dict):
                    data[k] = remove_attrib_prefix(data[k])
                else:
                    print(type(data[k]))
            return data

        return json.dumps(remove_attrib_prefix(jsonData), indent=4)


def user_info(request, data):
    """ Gives information about the user specified in the parameters.
    """
    try:
        api_key = data['api_key']
        output_format = data.get('format', 'xml')
        sk = data.get('sk')
        username = data.get('user')
        if not (sk or username):
            raise KeyError

        if not Token.is_valid_api_key(api_key):
            raise InvalidAPIUsage(CompatError.INVALID_API_KEY, output_format=output_format)     # Invalid API key

        user = User.load_by_sessionkey(sk, api_key)
        if not user:
            raise InvalidAPIUsage(CompatError.INVALID_SESSION_KEY, output_format=output_format)  # Invalid Session key

        query_user = User.load_by_name(username) if (username and username != user.name) else user
        if not query_user:
            raise InvalidAPIUsage(CompatError.INVALID_RESOURCE, output_format=output_format)     # Invalid resource specified

    except KeyError:
        raise InvalidAPIUsage(CompatError.INVALID_PARAMETERS, output_format=output_format)       # Missing required params

    doc, tag, text = Doc().tagtext()
    with tag('lfm', status='ok'):
        with tag('user'):
            with tag('name'):
                text(query_user.name)
            with tag('realname'):
                text(query_user.name)
            with tag('url'):
                text('http://listenbrainz.org/user/' + query_user.name)
            with tag('playcount'):
                text(User.get_play_count(query_user.id, _ts))
            with tag('registered', unixtime=str(query_user.created.strftime("%s"))):
                text(str(query_user.created))

    return format_response('<?xml version="1.0" encoding="utf-8"?>\n' + yattag.indent(doc.getvalue()),
                           data.get('format', "xml"))
