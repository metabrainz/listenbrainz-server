import datetime
from urllib.parse import urlparse
from uuid import UUID

import bleach
import ujson
from flask import Blueprint, current_app, jsonify, request
import requests
import listenbrainz.db.playlist as db_playlist
import listenbrainz.db.user as db_user

from listenbrainz.webserver.decorators import crossdomain, api_listenstore_needed
from listenbrainz.webserver.errors import APIBadRequest, APIInternalServerError, APINotFound, APIForbidden
from brainzutils.ratelimit import ratelimit
from listenbrainz.webserver.views.api_tools import log_raise_400, is_valid_uuid, validate_auth_header, \
    _filter_description_html
from listenbrainz.db.model.playlist import Playlist, WritablePlaylist, WritablePlaylistRecording

playlist_api_bp = Blueprint('playlist_api_v1', __name__)

PLAYLIST_TRACK_URI_PREFIX = "https://musicbrainz.org/recording/"
PLAYLIST_ARTIST_URI_PREFIX = "https://musicbrainz.org/artist/"
PLAYLIST_RELEASE_URI_PREFIX = "https://musicbrainz.org/release/"
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


def validate_create_playlist_required_items(jspf):
    """Given a JSPF dict, ensure that the title and public fields are present.
    These fields are required only when creating a new playlist"""

    if "playlist" not in jspf:
        log_raise_400("JSPF playlist requires 'playlist' element")

    if "title" not in jspf["playlist"]:
        log_raise_400("JSPF playlist must contain a title element with the title of the playlist.")

    if "public" not in jspf["playlist"].get("extension", {}).get(PLAYLIST_EXTENSION_URI, {}):
        log_raise_400("JSPF playlist.extension.https://musicbrainz.org/doc/jspf#playlist.public field must be given.")


def validate_playlist(jspf):
    """
        Given a JSPF dict, ensure that title is present and that if tracks are present
        they have valid URIs or MBIDs specified. If any errors are found 400 is raised.
    """

    if "playlist" not in jspf:
        log_raise_400("JSPF playlist requires 'playlist' element")

    if "title" in jspf["playlist"]:
        title = jspf["playlist"]["title"]
        if not title:
            log_raise_400("JSPF playlist must contain a title element with the title of the playlist.")

    if "public" in jspf["playlist"].get("extension", {}).get(PLAYLIST_EXTENSION_URI, {}):
        public = jspf["playlist"]["extension"][PLAYLIST_EXTENSION_URI]["public"]
        if not isinstance(public, bool):
            log_raise_400("JSPF playlist public field must contain a boolean.")

    try:
        # Collaborators are not required, so only validate if they are set
        for collaborator in jspf["playlist"]["extension"][PLAYLIST_EXTENSION_URI]["collaborators"]:
            if not collaborator:
                log_raise_400("The collaborators field contains an empty value.")
    except KeyError:
        pass

    if "track" not in jspf["playlist"]:
        return

    for i, track in enumerate(jspf["playlist"].get("track", [])):
        recording_uri = track.get("identifier")
        if not recording_uri:
            log_raise_400("JSPF playlist track %d must contain an identifier element with recording MBID." % i)

        if recording_uri.startswith(PLAYLIST_TRACK_URI_PREFIX):
            recording_mbid = recording_uri[len(PLAYLIST_TRACK_URI_PREFIX):]
        else:
            log_raise_400("JSPF playlist track %d identifier must have the namespace '%s' prepended to it." %
                          (i, PLAYLIST_TRACK_URI_PREFIX))

        if not is_valid_uuid(recording_mbid):
            log_raise_400("JSPF playlist track %d does not contain a valid track identifier field." % i)


