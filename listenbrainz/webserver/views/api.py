from datetime import datetime, timezone

import psycopg2
import orjson
from brainzutils.musicbrainz_db import engine as mb_engine
from brainzutils.ratelimit import ratelimit
from flask import Blueprint, request, jsonify, current_app

import listenbrainz.db.playlist as db_playlist
import listenbrainz.db.user as db_user
import listenbrainz.db.external_service_oauth as db_external_service_oauth
import listenbrainz.webserver.redis_connection as redis_connection
from listenbrainz.db.lb_radio_artist import lb_radio_artist
from data.model.external_service import ExternalServiceType
from listenbrainz.db import listens_importer, tags
from listenbrainz.db.exceptions import DatabaseException
from listenbrainz.listenstore.timescale_listenstore import TimescaleListenStoreException
from listenbrainz.webserver import timescale_connection, db_conn, ts_conn
from listenbrainz.webserver.decorators import api_listenstore_needed
from listenbrainz.webserver.decorators import crossdomain
from listenbrainz.webserver.errors import APIBadRequest, APIInternalServerError, APINotFound, APIServiceUnavailable, \
    APIUnauthorized, ListenValidationError, APIForbidden
from listenbrainz.webserver.models import SubmitListenUserMetadata
from listenbrainz.webserver.utils import REJECT_LISTENS_WITHOUT_EMAIL_ERROR, REJECT_LISTENS_FROM_PAUSED_USER_ERROR
from listenbrainz.webserver.views.api_tools import insert_payload, log_raise_400, validate_listen, \
    is_valid_uuid, MAX_LISTEN_PAYLOAD_SIZE, MAX_LISTENS_PER_REQUEST, MAX_LISTEN_SIZE, LISTEN_TYPE_SINGLE, \
    LISTEN_TYPE_IMPORT, _validate_get_endpoint_params, LISTEN_TYPE_PLAYING_NOW, validate_auth_header, \
    get_non_negative_param, _parse_int_arg

api_bp = Blueprint('api_v1', __name__)

DEFAULT_NUMBER_OF_PLAYLISTS_PER_CALL = 25

SEARCH_USER_LIMIT = 10


@api_bp.get("/search/users/")
@crossdomain
@ratelimit()
def search_user():
    """Search a ListenBrainz-registered user.

    :param search_term: Input on which search operation is to be performed.
    """
    search_term = request.args.get("search_term")
    if search_term:
        users = db_user.search_user_name(db_conn, search_term, SEARCH_USER_LIMIT)
    else:
        users = []
    return jsonify({'users': users})


