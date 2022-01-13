from operator import itemgetter

import ujson
import psycopg2
from flask import Blueprint, request, jsonify, current_app
from brainzutils.musicbrainz_db import engine as mb_engine

from data.model.external_service import ExternalServiceType
from listenbrainz.webserver.errors import APIBadRequest, APIInternalServerError, APINotFound, APIServiceUnavailable, \
    APIUnauthorized, ListenValidationError
from listenbrainz.webserver.decorators import api_listenstore_needed
from listenbrainz.db.exceptions import DatabaseException
from listenbrainz.webserver.decorators import crossdomain
from listenbrainz import webserver
import listenbrainz.db.playlist as db_playlist
import listenbrainz.db.user as db_user
from listenbrainz.db import listens_importer
from brainzutils.ratelimit import ratelimit
import listenbrainz.webserver.redis_connection as redis_connection
from listenbrainz.webserver.models import SubmitListenUserMetadata
from listenbrainz.webserver.utils import REJECT_LISTENS_WITHOUT_EMAIL_ERROR
from listenbrainz.webserver.views.api_tools import insert_payload, log_raise_400, validate_listen, parse_param_list, \
    is_valid_uuid, MAX_LISTEN_SIZE, LISTEN_TYPE_SINGLE, LISTEN_TYPE_IMPORT, _validate_get_endpoint_params, \
    _parse_int_arg, LISTEN_TYPE_PLAYING_NOW, validate_auth_header, get_non_negative_param
from listenbrainz.webserver.views.playlist_api import serialize_jspf
from listenbrainz.listenstore.timescale_listenstore import TimescaleListenStoreException
from listenbrainz.webserver.timescale_connection import _ts

api_bp = Blueprint('api_v1', __name__)

DEFAULT_NUMBER_OF_PLAYLISTS_PER_CALL = 25


@api_bp.route("/submit-listens", methods=["POST", "OPTIONS"])
@crossdomain(headers="Authorization, Content-Type")
@ratelimit()
def submit_listen():
    """
    Submit listens to the server. A user token (found on  https://listenbrainz.org/profile/ ) must
    be provided in the Authorization header! Each request should also contain at least one listen
    in the payload.

    Listens should be submitted for tracks when the user has listened to half the track or 4 minutes of
    the track, whichever is lower. If the user hasn't listened to 4 minutes or half the track, it doesn't
    fully count as a listen and should not be submitted.

    For complete details on the format of the JSON to be POSTed to this endpoint, see :ref:`json-doc`.

    :reqheader Authorization: Token <user token>
    :reqheader Content-Type: *application/json*
    :statuscode 200: listen(s) accepted.
    :statuscode 400: invalid JSON sent, see error message for details.
    :statuscode 401: invalid authorization. See error message for details.
    :resheader Content-Type: *application/json*
    """
    user = validate_auth_header(fetch_email=True)
    if mb_engine and current_app.config["REJECT_LISTENS_WITHOUT_USER_EMAIL"] and not user["email"]:
        raise APIUnauthorized(REJECT_LISTENS_WITHOUT_EMAIL_ERROR)

    raw_data = request.get_data()
    try:
        data = ujson.loads(raw_data.decode("utf-8"))
    except ValueError as e:
        log_raise_400("Cannot parse JSON document: %s" % e)

    try:
        if not isinstance(data, dict):
            raise APIBadRequest("Invalid JSON document submitted. Top level of "
                                "JSON document should be a json object.")

        payload = data['payload']

        if not isinstance(payload, list):
            raise APIBadRequest("The payload in the JSON document should be a list of listens.", payload)

        if len(payload) == 0:
            log_raise_400(
                "JSON document does not contain any listens", payload)

        if len(raw_data) > len(payload) * MAX_LISTEN_SIZE:
            log_raise_400("JSON document is too large. In aggregate, listens may not "
                          "be larger than %d characters." % MAX_LISTEN_SIZE, payload)

        if data['listen_type'] not in ('playing_now', 'single', 'import'):
            log_raise_400(
                "JSON document requires a valid listen_type key.", payload)

        listen_type = _get_listen_type(data['listen_type'])
        if (listen_type == LISTEN_TYPE_SINGLE or listen_type == LISTEN_TYPE_PLAYING_NOW) and len(payload) > 1:
            log_raise_400("JSON document contains more than listen for a single/playing_now. "
                          "It should contain only one.", payload)
    except KeyError:
        log_raise_400("Invalid JSON document submitted.", raw_data)

    try:
        # validate listens to make sure json is okay
        validated_payload = [validate_listen(listen, listen_type) for listen in payload]
    except ListenValidationError as err:
        raise APIBadRequest(err.message, err.payload)

    user_metadata = SubmitListenUserMetadata(user_id=user['id'], musicbrainz_id=user['musicbrainz_id'])
    insert_payload(validated_payload, user_metadata, listen_type)

    return jsonify({'status': 'ok'})