def serialize_jspf(playlist: Playlist):
    """
        Given a playlist, return a properly formated dict that can be passed to jsonify.
    """

    pl = {"creator": playlist.creator,
          "title": playlist.name,
          "identifier": PLAYLIST_URI_PREFIX + str(playlist.mbid),
          "date": playlist.created.astimezone(datetime.timezone.utc).isoformat()
    }
    if playlist.description:
        pl["annotation"] = playlist.description

    extension = {"public": playlist.public, "creator": playlist.creator}
    if playlist.last_updated:
        extension["last_modified_at"] = playlist.last_updated.astimezone(datetime.timezone.utc).isoformat()
    if playlist.copied_from_id is not None:
        if playlist.copied_from_mbid is None:
            extension['copied_from_deleted'] = True
        else:
            extension['copied_from_mbid'] = PLAYLIST_URI_PREFIX + str(playlist.copied_from_mbid)
    if playlist.created_for_id:
        extension['created_for'] = playlist.created_for
    if playlist.collaborators:
        extension['collaborators'] = playlist.collaborators

    pl["extension"] = {PLAYLIST_EXTENSION_URI: extension}

    tracks = []
    for rec in playlist.recordings:
        tr = {"identifier": PLAYLIST_TRACK_URI_PREFIX + str(rec.mbid)}
        if rec.artist_credit:
            tr["creator"] = rec.artist_credit

        if rec.release_name:
            tr["album"] = rec.release_name

        if rec.title:
            tr["title"] = rec.title

        extension = {"added_by": rec.added_by,
                     "added_at": rec.created.astimezone(datetime.timezone.utc).isoformat()}
        if rec.artist_mbids:
            extension["artist_identifier"] = [PLAYLIST_ARTIST_URI_PREFIX + str(mbid) for mbid in rec.artist_mbids]

        if rec.release_mbid:
            extension["release_identifier"] = PLAYLIST_RELEASE_URI_PREFIX + str(rec.release_mbid)

        tr["extension"] = {PLAYLIST_TRACK_EXTENSION_URI: extension}
        tracks.append(tr)

    pl["track"] = tracks

    return {"playlist": pl}


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


def fetch_playlist_recording_metadata(playlist: Playlist):
    """
        This interim function will soon be replaced with a more complete service layer
    """

    mbids = [{'[recording_mbid]': str(item.mbid)} for item in playlist.recordings]
    if not mbids:
        return

    r = requests.post(RECORDING_LOOKUP_SERVER_URL, params={"count": len(mbids)}, json=mbids)
    if r.status_code != 200:
        current_app.logger.error("Error while fetching metadata for a playlist: %d" % r.status_code)
        raise APIInternalServerError("Failed to fetch metadata for a playlist. Please try again.")

    try:
        rows = ujson.loads(r.text)
    except ValueError as err:
        current_app.logger.error("Error parse metadata for a playlist: {}".format(err))
        raise APIInternalServerError("Failed parse fetched metadata for a playlist. Please try again.")

    mbid_index = {}
    for row in rows:
        mbid_index[row['original_recording_mbid']] = row

    for rec in playlist.recordings:
        try:
            row = mbid_index[str(rec.mbid)]
        except KeyError:
            continue

        rec.artist_credit = row.get("artist_credit_name", "")
        if "[artist_credit_mbids]" in row and not row["[artist_credit_mbids]"] is None:
            rec.artist_mbids = [UUID(mbid) for mbid in row["[artist_credit_mbids]"]]
        rec.title = row.get("recording_name", "")


