import datetime
from uuid import UUID

from flask import Blueprint, current_app, jsonify, request
import requests
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
PLAYLIST_URI_PREFIX = "https://listenbrainz.org/playlist/"
PLAYLIST_EXTENSION_URI = "https://musicbrainz.org/doc/jspf#playlist"
PLAYLIST_TRACK_EXTENSION_URI = "https://musicbrainz.org/doc/jspf#track"
RECORDING_LOOKUP_SERVER_URL = "https://labs.api.listenbrainz.org/recording-mbid-lookup/json"
MAX_RECORDINGS_PER_ADD = 100

def _parse_boolean_arg(name, default=None):
    value = request.args.get(name)
    if not value:
        return default

    value = value.lower()
    if value not in ["true", "false"]:
        raise APIBadRequest("Invalid %s argument: %s. Must be 'true' or 'false'" % (name, value))

    return True if value == "true" else False


def validate_playlist(jspf, require_title=True):
    """
        Given a JSPF dict, ensure that title is present and that if tracks are present
        they have valid URIs or MBIDs specified. If any errors are found 400 is raised.
    """

    if require_title:
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
        TODO: Add tests for newly added fields.
              Add collaborators
    """

    pl = { "creator": user["musicbrainz_id"],
            "title": playlist.name,
            "identifier": PLAYLIST_URI_PREFIX + str(playlist.mbid),
            "date": playlist.created.replace(tzinfo=datetime.timezone.utc).isoformat(),
    }
    if playlist.description:
        pl["annotation"] = playlist.description


    extension = { "public": "true" if playlist.public else "false" }
    extension["creator_id"] = playlist.creator_id
    if playlist.created_for_id:
        extension['created_for'] = playlist.created_for
    if playlist.copied_from_id:
        extension['copied_from'] = PLAYLIST_URI_PREFIX + str(playlist.copied_from_id)

    pl["extension"] = { PLAYLIST_EXTENSION_URI: extension }

    tracks = []
    for rec in playlist.recordings:
        tr = { "identifier": PLAYLIST_TRACK_URI_PREFIX + str(rec.mbid) }
        extension = { "added_by": rec.added_by,
                      "added_at": rec.created }
        tr["extension"] = { PLAYLIST_TRACK_EXTENSION_URI: extension }

        tracks.append(tr)


    pl["track"] = tracks

    return { "playlist": pl }


def validate_move_data(data):
    """
        Check that the passed JSON for a move recordings endpoint call are valid. Raise 400 with
        error message if not.
    """

    if "mbid" not in data or "from" not in data or "to" not in data or "count" not in data:
        log_raise_400("post data for a move instruction must include the keys 'from', 'to', 'count' and 'mbid'.")

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


def validate_delete_data(data):
    """
        Check that the passed JSON for a delete recordings endpoint call are valid. Raise 400 with
        error message if not.
    """

    if "index" not in data or "count" not in data:
        log_raise_400("post data for a remove instruction must include the keys 'index' and 'count'.")

    try:
        index_value = int(data["index"])
        count_value = int(data["count"])
        if index_value < 0 or count_value < 0:
            raise ValueError
    except ValueError:
        log_raise_400("move instruction values for 'index' and 'count' must all be positive integers.")


#def fetch_playlist_recording_metadata(playlist: model_playlist.Playlist):
def fetch_playlist_recording_metadata(playlist):
    """
        This interim function will soon be replaced with a more complete service layer
    """

    mbids  = [ { '[recording_mbid]': item.mbid } for item in playlist.recordings ]
    if not mbids:
        return

    r = requests.post(RECORDING_LOOKUP_SERVER_URL, count=len(mbids), json=mbids)
    if r.status_code != 200:
        current_app.logger.error("Error while fetching metadata for a playlist: {}".format(e))
        raise APIInternalServerError("Failed to fetch metadata for a playlist. Please try again.")

    try:
        rows = ujson.loads(r.text)
    except ValueError as err:
        current_app.logger.error("Error parse metadata for a playlist: {}".format(e))
        raise APIInternalServerError("Failed parse fetched metadata for a playlist. Please try again.")

    mbid_index = {}
    for row in rows:
        mbid_index[row['original_recording_mbid']] = row

    for rec in playlist.recordings:
        try:
            row = mbid_index[r.mbid]
        except KeyError:
            continue

        rec.artist_credit = row["artist_credit_id"]
        rec.artist_mbids = [ UUID(mbid) for mbid in row["[artist_credit_mbids]"] ]
        rec.release_mbid = UUID(row["release_mbid"])
        rec.release_name = row["release_name"]
        rec.title = row["recording_name"]
        rec.identifier = PLAYLIST_TRACK_URI_PREFIX + row["recording_mbid"]


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

    playlist = db_playlist.get_by_mbid(playlist_mbid, True)
    if playlist is None or \
        (playlist.creator_id != user["id"] and not playlist.public):
        raise APINotFound("Cannot find playlist: %s" % playlist_mbid)

    fetch_playlist_recording_metadata(playlist)

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
    if offset is not None and offset < 0:
        log_raise_400("Offset must be a positive integer.")

    if not is_valid_uuid(playlist_mbid):
        log_raise_400("Provided playlist ID is invalid.")

    playlist = db_playlist.get_by_mbid(playlist_mbid)
    if playlist is None or \
        (playlist.creator_id != user["id"] and not playlist.public):
        raise APINotFound("Cannot find playlist: %s" % playlist_mbid)

    data = request.json
    validate_playlist(data, False)

    if len(data["playlist"]["track"]) > MAX_RECORDINGS_PER_ADD:
        log_raise_400("You may only add max %d recordings per call." % MAX_RECORDINGS_PER_ADD)

    precordings = []
    if "track" in data["playlist"]:
        for i, track in enumerate(data["playlist"]["track"]):
            try:
                mbid = UUID(track['identifier'][len(PLAYLIST_TRACK_URI_PREFIX):])
            except (KeyError, ValueError):
                log_raise_400("Track %d has an invalid identifier field, it must be a complete URI.")
            precordings.append(WritablePlaylistRecording(mbid=mbid, added_by_id=user["id"]))

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

     { “mbid” : “<mbid>”, “from” : 3, “to” : 4, “count”: 2 }

    :reqheader Authorization: Token <user token>
    :statuscode 200: playlist accepted.
    :statuscode 400: invalid JSON sent, see error message for details.
    :statuscode 401: invalid authorization. See error message for details.
    :resheader Content-Type: *application/json*
    """

    user = _validate_auth_header()

    if not is_valid_uuid(playlist_mbid):
        log_raise_400("Provided playlist ID is invalid.")

    playlist = db_playlist.get_by_mbid(playlist_mbid)
    if playlist is None or \
        (playlist.creator_id != user["id"] and not playlist.public):
        raise APINotFound("Cannot find playlist: %s" % playlist_mbid)

    data = request.json
    validate_move_data(data)

    try:
        db_playlist.move_recordings(playlist, data['from'], data['to'], data['count'])
    except Exception as e:
        current_app.logger.error("Error while moving recordings in the playlist: {}".format(e))
        raise APIInternalServerError("Failed to move recordings in the playlist. Please try again.")

    return jsonify({'status': 'ok' })