@api_bp.route("/user/<user_name>/listens")
@crossdomain()
@ratelimit()
@api_listenstore_needed
def get_listens(user_name):
    """
    Get listens for user ``user_name``. The format for the JSON returned is defined in our :ref:`json-doc`.

    If none of the optional arguments are given, this endpoint will return the :data:`~webserver.views.api.DEFAULT_ITEMS_PER_GET` most recent listens.
    The optional ``max_ts`` and ``min_ts`` UNIX epoch timestamps control at which point in time to start returning listens. You may specify max_ts or
    min_ts, but not both in one call. Listens are always returned in descending timestamp order.

    :param max_ts: If you specify a ``max_ts`` timestamp, listens with listened_at less than (but not including) this value will be returned.
    :param min_ts: If you specify a ``min_ts`` timestamp, listens with listened_at greater than (but not including) this value will be returned.
    :param count: Optional, number of listens to return. Default: :data:`~webserver.views.api.DEFAULT_ITEMS_PER_GET` . Max: :data:`~webserver.views.api.MAX_ITEMS_PER_GET`
    :statuscode 200: Yay, you have data!
    :statuscode 404: The requested user was not found.
    :resheader Content-Type: *application/json*
    """
    db_conn = webserver.create_timescale(current_app)

    user = db_user.get_by_mb_id(user_name)
    if user is None:
        raise APINotFound("Cannot find user: %s" % user_name)

    min_ts, max_ts, count = _validate_get_endpoint_params()
    if min_ts and max_ts and min_ts >= max_ts:
        raise APIBadRequest("min_ts should be less than max_ts")

    listens, _, max_ts_per_user = db_conn.fetch_listens(
        user["id"],
        limit=count,
        from_ts=min_ts,
        to_ts=max_ts
    )
    listen_data = []
    for listen in listens:
        listen_data.append(listen.to_api())

    return jsonify({'payload': {
        'user_id': user_name,
        'count': len(listen_data),
        'listens': listen_data,
        'latest_listen_ts': max_ts_per_user,
    }})


@api_bp.route("/user/<user_name>/listen-count")
@crossdomain()
@ratelimit()
@api_listenstore_needed
def get_listen_count(user_name):
    """
        Get the number of listens for a user ``user_name``.

        The returned listen count has an element 'payload' with only key: 'count'
        which unsurprisingly contains the listen count for the user.

    :statuscode 200: Yay, you have listen counts!
    :statuscode 404: The requested user was not found.
    :resheader Content-Type: *application/json*
    """
    user = db_user.get_by_mb_id(user_name)
    if user is None:
        raise APINotFound("Cannot find user: %s" % user_name)

    try:
        db_conn = webserver.create_timescale(current_app)
        listen_count = db_conn.get_listen_count_for_user(user["id"])
    except psycopg2.OperationalError as err:
        current_app.logger.error("cannot fetch user listen count: ", str(err))
        raise APIServiceUnavailable(
            "Cannot fetch user listen count right now.")

    return jsonify({'payload': {
        'count': listen_count
    }})


