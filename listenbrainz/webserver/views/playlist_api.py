from uuid import UUID
from flask import Blueprint, current_app, jsonify, request
#import listenbrainz.db.user as db_user
import listenbrainz.db.playlist as db_playlist

from listenbrainz.webserver.decorators import crossdomain
from listenbrainz.webserver.errors import (APIBadRequest,
                                           APIInternalServerError, APINotFound)
from listenbrainz.webserver.rate_limiter import ratelimit
from listenbrainz.webserver.views.api import _validate_auth_header
from listenbrainz.webserver.views.api_tools import log_raise_400, is_valid_uuid
from listenbrainz.db.model.playlist import Playlist, WritablePlaylist, WritablePlaylistRecording

playlist_api_bp = Blueprint('playlist_api_v1', __name__)

PLAYLIST_TRACK_URI_PREFIX = "https://musicbrainz.org/recording/"
MAX_RECORDINGS_PER_ADD = 100

def _parse_boolean_arg(name, default=None):
    value = request.args.get(name)
    if not value:
        return default

    value = value.lower()
    if value not in ["true", "false"]:
        raise APIBadRequest("Invalid %s argument: %s. Must be 'true' or 'false'" % (name, value))

    return True if value == "true" else False


def validate_playlist(jspf):
    """
        Given a JSPF dict, ensure that title is present and that if tracks are present
        they have valid URIs or MBIDs specified. If any errors are found 400 is raised.
    """

    try:
        title = jspf["playlist"]["title"]
        if not title:
            raise KeyError
    except KeyError:
        log_raise_400("JSPF playlist must contain a title element with the title of the playlist.")

    if 'track' not in jspf:
        return

    for i, track in enumerate(jspf['track']):
        try:
            recording_uri = track["identifier"]
            if not recording_uri:
                raise KeyError
        except KeyError:
            log_raise_400("JSPF playlist track %d must contain an identifier element with recording MBID." % i)

        if recording_uri.startswith(PLAYLIST_TRACK_URI_PREFIX):
            recording_mbid = recording_uri[len(PLAYLIST_TRACK_URI_PREFIX):]
        else:
            log_raise_400("JSPF playlist track %d identifier must have the namespace '%s' prepended to it." %
                          (i, PLAYLIST_TRACK_URI_PREFIX))

        if not is_valid_uuid(recording_mbid):
            log_raise_400("JSPF playlist track %d does not contain a valid track identifier field." % i)


def serialize_jspf(playlist: Playlist, user):
    """
        Given a playlist, return a properly formated dict that can be passed to jsonify.
    """

    pl = { "creator": user["musicbrainz_id"],
            "title": playlist.name,
            "identifier": playlist.mbid
    }

    tracks = []
    for rec in playlist.recordings:
        tracks.append({ "identifier": PLAYLIST_TRACK_URI_PREFIX + str(rec.mbid) })

    pl["track"] = tracks

    return { "playlist": pl }

def validate_move_data(data):
    """
        Check that the passed JSON for a move recordings endpoint call are valid. Raise 400 with
        error message if not.
    """

    if "mbid" not in data or "from" not in data or "to" not in data or "count" not in data:
        log_raise_400("move for a move instruction must include the keys 'from', 'to', 'count' and 'mbid'.")

    if not is_valid_uuid(data["mbid"]):
        log_raise_400("move instruction mbid is not a valid mbid.")

    try:
        from_value = int(data["from"])
        to_value = int(data["to"])
        count_value = int(data["count"])
        if from_value < 0 or to_value < 0 or count_value < 0:
            raise ValueError
    except ValueError:
        log_raise_400("move instruction values for 'from', 'to' and 'count' must all be positive integers.")


@playlist_api_bp.route("/create", methods=["POST"])
@crossdomain(headers="Authorization, Content-Type")
@ratelimit()
def create_playlist():
    """
    Create a playlist. The playlist must be in JSPF format with MusicBrainz extensions, which is defined
    here: https://musicbrainz.org/doc/jspf . To create an empty playlist, you can send an empty playlist
    with only the title field filled out. If you would like to create a playlist populated with recordings,
    each of the track items in the playlist must have the identifier element present.

    When creating a playlist, only the playlist tite and the track identifier elements will be used -- all
    other elements in the posted JSPF wil be ignored.

    :reqheader Authorization: Token <user token>
    :statuscode 200: playlist accepted.
    :statuscode 400: invalid JSON sent, see error message for details.
    :statuscode 401: invalid authorization. See error message for details.
    :resheader Content-Type: *application/json*
    """

    public = _parse_boolean_arg("public", "true")
    user = _validate_auth_header()

    data = request.json
    validate_playlist(data)

    playlist = WritablePlaylist(name=data['playlist']['title'], creator_id=user["id"])
    playlist.public = public

    if "track" in data["playlist"]:
        for track in data["playlist"]["track"]:
            playlist.recordings.append(WritablePlaylistRecording(mbid=UUID(track['identifier'][len(PLAYLIST_TRACK_URI_PREFIX):]),
                                       added_by_id=user["id"]))


    try:
        playlist = db_playlist.create(playlist)
    except Exception as e:
        current_app.logger.error("Error while creating new playlist: {}".format(e))
        raise APIInternalServerError("Failed to create the playlist. Please try again.")

    return jsonify({'status': 'ok', 'playlist_mbid': playlist.mbid })