@playlist_api_bp.route("/<playlist_mbid>/item/delete", methods=["POST"])
@crossdomain(headers="Authorization, Content-Type")
@ratelimit()
def delete_playlist_item(playlist_mbid):
    """

    To delete an item in a playlist, the POST data needs to specify the recording MBID and current index
    of the track to delete, and how many tracks from that position should be moved deleted. The format of the
    post data should look as follows:

     { “index” : 3, “count”: 2 }

    :reqheader Authorization: Token <user token>
    :statuscode 200: playlist accepted.
    :statuscode 400: invalid JSON sent, see error message for details.
    :statuscode 401: invalid authorization. See error message for details.
    :resheader Content-Type: *application/json*
    """

    user = _validate_auth_header()

    if not is_valid_uuid(playlist_mbid):
        log_raise_400("Provided playlist ID is invalid.")

    playlist = db_playlist.get_by_mbid(playlist_mbid)
    if playlist is None or \
        (playlist.creator_id != user["id"] and not playlist.public):
        raise APINotFound("Cannot find playlist: %s" % playlist_mbid)

    data = request.json
    validate_delete_data(data)

    try:
        db_playlist.delete_recordings_from_playlist(playlist, data['index'], data['count'])
    except Exception as e:
        current_app.logger.error("Error while deleting recordings from playlist: {}".format(e))
        raise APIInternalServerError("Failed to deleting recordings from the playlist. Please try again.")

    return jsonify({'status': 'ok' })


@playlist_api_bp.route("/<playlist_mbid>/delete", methods=["POST"])
@crossdomain(headers="Authorization, Content-Type")
@ratelimit()
def delete_playlist(playlist_mbid):
    """

    Delete a playlist. POST body data does not need to contain anything.

    :reqheader Authorization: Token <user token>
    :statuscode 200: playlist deleted.
    :statuscode 401: invalid authorization. See error message for details.
    :statuscode 404: Playlist not found
    :resheader Content-Type: *application/json*
    """

    user = _validate_auth_header()

    if not is_valid_uuid(playlist_mbid):
        log_raise_400("Provided playlist ID is invalid.")

    playlist = db_playlist.get_by_mbid(playlist_mbid)
    if playlist is None or \
        (playlist.creator_id != user["id"] and not playlist.public):
        raise APINotFound("Cannot find playlist: %s" % playlist_mbid)

    try:
        db_playlist.delete_playlist(playlist)
    except Exception as e:
        current_app.logger.error("Error deleting playlist: {}".format(e))
        raise APIInternalServerError("Failed to delete the playlist. Please try again.")

    return jsonify({'status': 'ok' })


@playlist_api_bp.route("/<playlist_mbid>/copy", methods=["POST"])
@crossdomain(headers="Authorization, Content-Type")
@ratelimit()
def copy_playlist(playlist_mbid):
    """

    Copy a playlist. POST body data does not need to contain anything.

    :reqheader Authorization: Token <user token>
    :statuscode 200: playlist deleted.
    :statuscode 401: invalid authorization. See error message for details.
    :statuscode 404: Playlist not found
    :resheader Content-Type: *application/json*
    """

    user = _validate_auth_header()

    if not is_valid_uuid(playlist_mbid):
        log_raise_400("Provided playlist ID is invalid.")

    playlist = db_playlist.get_by_mbid(playlist_mbid)
    if playlist is None or \
        (playlist.creator_id != user["id"] and not playlist.public):
        raise APINotFound("Cannot find playlist: %s" % playlist_mbid)

    try:
        new_playlist = db_playlist.copy_playlist(playlist, user["id"])
    except Exception as e:
        current_app.logger.error("Error deleting playlist: {}".format(e))
        raise APIInternalServerError("Failed to delete the playlist. Please try again.")

    return jsonify({'status': 'ok', 'playlist_mbid': new_playlist.mbid })