@api_bp.route("/user/<user_name>/playing-now")
@crossdomain()
@ratelimit()
def get_playing_now(user_name):
    """
    Get the listen being played right now for user ``user_name``.

    This endpoint returns a JSON document with a single listen in the same format as the ``/user/<user_name>/listens`` endpoint,
    with one key difference, there will only be one listen returned at maximum and the listen will not contain a ``listened_at`` element.

    The format for the JSON returned is defined in our :ref:`json-doc`.

    :statuscode 200: Yay, you have data!
    :statuscode 404: The requested user was not found.
    :resheader Content-Type: *application/json*
    """

    user = db_user.get_by_mb_id(user_name)
    if user is None:
        raise APINotFound("Cannot find user: %s" % user_name)

    playing_now_listen = redis_connection._redis.get_playing_now(user['id'])
    listen_data = []
    count = 0
    if playing_now_listen:
        count = 1
        listen_data = [playing_now_listen.to_api()]

    return jsonify({
        'payload': {
            'count': count,
            'user_id': user_name,
            'playing_now': True,
            'listens': listen_data,
        },
    })


@api_bp.route("/users/<user_list>/recent-listens")
@crossdomain(headers='Authorization, Content-Type')
@ratelimit()
@api_listenstore_needed
def get_recent_listens_for_user_list(user_list):
    """
    Fetch the most recent listens for a comma separated list of users. Take care to properly HTTP escape
    user names that contain commas!

    .. note::

        This is a bulk lookup endpoint. Hence, any non-existing users in the list will be simply ignored
        without raising any error.

    :statuscode 200: Fetched listens successfully.
    :statuscode 400: Your user list was incomplete or otherwise invalid.
    :resheader Content-Type: *application/json*
    """

    limit = _parse_int_arg("limit", 2)
    users = parse_param_list(user_list)
    if not len(users):
        raise APIBadRequest("user_list is empty or invalid.")

    db_conn = webserver.create_timescale(current_app)
    users = db_user.get_many_users_by_mb_id(users)
    user_ids = [user["id"] for user in users.values()]
    listens = db_conn.fetch_recent_listens_for_users(user_ids, limit=limit)

    listen_data = []
    for listen in listens:
        listen_data.append(listen.to_api())

    return jsonify({'payload': {
        'user_list': user_list,
        'count': len(listen_data),
        'listens': listen_data,
    }})


@api_bp.route("/user/<user_name>/similar-users", methods=['GET', 'OPTIONS'])
@crossdomain(headers='Content-Type')
@ratelimit()
def get_similar_users(user_name):
    """
    Get list of users who have similar music tastes (based on their listen history)
    for a given user. Returns an array of dicts like these:

    .. code-block:: json

        {
            "user_name": "hwnrwx",
            "similarity": 0.1938480256
        }

    :param user_name: the MusicBrainz ID of the user whose similar users are being requested.
    :statuscode 200: Yay, you have data!
    :resheader Content-Type: *application/json*
    :statuscode 404: The requested user was not found.
    """

    user = db_user.get_by_mb_id(user_name)
    if not user:
        raise APINotFound("User %s not found" % user_name)

    similar_users = db_user.get_similar_users(user['id'])
    if not similar_users:
        return jsonify({'payload': []})

    response = []
    for user_name in similar_users.similar_users:
        response.append({
            'user_name': user_name,
            'similarity': similar_users.similar_users[user_name]
        })
    return jsonify({'payload': sorted(response, key=itemgetter('similarity'), reverse=True)})


@api_bp.route("/user/<user_name>/similar-to/<other_user_name>", methods=['GET', 'OPTIONS'])
@crossdomain(headers='Content-Type')
@ratelimit()
def get_similar_to_user(user_name, other_user_name):
    """
    Get the similarity of the user and the other user, based on their listening history.
    Returns a single dict:

    .. code-block:: json

        {
            "user_name": "other_user",
            "similarity": 0.1938480256
        }

    :param user_name: the MusicBrainz ID of the the one user
    :param other_user_name: the MusicBrainz ID of the other user whose similar users are
    :statuscode 200: Yay, you have data!
    :resheader Content-Type: *application/json*
    :statuscode 404: The requested user was not found.
    """
    user = db_user.get_by_mb_id(user_name)
    if not user:
        raise APINotFound("User %s not found" % user_name)

    similar_users = db_user.get_similar_users(user['id'])
    try:
        return jsonify({'payload': {"user_name": other_user_name, "similarity": similar_users.similar_users[other_user_name]}})
    except KeyError:
        raise APINotFound("Similar-to user not found")


