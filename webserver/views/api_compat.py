import time
import json
import re
from collections import defaultdict
from flask import Blueprint, request, render_template
from flask_login import login_required, current_user
from yattag import Doc
import yattag
from webserver.kafka_connection import _kafka
from webserver.external import messybrainz
# import db.user
from webserver.rate_limiter import ratelimit
import xmltodict

from api_tools import _send_listens_to_kafka, _validate_api_key, _get_augumented_listens
from db.mockdata import User, Session, Token

staticuser = "armalcolite"
api_bp = Blueprint('api_compat', __name__)

# List of errors compatible with LastFM messages.
ERROR_MESSAGES = {
    1: "This error does not exist",
    2: "Invalid service -This service does not exist",
    3: "Invalid Method - No method with that name in this package",
    4: "Invalid Token - Invalid authentication token supplied",
    5: "Invalid format - This service doesn't exist in that format",
    6: "Invalid parameters - Your request is missing a required parameter",
    7: "Invalid resource specified",
    8: "Operation failed - Most likely the backend service failed. Please try again.",
    9: "Invalid session key - Please re-authenticate",
    10: "Invalid API key - You must be granted a valid key by last.fm",
    11: "Service Offline - This service is temporarily offline. Try again later.",
    12: "Subscribers Only - This station is only available to paid last.fm subscribers",
    13: "Invalid method signature supplied",
    14: "Unauthorized Token - This token has not been authorized",
    15: "This token has expired",
    16: "The service is temporarily unavailable, please try again.",
    17: "Login: User requires to be logged in",
    18: "Trial Expired - This user has no free radio plays left. Subscription required.",
    19: "This error does not exist",
    20: "Not Enough Content - There is not enough content to play this station",
    21: "Not Enough Members - This group does not have enough members for radio",
    22: "Not Enough Fans - This artist does not have enough fans for for radio",
    23: "Not Enough Neighbours - There are not enough neighbours for radio",
    24: "No Peak Radio - This user is not allowed to listen to radio during peak usage",
    25: "Radio Not Found - Radio station not found",
    26: "API Key Suspended - This application is not allowed to make requests to the web services",
    27: "Deprecated - This type of request is no longer supported",
    29: "Rate Limit Exceded - Your IP has made too many requests in a short period, exceeding our API guidelines"
}


@api_bp.route('/api/auth/', methods=['GET'])
@ratelimit()
@login_required
def api_auth():
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
    user = request.form['user']
    token = Token.load(request.form['token'])
    if not token:
        return render_template(
            "user/auth.html",
            user_id=current_user.musicbrainz_id,
            msg="Either this token is already used or invalid. Please try again."
        )

    token.validate(User.load_by_name(user).id)
    return render_template(
        "user/auth.html",
        user_id=current_user.musicbrainz_id,
        msg="Token %s approved for user %s, press continue in client." % (token.token, user)
    )


@api_bp.route('/2.0/', methods=['GET'])
@ratelimit()
def api_get():
    method = request.args['method'].lower()
    return {
        'user.getinfo': user_info,
        'auth.gettoken': get_token,
        'auth.getsessioninfo': get_session_info
    }.get(method, invalid_method_error)(request, request.args)


@api_bp.route('/2.0/', methods=['POST'])
@ratelimit()
def api_post():
    method = request.form['method'].lower()
    return {
        'track.updatenowplaying': now_playing,
        'track.scrobble': scrobble,
        'auth.getsession': get_session,
        'user.getinfo': user_info
    }.get(method, invalid_method_error)(request, request.form)


def invalid_method_error(request, data):
    """ Return error for invalid method name """
    return format_error(3, data.get('format', "xml"))