@playlist_api_bp.route("/<playlist_mbid>", methods=["GET"])
@crossdomain()
@ratelimit()
def get_playlist(playlist_mbid):
    """
    Fetch the given playlist.

    :param playlist_mbid: Optional, The playlist mbid to fetch.
    :statuscode 200: Yay, you have data!
    :statuscode 404: Playlist not found
    :statuscode 401: Invalid authorization. See error message for details.
    :resheader Content-Type: *application/json*
    """
    user = _validate_auth_header()

    if not is_valid_uuid(playlist_mbid):
        log_raise_400("Provided playlist ID is invalid.")

    playlist = db_playlist.get_by_id(playlist_mbid, True)
    if playlist is None or \
        (playlist.creator_id != user["id"] and not playlist.public):
        raise APINotFound("Cannot find playlist: %s" % playlist_mbid)

    return jsonify(serialize_jspf(playlist, user))


@playlist_api_bp.route("/<playlist_mbid>/item/add/<int:offset>", methods=["POST"])
@playlist_api_bp.route("/<playlist_mbid>/item/add", methods=["POST"], defaults={'offset': None})
@crossdomain(headers="Authorization, Content-Type")
@ratelimit()
def add_playlist_item(playlist_mbid, offset):
    """
    Append recordings to an existing playlist by posting a playlist with one of more recordings in it.
    The playlist must be in JSPF format with MusicBrainz extensions, which is defined here:
    https://musicbrainz.org/doc/jspf .

    If the offset is provided in the URL, then the recordings will be added at that offset,
    otherwise they will be added at the end of the playlist.

    You may only add MAX_RECORDINGS_PER_ADD recordings in one call to this endpoint.

    :reqheader Authorization: Token <user token>
    :statuscode 200: playlist accepted.
    :statuscode 400: invalid JSON sent, see error message for details.
    :statuscode 401: invalid authorization. See error message for details.
    :resheader Content-Type: *application/json*
    """

    user = _validate_auth_header()
    if offset < 0:
        log_raise_400("Offset must be a positive integer.")

    if not is_valid_uuid(playlist_mbid):
        log_raise_400("Provided playlist ID is invalid.")

    data = request.json
    validate_playlist(data)

    if len(data["playlist"]["track"]) > MAX_RECORDINGS_PER_ADD:
        log_raise_400("You may only add max %d recordings per call." % MAX_RECORDINGS_PER_ADD)

    playlist = db_playlist.get_by_id(playlist_mbid)
    if playlist is None or \
        (playlist.creator_id != user["id"] and not playlist.public):
        raise APINotFound("Cannot find playlist: %s" % playlist_mbid)

    precordings = []
    if "track" in data:
        for track in data['track']:
            pr = WritablePlaylistRecording()
            pr.mbid = track['mbid']
            precordings.append(pr)

    try:
        db_playlist.add_recordings_to_playlist(playlist, precordings, offset)
    except Exception as e:
        current_app.logger.error("Error while adding recordings to playlist: {}".format(e))
        raise APIInternalServerError("Failed to add recordings to the playlist. Please try again.")

    return jsonify({'status': 'ok' })


@playlist_api_bp.route("/<playlist_mbid>/item/move", methods=["POST"])
@crossdomain(headers="Authorization, Content-Type")
@ratelimit()
def move_playlist_item(playlist_mbid):
    """

    To move an item in a playlist, the POST data needs to specify the recording MBID and current index
    of the track to move (from), where to move it to (to) and how many tracks from that position should
    be moved (count). The format of the post data should look as follows:

     { “mbid” : “<mbid>”, “from” : 3, “to” : 4, “count”: 2 } }

    :reqheader Authorization: Token <user token>
    :statuscode 200: playlist accepted.
    :statuscode 400: invalid JSON sent, see error message for details.
    :statuscode 401: invalid authorization. See error message for details.
    :resheader Content-Type: *application/json*
    """

    user = _validate_auth_header()

    if not is_valid_uuid(playlist_mbid):
        log_raise_400("Provided playlist ID is invalid.")

    data = request.json
    validate_move_data(data)

    playlist = db_playlist.get_by_id(playlist_mbid)
    if playlist is None or \
        (playlist.creator_id != user["id"] and not playlist.public):
        raise APINotFound("Cannot find playlist: %s" % playlist_mbid)

    try:
        # TODO, complete when the method becomes available
        #db_playlist.add_playlist_items(playlist, precordings, offset)
        pass
    except Exception as e:
        current_app.logger.error("Error while adding recordings to playlist: {}".format(e))
        raise APIInternalServerError("Failed to add recordings to the playlist. Please try again.")

    return jsonify({'status': 'ok' })