@api_bp.route('/latest-import', methods=['GET', 'POST', 'OPTIONS'])
@crossdomain(headers='Authorization, Content-Type')
@ratelimit()
def latest_import():
    """
    Get and update the timestamp of the newest listen submitted in previous imports to ListenBrainz.

    In order to get the timestamp for a user, make a GET request to this endpoint. The data returned will
    be JSON of the following format:

    .. code-block:: json

        {
            "musicbrainz_id": "the MusicBrainz ID of the user",
            "latest_import": "the timestamp of the newest listen submitted in previous imports. Defaults to 0"
        }

    :param user_name: the MusicBrainz ID of the user whose data is needed
    :type user_name: ``str``
    :statuscode 200: Yay, you have data!
    :resheader Content-Type: *application/json*

    In order to update the timestamp of a user, you'll have to provide a user token in the Authorization
    Header. User tokens can be found on https://listenbrainz.org/profile/ .

    The JSON that needs to be posted must contain a field named `ts` in the root with a valid unix timestamp.

    :reqheader Authorization: Token <user token>
    :reqheader Content-Type: *application/json*
    :statuscode 200: latest import timestamp updated
    :statuscode 400: invalid JSON sent, see error message for details.
    :statuscode 401: invalid authorization. See error message for details.
    :statuscode 404: user or service not found. See error message for details.
    """
    if request.method == 'GET':
        user_name = request.args.get('user_name', '')
        service_name = request.args.get('service', 'lastfm')
        try:
            service = ExternalServiceType[service_name.upper()]
        except KeyError:
            raise APINotFound("Service does not exist: {}".format(service_name))
        user = db_user.get_by_mb_id(user_name)
        if user is None:
            raise APINotFound("Cannot find user: {user_name}".format(user_name=user_name))
        latest_import_ts = listens_importer.get_latest_listened_at(user["id"], service)
        return jsonify({
            'musicbrainz_id': user['musicbrainz_id'],
            'latest_import': 0 if not latest_import_ts else int(latest_import_ts.strftime('%s'))
        })
    elif request.method == 'POST':
        user = validate_auth_header()

        try:
            data = ujson.loads(request.get_data())
            ts = int(data.get('ts', 0))
            service_name = data.get('service', 'lastfm')
            service = ExternalServiceType[service_name.upper()]
        except (ValueError, KeyError):
            raise APIBadRequest('Invalid data sent')

        try:
            last_import_ts = listens_importer.get_latest_listened_at(user["id"], service)
            last_import_ts = 0 if not last_import_ts else int(last_import_ts.strftime('%s'))
            if ts > last_import_ts:
                listens_importer.update_latest_listened_at(user["id"], service, ts)
        except DatabaseException:
            current_app.logger.error("Error while updating latest import: ", exc_info=True)
            raise APIInternalServerError('Could not update latest_import, try again')

        return jsonify({'status': 'ok'})