def format_error(error_code, error_format="xml"):
    """ Returns the errors with error codes in appropriate format """
    if error_format == "json":
        return json.dumps({
            "error": error_code,
            "message": ERROR_MESSAGES[error_code]
        }, indent=4)

    doc, tag, text = Doc().tagtext()
    with tag('lfm', status="failed"):
        with tag('error', code=error_code):
            text(ERROR_MESSAGES[error_code])
    return format_response('<?xml version="1.0" encoding="utf-8"?>\n' + yattag.indent(doc.getvalue()),
                           data.get('format', "xml"))


def get_token(request, data):
    """ Issue a token to user after verying his API_KEY """

    output_format = data.get("format", "xml")
    if not data.get('api_key', None):
        return format_error(6, output_format)   # Missing required params
    if not _validate_api_key(data['api_key']):
        return format_error(10, output_format)   # Invalid API_KEY

    token = Token.generate()

    doc, tag, text = Doc().tagtext()
    with tag('lfm', status="ok"):
        with tag('token'):
            text(token.token)
    return format_response('<?xml version="1.0" encoding="utf-8"?>\n' + yattag.indent(doc.getvalue()),
                           output_format)


# NEEDS MORE WORK !!
# Validate API Key
def get_session(request, data):
    """ Create new session """

    output_format = data.get("format", "xml")
    try:
        api_key = data['api_key']
        token = Token.load(data['token'])
    except KeyError:
        return format_error(6, output_format)   # Missing Required Params

    if not token:
        return format_error(4, output_format)   # Invalid token

    if not token.user:
        return format_error(14, output_format)   # Unauthorized token

    print "GRANTING SESSION for token %s" % token.token
    token.consume()
    session = Session.create(token.user)

    doc, tag, text = Doc().tagtext()
    with tag('lfm', status="ok"):
        with tag('session'):
            with tag('name'):
                text(session.user.name)
            with tag('key'):
                text(session.id)
            with tag('subscriber'):
                text('0')

    return format_response('<?xml version="1.0" encoding="utf-8"?>\n' + yattag.indent(doc.getvalue()),
                           data.get('format', "xml"))


def get_session_info(request, data):
    sk = data['sk']
    session = Session.load(sk)
    if not session:
        print "Invalid session"
        return "NOPE"

    print "SESSION INFO for session %s, user %s" % (session.id, session.user.name)

    doc, tag, text = Doc().tagtext()
    with tag('lfm', status="ok"):
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
                           data.get('format', "xml"))


def _to_native_api(lookup):
    listens = []
    for ind, data in lookup.iteritems():
        listen = {
            'track_metadata': {
                'additional_info': {}
            }
        }
        if 'timestamp' in data:
            listen['listened_at'] = data['timestamp']
        if 'album' in data:
            listen['track_metadata']['release_name'] = data['album']
        if 'track' in data:
            listen['track_metadata']['track_name'] = data['track']
        if 'artist' in data:
            listen['track_metadata']['artist_name'] = data['artist']
        if 'mbid' in data:
            listen['track_metadata']['release_mbid'] = data['mbid']
        if 'trackNumber' in data or 'duration' in data or 'albumArtist' in data or \
                'choosenByUser' in data or 'streamId' in data or 'context' in data:
            # Album artist, Song Duration, trackNumber on the album, etc
            # are not supported by the native ListenBrainz API
            pass
        listens.append(listen)
    return listens


