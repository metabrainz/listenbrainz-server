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
from webserver.rate_limiter import ratelimit
from webserver.errors import InvalidAPIUsage
import xmltodict

from api_tools import _send_listens_to_kafka, _get_augumented_listens
from db.mockdata import User, Session, Token

staticuser = "armalcolite"
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
    """ Receives the GET-API calls and redirects them to appropriate methods.
    """
    method = request.args['method'].lower()
    return {
        'user.getinfo': user_info,
        'auth.gettoken': get_token,
        'auth.getsessioninfo': get_session_info
    }.get(method, invalid_method_error)(request, request.args)


@api_bp.route('/2.0/', methods=['POST'])
@ratelimit()
def api_post():
    """ Receives the POST-API calls and redirects them to appropriate methods.
    """
    method = request.form['method'].lower()
    return {
        'track.updatenowplaying': now_playing,
        'track.scrobble': scrobble,
        'auth.getsession': get_session,
        'user.getinfo': user_info
    }.get(method, invalid_method_error)(request, request.form)


def invalid_method_error(request, data):
    """ Return error for invalid method name """
    raise InvalidAPIUsage(3, output_format=data.get('format', "xml"))


def get_token(request, data):
    """ Issue a token to user after verying his API_KEY
    """
    output_format = data.get("format", "xml")
    api_key = data.get('api_key', None)

    if not api_key:
        raise InvalidAPIUsage(6, output_format=output_format)   # Missing required params
    if not Token.is_valid_api_key(api_key):
        raise InvalidAPIUsage(10, output_format=output_format)   # Invalid API_KEY

    token = Token.generate(api_key)

    doc, tag, text = Doc().tagtext()
    with tag('lfm', status="ok"):
        with tag('token'):
            text(token.token)
    return format_response('<?xml version="1.0" encoding="utf-8"?>\n' + yattag.indent(doc.getvalue()),
                           output_format)


# NEEDS MORE WORK !!
# Validate API Key
def get_session(request, data):
    """ Create new session
    """
    output_format = data.get("format", "xml")
    try:
        api_key = data['api_key']
        token = Token.load(data['token'])
    except KeyError:
        raise InvalidAPIUsage(6, output_format=output_format)   # Missing Required Params

    if not token:
        raise InvalidAPIUsage(4, output_format=output_format)   # Invalid token

    if not token.user:
        raise InvalidAPIUsage(14, output_format=output_format)   # Unauthorized token

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
    """ Converts the list of listens to the native API format
    """
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
    """ Submit the listen in the lastfm format to be inserted in db.
    """
    sk = data['sk']
    output_format = data.get('format', "xml")
    session = Session.load(sk)
    if not session:
        raise InvalidAPIUsage(9, output_format=output_format)   # Invalid Session

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