@api_bp.post("/submit-listens")
@crossdomain
@ratelimit()
def submit_listen():
    """
    Submit listens to the server. A user token (found on  https://listenbrainz.org/settings/ ) must
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
    user = validate_auth_header(fetch_email=True, scopes=["listenbrainz:submit-listens"])
    if mb_engine and current_app.config["REJECT_LISTENS_WITHOUT_USER_EMAIL"] and not user["email"]:
        raise APIUnauthorized(REJECT_LISTENS_WITHOUT_EMAIL_ERROR)

    if user['is_paused']:
        raise APIUnauthorized(REJECT_LISTENS_FROM_PAUSED_USER_ERROR)

    raw_data = request.get_data()

    if len(raw_data) > MAX_LISTEN_PAYLOAD_SIZE:
        log_raise_400(
            "Payload too large. Payload cannot exceed %s bytes" % MAX_LISTEN_PAYLOAD_SIZE
        )

    try:
        data = orjson.loads(raw_data.decode("utf-8"))
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

        if len(payload) > MAX_LISTENS_PER_REQUEST:
            log_raise_400(
                "Too many listens. You may not submit more than %s listens at once." % MAX_LISTENS_PER_REQUEST
            )

        if len(raw_data) > len(payload) * MAX_LISTEN_SIZE:
            log_raise_400("JSON document is too large. Each listens may not "
                          "be larger than %d bytes." % MAX_LISTEN_SIZE, payload)

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


@api_bp.get("/user/<user_name>/listens")
@crossdomain
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
    user = db_user.get_by_mb_id(db_conn, user_name)
    if user is None:
        raise APINotFound("Cannot find user: %s" % user_name)

    min_ts, max_ts, count = _validate_get_endpoint_params()
    if min_ts and max_ts and min_ts >= max_ts:
        raise APIBadRequest("min_ts should be less than max_ts")

    listens, min_ts_per_user, max_ts_per_user = timescale_connection._ts.fetch_listens(
        user,
        limit=count,
        from_ts=datetime.fromtimestamp(min_ts, timezone.utc) if min_ts else None,
        to_ts=datetime.fromtimestamp(max_ts, timezone.utc) if max_ts else None
    )
    listen_data = []
    for listen in listens:
        listen_data.append(listen.to_api())

    return jsonify({'payload': {
        'user_id': user_name,
        'count': len(listen_data),
        'listens': listen_data,
        'latest_listen_ts': int(max_ts_per_user.timestamp()),
        'oldest_listen_ts': int(min_ts_per_user.timestamp()),
    }})


@api_bp.get("/user/<user_name>/listen-count")
@crossdomain
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
    user = db_user.get_by_mb_id(db_conn, user_name)
    if user is None:
        raise APINotFound("Cannot find user: %s" % user_name)

    try:
        listen_count = timescale_connection._ts.get_listen_count_for_user(user["id"])
    except psycopg2.OperationalError as err:
        current_app.logger.error("cannot fetch user listen count: ", str(err))
        raise APIServiceUnavailable("Cannot fetch user listen count right now.")

    return jsonify({'payload': {
        'count': listen_count
    }})


@api_bp.get("/user/<user_name>/playing-now")
@crossdomain
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

    user = db_user.get_by_mb_id(db_conn, user_name)
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


@api_bp.get("/user/<user_name>/similar-users")
@crossdomain
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
    user = db_user.get_by_mb_id(db_conn, user_name)
    if not user:
        raise APINotFound("User %s not found" % user_name)

    similar_users = db_user.get_similar_users(db_conn, user['id'])
    return jsonify({
        "payload": [
            {
                "user_name": r["musicbrainz_id"],
                "similarity": r["similarity"]
            }
            for r in similar_users
        ]
    })


@api_bp.get("/user/<user_name>/similar-to/<other_user_name>")
@crossdomain
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
    user = db_user.get_by_mb_id(db_conn, user_name)
    if not user:
        raise APINotFound("User %s not found" % user_name)

    similar_users = db_user.get_similar_users(db_conn, user['id'])

    # Constructing an id-similarity map
    id_similarity_map = {r["musicbrainz_id"]: r["similarity"] for r in similar_users}

    try:
        return jsonify({'payload': {"user_name": other_user_name, "similarity": id_similarity_map[other_user_name]}})
    except (KeyError, AttributeError):
        raise APINotFound("Similar-to user not found")


@api_bp.route("/latest-import", methods=["GET", "POST"])
@crossdomain
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
    Header. User tokens can be found on https://listenbrainz.org/settings/ .

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
        user = db_user.get_by_mb_id(db_conn, user_name)
        if user is None:
            raise APINotFound("Cannot find user: {user_name}".format(user_name=user_name))
        latest_import_ts = listens_importer.get_latest_listened_at(db_conn, user["id"], service)
        return jsonify({
            'musicbrainz_id': user['musicbrainz_id'],
            'latest_import': 0 if not latest_import_ts else int(latest_import_ts.strftime('%s'))
        })
    elif request.method == 'POST':
        user = validate_auth_header()

        try:
            data = orjson.loads(request.get_data())
            ts = int(data.get('ts', 0))
            service_name = data.get('service', 'lastfm')
            service = ExternalServiceType[service_name.upper()]
        except (ValueError, KeyError):
            raise APIBadRequest('Invalid data sent')

        try:
            last_import_ts = listens_importer.get_latest_listened_at(db_conn, user["id"], service)
            last_import_ts = 0 if not last_import_ts else int(last_import_ts.strftime('%s'))
            if ts > last_import_ts:
                listens_importer.update_latest_listened_at(db_conn, user["id"], service, ts)
        except DatabaseException:
            current_app.logger.error("Error while updating latest import: ", exc_info=True)
            raise APIInternalServerError('Could not update latest_import, try again')

        return jsonify({'status': 'ok'})


@api_bp.get("/validate-token")
@crossdomain
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
    user = db_user.get_by_token(db_conn, auth_token)
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


@api_bp.post("/delete-listen")
@crossdomain
@ratelimit()
@api_listenstore_needed
def delete_listen():
    """
    Delete a particular listen from a user's listen history.
    This checks for the correct authorization token and deletes the listen.

    .. note::

        The listen is not deleted immediately, but is scheduled for deletion, which
        usually happens shortly after the hour.

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
        listened_at = datetime.fromtimestamp(int(data["listened_at"]), timezone.utc)
    except ValueError:
        log_raise_400("%s: Listen timestamp invalid." % data["listened_at"])

    if "recording_msid" not in data:
        log_raise_400("Recording MSID missing.")

    recording_msid = data["recording_msid"]
    if not is_valid_uuid(recording_msid):
        log_raise_400("%s: Recording MSID format invalid." % recording_msid)

    try:
        timescale_connection._ts.delete_listen(listened_at=listened_at,
                                               recording_msid=recording_msid, user_id=user["id"])
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
        items.append(playlist.serialize_jspf())

    return {"playlists": items,
            "playlist_count": playlist_count,
            "offset": offset,
            "count": count}