@playlist_api_bp.route("/create", methods=["POST", "OPTIONS"])
@crossdomain(headers="Authorization, Content-Type")
@ratelimit()
@api_listenstore_needed
def create_playlist():
    """
    Create a playlist. The playlist must be in JSPF format with MusicBrainz extensions, which is defined
    here: https://musicbrainz.org/doc/jspf . To create an empty playlist, you can send an empty playlist
    with only the title field filled out. If you would like to create a playlist populated with recordings,
    each of the track items in the playlist must have an identifier element that contains the MusicBrainz
    recording that includes the recording MBID.

    When creating a playlist, only the playlist title and the track identifier elements will be used -- all
    other elements in the posted JSPF wil be ignored.

    If a created_for field is found and the user is not an approved playlist bot, then a 403 forbidden will be raised.

    :reqheader Authorization: Token <user token>
    :statuscode 200: playlist accepted.
    :statuscode 400: invalid JSON sent, see error message for details.
    :statuscode 401: invalid authorization. See error message for details.
    :statuscode 403: forbidden. The submitting user is not allowed to create playlists for other users.
    :resheader Content-Type: *application/json*
    """

    user = validate_auth_header()

    data = request.json
    validate_create_playlist_required_items(data)
    validate_playlist(data)

    public = data["playlist"]["extension"][PLAYLIST_EXTENSION_URI]["public"]
    collaborators = data.get("playlist", {}).\
        get("extension", {}).get(PLAYLIST_EXTENSION_URI, {}).\
        get("collaborators", [])

    # Uniquify collaborators list
    collaborators = list(set(collaborators))

    # Don't allow creator to also be a collaborator
    if user["musicbrainz_id"] in collaborators:
        collaborators.remove(user["musicbrainz_id"])

    username_lookup = collaborators
    created_for = data["playlist"].get("created_for", None)
    if created_for:
        username_lookup.append(created_for)

    users = {}
    if username_lookup:
        users = db_user.get_many_users_by_mb_id(username_lookup)

    collaborator_ids = []
    for collaborator in collaborators:
        if collaborator.lower() not in users:
            log_raise_400("Collaborator {} doesn't exist".format(collaborator))
        collaborator_ids.append(users[collaborator.lower()]["id"])

    # filter description
    description = data["playlist"].get("annotation", None)
    if description is not None:
        description = _filter_description_html(description)

    playlist = WritablePlaylist(name=data['playlist']['title'],
                                creator_id=user["id"],
                                description=description,
                                collaborator_ids=collaborator_ids,
                                collaborators=collaborators,
                                public=public)

    if data["playlist"].get("created_for", None):
        if user["musicbrainz_id"] not in current_app.config["APPROVED_PLAYLIST_BOTS"]:
            raise APIForbidden("Playlist contains a created_for field, but submitting user is not an approved playlist bot.")
        created_for_user = users.get(data["playlist"]["created_for"].lower())
        if not created_for_user:
            log_raise_400("created_for user does not exist.")
        playlist.created_for_id = created_for_user["id"]

    if "track" in data["playlist"]:
        for track in data["playlist"]["track"]:
            try:
                playlist.recordings.append(WritablePlaylistRecording(mbid=UUID(track['identifier'][len(PLAYLIST_TRACK_URI_PREFIX):]),
                                           added_by_id=user["id"]))
            except ValueError:
                log_raise_400("Invalid recording MBID found in submitted recordings")

    try:
        playlist = db_playlist.create(playlist)
    except Exception as e:
        current_app.logger.error("Error while creating new playlist: {}".format(e))
        raise APIInternalServerError("Failed to create the playlist. Please try again.")

    return jsonify({'status': 'ok', 'playlist_mbid': playlist.mbid})