def scrobble(request, data):
    """ Converts the listens from the lastfm format to native API, the saves 'em """

    sk = data['sk']
    output_format = data.get('format', "xml")
    session = Session.load(sk)
    if not session:
        return format_error(9, output_format)   # Invalid Session

    lookup = defaultdict(dict)
    for key, value in data.items():
        if key == "sk" or key == "token" or key == "api_key" or key == "method":
            continue
        matches = re.match('(.*)\[(\d+)\]', key)
        if matches:
            key = matches.group(1)
            number = matches.group(2)
        else:
            number = 0
        lookup[number][key] = value

    native_payload = _to_native_api(lookup)
    augumented_listens = _get_augumented_listens(native_payload, staticuser)
    _send_listens_to_kafka("listens", augumented_listens)

    # With corrections than the original submitted listen.
    doc, tag, text = Doc().tagtext()
    with tag('lfm', status="ok"):
        with tag('scrobbles'):

            for origL, augL in zip(lookup.values(), augumented_listens):
                corr = defaultdict(lambda: "0")

                track = augL['track_metadata']['track_name']
                if origL['track'] != augL['track_metadata']['track_name']:
                    corr['track'] = '1'

                artist = augL['track_metadata']['artist_name']
                if origL['artist'] != augL['track_metadata']['artist_name']:
                    corr['artist'] = '1'

                ts = augL['listened_at']

                albumArtist = artist
                if origL.get('albumArtist', origL['artist']) != artist:
                    corr['albumArtist'] = '1'

                # TODO: Add the album part
                album = ""

                with tag('scrobble'):
                    with tag('track', corrected=corr['track']):
                        text(track)
                    with tag('artist', corrected=corr['artist']):
                        text(artist)
                    with tag('album', corrected=corr['album']):
                        text(album)
                    with tag('albumArtist', corrected=corr['albumArtist']):
                        text(albumArtist)
                    with tag('timestamp'):
                        text(ts)
                    with tag('ignoredMessage', code="0"):
                        text('')

    return format_response('<?xml version="1.0" encoding="utf-8"?>\n' + yattag.indent(doc.getvalue()),
                           output_format)


def format_response(data, format="xml"):
    """ Convert the XML response to required format.
        NOTE: The order of attributes may change while converting from XML to other formats.
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
    if format == "xml":
        return data
    elif format == "json":
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
            for k in data.keys():
                if k[0] == "@":
                    data[k[1:]] = data.pop(k)
                elif isinstance(data[k], basestring):
                    continue
                elif isinstance(data[k], list):
                    for ind, item in enumerate(data[k]):
                        data[k][ind] = remove_attrib_prefix(item)
                elif isinstance(data[k], dict):
                    data[k] = remove_attrib_prefix(data[k])
                else:
                    print type(data[k])
            return data

        return json.dumps(remove_attrib_prefix(jsonData), indent=4)


# Definately Needs WORK !
def now_playing(request, data):
    sk = data['sk']
    session = Session.load(sk)
    if not session:
        print "Invalid session"
        return "NOPE"

    track = data['track']
    artist = data['artist']
    album = data['album']
    albumArtist = data['albumArtist']

    print "NOW PLAYING- User: %s, Artist: %s, Track: %s, Album: %s"  \
        % (session.user.name, artist, track, album)

    doc, tag, text = Doc().tagtext()
    with tag('lfm', status="ok"):
        with tag('nowplaying'):
            with tag('track', corrected="0"):
                text(track)
            with tag('artist', corrected="0"):
                text(artist)
            with tag('album', corrected="0"):
                text(album)
            with tag('albumArtist', corrected="0"):
                text(albumArtist)
            with tag('ignoredMessage', code="0"):
                text('')

    return format_response('<?xml version="1.0" encoding="utf-8"?>\n' + yattag.indent(doc.getvalue()),
                           data.get('format', "xml"))


def user_info(request, data):
    sk = data['sk']
    session = Session.load(sk)
    if not session:
        print "Invalid session"
        return "NOPE"

    doc, tag, text = Doc().tagtext()
    with tag('lfm', status="ok"):
        with tag('user'):
            with tag('name'):
                text(session.user.name)
            with tag('realname'):
                text(session.user.name)
            with tag('url'):
                text('http://foo.bar/user/' + session.user.name)
            with tag('playcount'):
                text('9001')
            with tag('registered', unixtime=str(time)):
                text(session.user.timestamp)

    return format_response('<?xml version="1.0" encoding="utf-8"?>\n' + yattag.indent(doc.getvalue()),
                           data.get('format', "xml"))