@api_bp.get("/user/<playlist_user_name>/playlists")
@crossdomain
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
    playlist_user = db_user.get_by_mb_id(db_conn, playlist_user_name)
    if playlist_user is None:
        raise APINotFound("Cannot find user: %s" % playlist_user_name)

    include_private = True if user and user["id"] == playlist_user["id"] else False
    playlists, playlist_count = db_playlist.get_playlists_for_user(db_conn, ts_conn, playlist_user["id"],
                                                                   include_private=include_private,
                                                                   load_recordings=False, count=count, offset=offset)

    return jsonify(serialize_playlists(playlists, playlist_count, count, offset))


@api_bp.get("/user/<playlist_user_name>/playlists/createdfor")
@crossdomain
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
    playlist_user = db_user.get_by_mb_id(db_conn, playlist_user_name)
    if playlist_user is None:
        raise APINotFound("Cannot find user: %s" % playlist_user_name)

    playlists, playlist_count = db_playlist.get_playlists_created_for_user(
        db_conn, ts_conn, playlist_user["id"], load_recordings=False, count=count, offset=offset
    )

    return jsonify(serialize_playlists(playlists, playlist_count, count, offset))


@api_bp.get("/user/<playlist_user_name>/playlists/collaborator")
@crossdomain
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
    playlist_user = db_user.get_by_mb_id(db_conn, playlist_user_name)
    if playlist_user is None:
        raise APINotFound("Cannot find user: %s" % playlist_user_name)

    # TODO: This needs to be passed to the DB layer
    include_private = True if user and user["id"] == playlist_user["id"] else False
    playlists, playlist_count = db_playlist.get_playlists_collaborated_on(db_conn, ts_conn,
                                                                          playlist_user["id"],
                                                                          include_private=include_private,
                                                                          load_recordings=False,
                                                                          count=count,
                                                                          offset=offset)

    return jsonify(serialize_playlists(playlists, playlist_count, count, offset))


@api_bp.get("/user/<playlist_user_name>/playlists/recommendations")
@crossdomain
@ratelimit()
@api_listenstore_needed
def user_recommendations(playlist_user_name):
    """
    Fetch recommendation playlist metadata in JSPF format without recordings for playlist_user_name.
    This endpoint only lists playlists that are to be shown on the listenbrainz.org recommendations
    pages.

    :statuscode 200: success
    :statuscode 404: user not found
    :resheader Content-Type: *application/json*
    """

    playlist_user = db_user.get_by_mb_id(db_conn, playlist_user_name)
    if playlist_user is None:
        raise APINotFound("Cannot find user: %s" % playlist_user_name)

    playlists = db_playlist.get_recommendation_playlists_for_user(db_conn, ts_conn, playlist_user.id)
    return jsonify(serialize_playlists(playlists, len(playlists), 0, 0))