@api_bp.route('/validate-token', methods=['GET'])
@crossdomain(headers='Authorization')
@ratelimit()
def validate_token():
    """
    Check whether a User Token is a valid entry in the database.

    In order to query this endpoint, send a GET request with the Authorization
    header set to the value ``Token [the token value]``.

    .. note::

        This endpoint also checks for `token` argument in query params
        (example: /validate-token?token=token-to-check) if the Authorization
        header is missing for backward compatibility.

    A JSON response, with the following format, will be returned.

    - If the given token is valid:

    .. code-block:: json

        {
            "code": 200,
            "message": "Token valid.",
            "valid": true,
            "user_name": "MusicBrainz ID of the user with the passed token"
        }

    - If the given token is invalid:

    .. code-block:: json

        {
            "code": 200,
            "message": "Token invalid.",
            "valid": false,
        }

    :statuscode 200: The user token is valid/invalid.
    :statuscode 400: No token was sent to the endpoint.
    """
    header = request.headers.get('Authorization')
    if header and header.lower().startswith("token "):
        auth_token = header.split(" ")[1]
    else:
        # for backwards compatibility, check for auth token in query parameters as well
        auth_token = request.args.get('token', '')

    if not auth_token:
        raise APIBadRequest("You need to provide an Authorization token.")
    user = db_user.get_by_token(auth_token)
    if user is None:
        return jsonify({
            'code': 200,
            'message': 'Token invalid.',
            'valid': False,
        })
    else:
        return jsonify({
            'code': 200,
            'message': 'Token valid.',
            'valid': True,
            'user_name': user['musicbrainz_id'],
        })


@api_bp.route('/delete-listen', methods=['POST', 'OPTIONS'])
@crossdomain(headers="Authorization, Content-Type")
@ratelimit()
@api_listenstore_needed
def delete_listen():
    """
    Delete a particular listen from a user's listen history.
    This checks for the correct authorization token and deletes the listen.

    The format of the JSON to be POSTed to this endpoint is:

    .. code-block:: json

        {
            "listened_at": 1,
            "recording_msid": "d23f4719-9212-49f0-ad08-ddbfbfc50d6f"
        }

    :reqheader Authorization: Token <user token>
    :reqheader Content-Type: *application/json*
    :statuscode 200: listen deleted.
    :statuscode 400: invalid JSON sent, see error message for details.
    :statuscode 401: invalid authorization. See error message for details.
    :resheader Content-Type: *application/json*
    """
    user = validate_auth_header()

    data = request.json

    if "listened_at" not in data:
        log_raise_400("Listen timestamp missing.")
    try:
        listened_at = data["listened_at"]
        listened_at = int(listened_at)
    except ValueError:
        log_raise_400("%s: Listen timestamp invalid." % listened_at)

    if "recording_msid" not in data:
        log_raise_400("Recording MSID missing.")

    recording_msid = data["recording_msid"]
    if not is_valid_uuid(recording_msid):
        log_raise_400("%s: Recording MSID format invalid." % recording_msid)

    try:
        _ts.delete_listen(listened_at=listened_at, recording_msid=recording_msid,
                          user_id=user["id"], user_name=user["musicbrainz_id"])
    except TimescaleListenStoreException as e:
        current_app.logger.error("Cannot delete listen for user: %s" % str(e))
        raise APIServiceUnavailable(
            "We couldn't delete the listen. Please try again later.")
    except Exception as e:
        current_app.logger.error("Cannot delete listen for user: %s" % str(e))
        raise APIInternalServerError(
            "We couldn't delete the listen. Please try again later.")

    return jsonify({'status': 'ok'})


def serialize_playlists(playlists, playlist_count, count, offset):
    """
        Serialize the playlist metadata for the get playlists commands.
    """

    items = []
    for playlist in playlists:
        items.append(serialize_jspf(playlist))

    return {"playlists": items,
            "playlist_count": playlist_count,
            "offset": offset,
            "count": count}


@api_bp.route("/user/<playlist_user_name>/playlists", methods=["GET", "OPTIONS"])
@crossdomain(headers="Authorization, Content-Type")
@ratelimit()
def get_playlists_for_user(playlist_user_name):
    """
    Fetch playlist metadata in JSPF format without recordings for the given user.
    If a user token is provided in the Authorization header, return private playlists as well
    as public playlists for that user.

    :param count: The number of playlists to return (for pagination). Default
        :data:`~webserver.views.api.DEFAULT_NUMBER_OF_PLAYLISTS_PER_CALL`
    :type count: ``int``
    :param offset: The offset of into the list of playlists to return (for pagination)
    :type offset: ``int``
    :statuscode 200: Yay, you have data!
    :statuscode 404: User not found
    :resheader Content-Type: *application/json*
    """
    user = validate_auth_header(optional=True)

    count = get_non_negative_param(
        'count', DEFAULT_NUMBER_OF_PLAYLISTS_PER_CALL)
    offset = get_non_negative_param('offset', 0)
    playlist_user = db_user.get_by_mb_id(playlist_user_name)
    if playlist_user is None:
        raise APINotFound("Cannot find user: %s" % playlist_user_name)

    include_private = True if user and user["id"] == playlist_user["id"] else False
    playlists, playlist_count = db_playlist.get_playlists_for_user(playlist_user["id"],
                                                                   include_private=include_private,
                                                                   load_recordings=False, count=count, offset=offset)

    return jsonify(serialize_playlists(playlists, playlist_count, count, offset))