@playlist_api_bp.route("/edit/<playlist_mbid>", methods=["POST", "OPTIONS"])
@crossdomain(headers="Authorization, Content-Type")
@ratelimit()
@api_listenstore_needed
def edit_playlist(playlist_mbid):
    """
    Edit the private/public status, name, description or list of collaborators for an exising playlist.
    The Authorization header must be set and correspond to the owner of the playlist otherwise a 403
    error will be returned. All fields will be overwritten with new values.

    :reqheader Authorization: Token <user token>
    :statuscode 200: playlist accepted.
    :statuscode 400: invalid JSON sent, see error message for details.
    :statuscode 401: invalid authorization. See error message for details.
    :statuscode 403: forbidden. The subitting user is not allowed to edit playlists for other users.
    :resheader Content-Type: *application/json*
    """

    user = validate_auth_header()

    data = request.json
    validate_playlist(data)

    if not is_valid_uuid(playlist_mbid):
        log_raise_400("Provided playlist ID is invalid.")

    playlist = db_playlist.get_by_mbid(playlist_mbid, False)
    if playlist is None or not playlist.is_visible_by(user["id"]):
        raise APINotFound("Cannot find playlist: %s" % playlist_mbid)

    if playlist.creator_id != user["id"]:
        raise APIForbidden("You are not allowed to edit this playlist.")

    try:
        playlist.public = data["playlist"]["extension"][PLAYLIST_EXTENSION_URI]["public"]
    except KeyError:
        pass

    if "annotation" in data["playlist"]:
        # If the annotation key exists but the value is empty ("" or None),
        # unset the description
        description = data["playlist"]["annotation"]
        if description:
            description = _filter_description_html(description)
        else:
            description = None
        playlist.description = description

    if data["playlist"].get("title"):
        playlist.name = data["playlist"]["title"]

    collaborators = data.get("playlist", {}).\
        get("extension", {}).get(PLAYLIST_EXTENSION_URI, {}).\
        get("collaborators", [])
    users = {}

    # Uniquify collaborators list
    collaborators = list(set(collaborators))

    # Don't allow creator to also be a collaborator
    if user["musicbrainz_id"] in collaborators:
        collaborators.remove(user["musicbrainz_id"])

    if collaborators:
        users = db_user.get_many_users_by_mb_id(collaborators)

    collaborator_ids = []
    for collaborator in collaborators:
        if collaborator.lower() not in users:
            log_raise_400("Collaborator {} doesn't exist".format(collaborator))
        collaborator_ids.append(users[collaborator.lower()]["id"])

    playlist.collaborators = collaborators
    playlist.collaborator_ids = collaborator_ids

    db_playlist.update_playlist(playlist)

    return jsonify({'status': 'ok'})


@playlist_api_bp.route("/<playlist_mbid>", methods=["GET", "OPTIONS"])
@crossdomain(headers="Authorization, Content-Type")
@ratelimit()
@api_listenstore_needed
def get_playlist(playlist_mbid):
    """
    Fetch the given playlist.

    :param playlist_mbid: The playlist mbid to fetch.
    :type playlist_mbid: ``str``
    :param fetch_metadata: Optional, pass value 'false' to skip lookup up recording metadata
    :type fetch_metadata: ``bool``
    :statuscode 200: Yay, you have data!
    :statuscode 404: Playlist not found
    :statuscode 401: Invalid authorization. See error message for details.
    :resheader Content-Type: *application/json*
    """

    if not is_valid_uuid(playlist_mbid):
        log_raise_400("Provided playlist ID is invalid.")

    fetch_metadata = _parse_boolean_arg("fetch_metadata", True)

    playlist = db_playlist.get_by_mbid(playlist_mbid, True)
    if playlist is None:
        raise APINotFound("Cannot find playlist: %s" % playlist_mbid)

    user = validate_auth_header(optional=True)
    user_id = None
    if user:
        user_id = user["id"]
    if not playlist.is_visible_by(user_id):
        raise APINotFound("Cannot find playlist: %s" % playlist_mbid)

    if fetch_metadata:
        fetch_playlist_recording_metadata(playlist)

    return jsonify(serialize_jspf(playlist))