@api_bp.get("/user/<playlist_user_name>/playlists/search")
@crossdomain
@ratelimit()
@api_listenstore_needed
def search_user_playlist(playlist_user_name):
    """
    Search for a playlist by name for a user.

    :param playlist_user_name: the MusicBrainz ID of the user whose playlists are being searched.
    :queryparam name: the name of the playlist to search for.
    :queryparam count: the number of playlists to return. Default: 25.
    :queryparam offset: the offset of the playlists to return. Default: 0.

    :statuscode 200: success
    :statuscode 404: user not found
    :resheader Content-Type: *application/json*
    """
    playlist_user = db_user.get_by_mb_id(db_conn, playlist_user_name)
    if playlist_user is None:
        raise APINotFound("Cannot find user: %s" % playlist_user_name)

    query = request.args.get("query")
    count = get_non_negative_param("count", DEFAULT_NUMBER_OF_PLAYLISTS_PER_CALL)
    offset = get_non_negative_param("offset", 0)

    playlists, playlist_count = db_playlist.search_playlists_for_user(db_conn, ts_conn, playlist_user.id, query, count, offset)

    return jsonify(serialize_playlists(playlists, playlist_count, count, offset))


@api_bp.get("/user/<user_name>/services")
@crossdomain
@ratelimit()
def get_service_details(user_name):
    """
    Get list of services which are connected to a given user's account.

    .. code-block:: json

        {
            "user_name": "hwnrwx",
            "services": ["spotify"]
        }

    :param user_name: the MusicBrainz ID of the user whose similar users are being requested.
    :resheader Content-Type: *application/json*
    :statuscode 200: Yay, you have data!
    :statuscode 401: Invalid authorization. See error message for details.
    :statuscode 403: Forbidden, you do not have permissions to view this user's information.
    :statuscode 404: The requested user was not found.
    """
    user = validate_auth_header(fetch_email=True)
    if user_name != user['musicbrainz_id']:
        raise APIForbidden("You don't have permissions to view this user's information.")

    services = db_external_service_oauth.get_services(db_conn, user["id"])
    return jsonify({'user_name': user_name, 'services': services})


@api_bp.get("/lb-radio/tags")
@crossdomain
@ratelimit()
def get_tags_dataset():
    """ Get recordings for use in LB radio with the specified tags that match the requested criteria.

    :param tag: the MusicBrainz tag to fetch recordings for, this parameter can be specified multiple times. if more
        than one tag is specified, the operator param should also be specified.
    :param operator: specify AND to retrieve recordings that have all the tags, otherwise specify OR to retrieve
        recordings that have any one of the tags.
    :param pop_begin: percent is a measure of the recording's popularity, pop_begin denotes a preferred
        lower bound on the popularity of recordings to be returned.
    :param pop_end: percent is a measure of the recording's popularity, pop_end denotes a preferred
        upper bound on the popularity of recordings to be returned.
    :param count: number of recordings to return for the
    :resheader Content-Type: *application/json*
    :statuscode 200: Yay, you have data!
    :statuscode 400: Invalid or missing param in request, see error message for details.
    """
    tag = request.args.getlist("tag")
    if tag is None:
        raise APIBadRequest("tag param is missing")

    operator = request.args.get("operator")

    # if there is only one tag, then we can use any of the operator's query to retrieve data
    if len(tag) == 1 and operator is None:
        operator = "OR"

    if operator is None:
        raise APIBadRequest("multiple tags are specified but the operator param is missing")
    operator = operator.upper()
    if operator != "AND" and operator != "OR":
        raise APIBadRequest("operator param should be either 'AND' or 'OR'")

    try:
        pop_begin = request.args.get("pop_begin")
        if pop_begin is None:
            raise APIBadRequest("pop_begin param is missing")
        pop_begin = float(pop_begin) / 100
        if pop_begin < 0 or pop_begin > 1:
            raise APIBadRequest("pop_begin should be between the range: 0 to 100")
    except ValueError:
        raise APIBadRequest(f"pop_begin: '{pop_begin}' is not a valid number")

    try:
        pop_end = request.args.get("pop_end")
        if pop_end is None:
            raise APIBadRequest("pop_end param is missing")
        pop_end = float(pop_end) / 100
        if pop_end < 0 or pop_end > 1:
            raise APIBadRequest("pop_end should be between the range: 0 to 100")
    except ValueError:
        raise APIBadRequest(f"pop_end: '{pop_end}' is not a valid number")

    try:
        count = request.args.get("count")
        if count is None:
            raise APIBadRequest("count param is missing")
        count = int(count)
        if count <= 0:
            raise APIBadRequest("count should be a positive number")
    except ValueError:
        raise APIBadRequest(f"count: '{count}' is not a valid positive number")

    if operator == "AND":
        recordings = tags.get_and(tag, pop_begin, pop_end, count)
    else:
        recordings = tags.get_or(tag, pop_begin, pop_end, count)
    return jsonify(recordings[:count])


