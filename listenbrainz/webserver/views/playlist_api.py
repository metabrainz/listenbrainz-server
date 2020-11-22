import ujson
from uuid import UUID
import listenbrainz.db.user as db_user
import listenbrainz.db.playlist as db_playlist

from flask import Blueprint, current_app, jsonify, request
from listenbrainz.webserver.decorators import crossdomain
from listenbrainz.webserver.errors import (APIBadRequest,
                                           APIInternalServerError, APINotFound,
                                           APIServiceUnavailable,
                                           APIUnauthorized)
from listenbrainz.webserver.rate_limiter import ratelimit
from listenbrainz.webserver.views.api import _validate_auth_header, _parse_int_arg
from listenbrainz.webserver.views.api_tools import log_raise_400, is_valid_uuid,\
    DEFAULT_ITEMS_PER_GET, MAX_ITEMS_PER_GET, _get_non_negative_param, parse_param_list
from listenbrainz.db.model.playlist import Playlist, WritablePlaylist, PlaylistRecording, WritablePlaylistRecording
from pydantic import ValidationError

playlist_api_bp = Blueprint('playlist_api_v1', __name__)

PLAYLIST_TRACK_URI_PREFIX = "https://musicbrainz.org/recording/"

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
            recording_mbid = recording_uri

        try:
            uid = UUID(recording_mbid)
        except ValueError:
            log_raise_400("JSPF playlist track %d does not contain a valid track identifier field." % i)

        track['mbid'] = recording_mbid
            

def serialize_jspf(playlist: Playlist, user):
    """
        Given a playlist, return a properly formated dict that can be passed to jsonify.
    """

    pl = { "creator" : user["musicbrainz_id"],
            "title" : playlist.name
    }

    tracks = []
    for rec in playlist.recordings:
        tracks.append({ "identifier": rec.mbid })

    pl["track"] = tracks

    return { "playlist": pl }


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

    if "track" in data:
        for track in data['track']:
            pr = WritablePlaylistRecording()
            pr.mbid = track['mbid']
            playlist.recordings.append(pr)

    try:
        playlist = db_playlist.create(playlist)
    except Exception as e:
        current_app.logger.error("Error while new playlist: {}".format(e))
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

    try:
        uid = UUID(playlist_mbid)
    except ValueError:
        log_raise_400("Provided playlist ID is invalid.")

    playlist = db_playlist.get_by_id(playlist_mbid)
    if playlist is None or \
        (playlist.creator_id != user["id"] and playlist.public == False):
        raise APINotFound("Cannot find playlist: %s" % playlist_mbid)

    return jsonify(serialize_jspf(playlist, user))