@api_bp.route("/user/<playlist_user_name>/playlists/createdfor", methods=["GET", "OPTIONS"])
@crossdomain(headers="Content-Type")
@ratelimit()
def get_playlists_created_for_user(playlist_user_name):
    """
    Fetch playlist metadata in JSPF format without recordings that have been created for the user.
    Createdfor playlists are all public, so no Authorization is needed for this call.

    :param count: The number of playlists to return (for pagination). Default
        :data:`~webserver.views.api.DEFAULT_NUMBER_OF_PLAYLISTS_PER_CALL`
    :type count: ``int``
    :param offset: The offset of into the list of playlists to return (for pagination)
    :type offset: ``int``
    :statuscode 200: Yay, you have data!
    :statuscode 404: User not found
    :resheader Content-Type: *application/json*
    """

    count = get_non_negative_param(
        'count', DEFAULT_NUMBER_OF_PLAYLISTS_PER_CALL)
    offset = get_non_negative_param('offset', 0)
    playlist_user = db_user.get_by_mb_id(playlist_user_name)
    if playlist_user is None:
        raise APINotFound("Cannot find user: %s" % playlist_user_name)

    playlists, playlist_count = db_playlist.get_playlists_created_for_user(playlist_user["id"],
                                                                           load_recordings=False, count=count, offset=offset)

    return jsonify(serialize_playlists(playlists, playlist_count, count, offset))


@api_bp.route("/user/<playlist_user_name>/playlists/collaborator", methods=["GET", "OPTIONS"])
@crossdomain(headers="Content-Type")
@ratelimit()
def get_playlists_collaborated_on_for_user(playlist_user_name):
    """
    Fetch playlist metadata in JSPF format without recordings for which a user is a collaborator.
    If a playlist is private, it will only be returned if the caller is authorized to edit that playlist.

    :param count: The number of playlists to return (for pagination). Default
        :data:`~webserver.views.api.DEFAULT_NUMBER_OF_PLAYLISTS_PER_CALL`
    :type count: ``int``
    :param offset: The offset of into the list of playlists to return (for pagination)
    :type offset: ``int``
    :statuscode 200: Yay, you have data!
    :statuscode 404: User not found
    :resheader Content-Type: *application/json*
    """

    user = validate_auth_header(optional=True)

    count = get_non_negative_param(
        'count', DEFAULT_NUMBER_OF_PLAYLISTS_PER_CALL)
    offset = get_non_negative_param('offset', 0)
    playlist_user = db_user.get_by_mb_id(playlist_user_name)
    if playlist_user is None:
        raise APINotFound("Cannot find user: %s" % playlist_user_name)

    # TODO: This needs to be passed to the DB layer
    include_private = True if user and user["id"] == playlist_user["id"] else False
    playlists, playlist_count = db_playlist.get_playlists_collaborated_on(playlist_user["id"],
                                                                          include_private=include_private,
                                                                          load_recordings=False,
                                                                          count=count,
                                                                          offset=offset)

    return jsonify(serialize_playlists(playlists, playlist_count, count, offset))


def _get_listen_type(listen_type):
    return {
        'single': LISTEN_TYPE_SINGLE,
        'import': LISTEN_TYPE_IMPORT,
        'playing_now': LISTEN_TYPE_PLAYING_NOW
    }.get(listen_type)