@playlist_api_bp.route("/<playlist_mbid>/item/add/<int:offset>", methods=["POST", "OPTIONS"])
@playlist_api_bp.route("/<playlist_mbid>/item/add", methods=["POST", "OPTIONS"], defaults={'offset': None})
@crossdomain(headers="Authorization, Content-Type")
@ratelimit()
@api_listenstore_needed
def add_playlist_item(playlist_mbid, offset):
    """
    Append recordings to an existing playlist by posting a playlist with one of more recordings in it.
    The playlist must be in JSPF format with MusicBrainz extensions, which is defined here:
    https://musicbrainz.org/doc/jspf .

    If the offset is provided in the URL, then the recordings will be added at that offset,
    otherwise they will be added at the end of the playlist.

    You may only add :data:`~webserver.views.playlist_api.MAX_RECORDINGS_PER_ADD` recordings in one
    call to this endpoint.

    :reqheader Authorization: Token <user token>
    :statuscode 200: playlist accepted.
    :statuscode 400: invalid JSON sent, see error message for details.
    :statuscode 401: invalid authorization. See error message for details.
    :statuscode 403: forbidden. the requesting user was not allowed to carry out this operation.
    :resheader Content-Type: *application/json*
    """

    user = validate_auth_header()
    if offset is not None and offset < 0:
        log_raise_400("Offset must be a positive integer.")

    if not is_valid_uuid(playlist_mbid):
        log_raise_400("Provided playlist ID is invalid.")

    playlist = db_playlist.get_by_mbid(playlist_mbid)
    if playlist is None or not playlist.is_visible_by(user["id"]):
        raise APINotFound("Cannot find playlist: %s" % playlist_mbid)

    if not playlist.is_modifiable_by(user["id"]):
        raise APIForbidden("You are not allowed to add recordings to this playlist.")

    data = request.json
    validate_playlist(data)

    if len(data["playlist"]["track"]) > MAX_RECORDINGS_PER_ADD:
        log_raise_400("You may only add max %d recordings per call." % MAX_RECORDINGS_PER_ADD)

    precordings = []
    if "track" in data["playlist"]:
        for track in data["playlist"]["track"]:
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

    return jsonify({'status': 'ok'})


@playlist_api_bp.route("/<playlist_mbid>/item/move", methods=["POST", "OPTIONS"])
@crossdomain(headers="Authorization, Content-Type")
@ratelimit()
@api_listenstore_needed
def move_playlist_item(playlist_mbid):
    """

    To move an item in a playlist, the POST data needs to specify the recording MBID and current index
    of the track to move (from), where to move it to (to) and how many tracks from that position should
    be moved (count). The format of the post data should look as follows:

    .. code-block:: json

        {
            "mbid": "<mbid>",
            "from": 3,
            "to": 4,
            "count": 2
        }

    :reqheader Authorization: Token <user token>
    :statuscode 200: move operation succeeded
    :statuscode 400: invalid JSON sent, see error message for details.
    :statuscode 401: invalid authorization. See error message for details.
    :statuscode 403: forbidden. the requesting user was not allowed to carry out this operation.
    :resheader Content-Type: *application/json*
    """

    user = validate_auth_header()

    if not is_valid_uuid(playlist_mbid):
        log_raise_400("Provided playlist ID is invalid.")

    playlist = db_playlist.get_by_mbid(playlist_mbid)
    if playlist is None or not playlist.is_visible_by(user["id"]):
        raise APINotFound("Cannot find playlist: %s" % playlist_mbid)

    if not playlist.is_modifiable_by(user["id"]):
        raise APIForbidden("You are not allowed to move recordings in this playlist.")

    data = request.json
    validate_move_data(data)

    try:
        db_playlist.move_recordings(playlist, data['from'], data['to'], data['count'])
    except Exception as e:
        current_app.logger.error("Error while moving recordings in the playlist: {}".format(e))
        raise APIInternalServerError("Failed to move recordings in the playlist. Please try again.")

    return jsonify({'status': 'ok'})