def _get_listen_type(listen_type):
    return {
        'single': LISTEN_TYPE_SINGLE,
        'import': LISTEN_TYPE_IMPORT,
        'playing_now': LISTEN_TYPE_PLAYING_NOW
    }.get(listen_type)


@api_bp.get("/lb-radio/artist/<seed_artist_mbid>")
@crossdomain
@ratelimit()
def get_artist_radio_recordings(seed_artist_mbid):
    """ Get recordings for use in LB radio with the given seed artist. The endpoint
    returns a dict of all the similar artists, including the seed artist. For each artists,
    there will be a list of dicts that contain recording_mbid, similar_artist_mbid and total_listen_count:

    .. code-block:: json

            {
              "recording_mbid": "401c1a5d-56e7-434d-b07e-a14d4e7eb83c",
              "similar_artist_mbid": "cb67438a-7f50-4f2b-a6f1-2bb2729fd538",
              "similar_artist_name": "Boo Hoo Boys",
              "total_listen_count": 232361
            }

    :param mode: mode is the LB radio mode to be used for this query. Must be one of "easy", "medium", "hard".
    :param max_similar_artists: The maximum number of similar artists to return recordings for.
    :param max_recordings_per_artist: The maximum number of recordings to return for each artist. If there are aren't enough recordings, all available recordings will be returned.
    :param pop_begin: Popularity range percentage lower bound. A popularity range is given to narrow down the recordings into a smaller target group. The most popular recording(s) on LB have a pop percent of 100. The least popular recordings have a score of 0. This range is not coupled to the specified mode, but the mode would often determine the popularity range, so that less popular recordings can be returned on the medium and harder modes.
    :param pop_end: Popularity range percentage upper bound. See above.
    :resheader Content-Type: *application/json*
    :statuscode 200: Yay, you have data!
    :statuscode 400: Invalid or missing param in request, see error message for details.
    """
    if not is_valid_uuid(seed_artist_mbid):
        log_raise_400("Seed artist mbid is not a valid UUID.")

    max_similar_artists = _parse_int_arg("max_similar_artists")
    if max_similar_artists is None:
        raise APIBadRequest("Argument max_similar_artists must be specified.")

    max_recordings_per_artist = _parse_int_arg("max_recordings_per_artist")
    if max_recordings_per_artist is None:
        raise APIBadRequest("Argument max_recordings_per_artist must be specified.")

    mode = request.args.get("mode")
    if mode is None:
        raise APIBadRequest("mode param is missing")
    if mode not in ("easy", "medium", "hard"):
        raise APIBadRequest("mode must be one of: easy, medium or hard.")

    try:
        pop_begin = request.args.get("pop_begin")
        if pop_begin is None:
            raise APIBadRequest("pop_begin param is missing")
        pop_begin = float(pop_begin) / 100
        if pop_begin < 0 or pop_begin > 1:
            raise APIBadRequest("pop_begin should be between the range: 0 to 100")
    except ValueError:
        raise APIBadRequest(f"pop_begin: '{pop_begin}' is not a valid number")

    try:
        pop_end = request.args.get("pop_end")
        if pop_end is None:
            raise APIBadRequest("pop_end param is missing")
        pop_end = float(pop_end) / 100
        if pop_end < 0 or pop_end > 1:
            raise APIBadRequest("pop_end should be between the range: 0 to 100")
    except ValueError:
        raise APIBadRequest(f"pop_end: '{pop_end}' is not a valid number")

    return jsonify(lb_radio_artist(mode, seed_artist_mbid, max_similar_artists, max_recordings_per_artist, pop_begin, pop_end))