@playlist_api_bp.route("/<playlist_mbid>/item/delete", methods=["POST", "OPTIONS"])
@crossdomain(headers="Authorization, Content-Type")
@ratelimit()
@api_listenstore_needed
def delete_playlist_item(playlist_mbid):
    """

    To delete an item in a playlist, the POST data needs to specify the recording MBID and current index
    of the track to delete, and how many tracks from that position should be moved deleted. The format of the
    post data should look as follows:

    .. code-block:: json

        {
            "index": 3,
            "count": 2
        }

    :reqheader Authorization: Token <user token>
    :statuscode 200: playlist accepted.
    :statuscode 400: invalid JSON sent, see error message for details.
    :statuscode 401: invalid authorization. See error message for details.
    :statuscode 403: forbidden. the requesting user was not allowed to carry out this operation.
    :resheader Content-Type: *application/json*
    """

    user = validate_auth_header()

    if not is_valid_uuid(playlist_mbid):
        log_raise_400("Provided playlist ID is invalid.")

    playlist = db_playlist.get_by_mbid(playlist_mbid)
    if playlist is None or not playlist.is_visible_by(user["id"]):
        raise APINotFound("Cannot find playlist: %s" % playlist_mbid)

    if not playlist.is_modifiable_by(user["id"]):
        raise APIForbidden("You are not allowed to remove recordings from this playlist.")

    data = request.json
    validate_delete_data(data)

    try:
        db_playlist.delete_recordings_from_playlist(playlist, data['index'], data['count'])
    except Exception as e:
        current_app.logger.error("Error while deleting recordings from playlist: {}".format(e))
        raise APIInternalServerError("Failed to deleting recordings from the playlist. Please try again.")

    return jsonify({'status': 'ok'})


@playlist_api_bp.route("/<playlist_mbid>/delete", methods=["POST", "OPTIONS"])
@crossdomain(headers="Authorization, Content-Type")
@ratelimit()
@api_listenstore_needed
def delete_playlist(playlist_mbid):
    """

    Delete a playlist. POST body data does not need to contain anything.

    :reqheader Authorization: Token <user token>
    :statuscode 200: playlist deleted.
    :statuscode 401: invalid authorization. See error message for details.
    :statuscode 403: forbidden. the requesting user was not allowed to carry out this operation.
    :statuscode 404: Playlist not found
    :resheader Content-Type: *application/json*
    """

    user = validate_auth_header()

    if not is_valid_uuid(playlist_mbid):
        log_raise_400("Provided playlist ID is invalid.")

    playlist = db_playlist.get_by_mbid(playlist_mbid)
    if playlist is None or not playlist.is_visible_by(user["id"]):
        raise APINotFound("Cannot find playlist: %s" % playlist_mbid)

    if playlist.creator_id != user["id"]:
        raise APIForbidden("You are not allowed to delete this playlist.")

    try:
        db_playlist.delete_playlist(playlist)
    except Exception as e:
        current_app.logger.error("Error deleting playlist: {}".format(e))
        raise APIInternalServerError("Failed to delete the playlist. Please try again.")

    return jsonify({'status': 'ok'})


@playlist_api_bp.route("/<playlist_mbid>/copy", methods=["POST", "OPTIONS"])
@crossdomain(headers="Authorization, Content-Type")
@ratelimit()
@api_listenstore_needed
def copy_playlist(playlist_mbid):
    """

    Copy a playlist -- the new playlist will be given the name "Copy of <playlist_name>".
    POST body data does not need to contain anything.

    :reqheader Authorization: Token <user token>
    :statuscode 200: playlist copied.
    :statuscode 401: invalid authorization. See error message for details.
    :statuscode 404: Playlist not found
    :resheader Content-Type: *application/json*
    """

    user = validate_auth_header()

    if not is_valid_uuid(playlist_mbid):
        log_raise_400("Provided playlist ID is invalid.")

    playlist = db_playlist.get_by_mbid(playlist_mbid)
    if playlist is None or not playlist.is_visible_by(user["id"]):
        raise APINotFound("Cannot find playlist: %s" % playlist_mbid)

    try:
        new_playlist = db_playlist.copy_playlist(playlist, user["id"])
    except Exception as e:
        current_app.logger.error("Error copying playlist: {}".format(e))
        raise APIInternalServerError("Failed to copy the playlist. Please try again.")

    return jsonify({'status': 'ok', 'playlist_mbid': new_playlist.mbid})
