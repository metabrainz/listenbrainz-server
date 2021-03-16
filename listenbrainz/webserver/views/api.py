import datetime
from operator import itemgetter
import time
from typing import Tuple

import ujson
import psycopg2
from flask import Blueprint, request, jsonify, current_app

from listenbrainz.listenstore import TimescaleListenStore
from listenbrainz.webserver.errors import APIBadRequest, APIInternalServerError, APIUnauthorized, APINotFound, APIServiceUnavailable
from listenbrainz.db.exceptions import DatabaseException
from listenbrainz.webserver.decorators import crossdomain
from listenbrainz import webserver
from listenbrainz.db.model.playlist import Playlist
import listenbrainz.db.playlist as db_playlist
import listenbrainz.db.user as db_user
import listenbrainz.db.user_relationship as db_user_relationship
from listenbrainz.webserver.rate_limiter import ratelimit
import listenbrainz.webserver.redis_connection as redis_connection
from listenbrainz.webserver.views.api_tools import insert_payload, log_raise_400, validate_listen, parse_param_list,\
    is_valid_uuid, MAX_LISTEN_SIZE, MAX_ITEMS_PER_GET, DEFAULT_ITEMS_PER_GET, LISTEN_TYPE_SINGLE, LISTEN_TYPE_IMPORT,\
    LISTEN_TYPE_PLAYING_NOW, validate_auth_header, get_non_negative_param
from listenbrainz.webserver.views.playlist_api import serialize_jspf
from listenbrainz.listenstore.timescale_listenstore import SECONDS_IN_TIME_RANGE, TimescaleListenStoreException
from listenbrainz.webserver.timescale_connection import _ts

api_bp = Blueprint('api_v1', __name__)

DEFAULT_TIME_RANGE = 3
MAX_TIME_RANGE = 73
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
    user = validate_auth_header()

    raw_data = request.get_data()
    try:
        data = ujson.loads(raw_data.decode("utf-8"))
    except ValueError as e:
        log_raise_400("Cannot parse JSON document: %s" % e, raw_data)

    try:
        payload = data['payload']
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

    # validate listens to make sure json is okay
    for listen in payload:
        validate_listen(listen, listen_type)

    try:
        insert_payload(
            payload, user, listen_type=_get_listen_type(data['listen_type']))
    except APIServiceUnavailable as e:
        raise
    except Exception as e:
        raise APIInternalServerError("Something went wrong. Please try again.")

    return jsonify({'status': 'ok'})


@api_bp.route("/user/<user_name>/listens")
@crossdomain()
@ratelimit()
def get_listens(user_name):
    """
    Get listens for user ``user_name``. The format for the JSON returned is defined in our :ref:`json-doc`.

    If none of the optional arguments are given, this endpoint will return the :data:`~webserver.views.api.DEFAULT_ITEMS_PER_GET` most recent listens.
    The optional ``max_ts`` and ``min_ts`` UNIX epoch timestamps control at which point in time to start returning listens. You may specify max_ts or
    min_ts, but not both in one call. Listens are always returned in descending timestamp order.

    :param max_ts: If you specify a ``max_ts`` timestamp, listens with listened_at less than (but not including) this value will be returned.
    :param min_ts: If you specify a ``min_ts`` timestamp, listens with listened_at greater than (but not including) this value will be returned.
    :param count: Optional, number of listens to return. Default: :data:`~webserver.views.api.DEFAULT_ITEMS_PER_GET` . Max: :data:`~webserver.views.api.MAX_ITEMS_PER_GET`
    :param time_range: This parameter determines the time range for the listen search. Each increment of the time_range corresponds to a range of 5 days and the default
                       time_range of 3 means that 15 days will be searched.
                       Default: :data:`~webserver.views.api.DEFAULT_TIME_RANGE` . Max: :data:`~webserver.views.api.MAX_TIME_RANGE`
    :statuscode 200: Yay, you have data!
    :resheader Content-Type: *application/json*
    """
    db_conn = webserver.create_timescale(current_app)
    min_ts, max_ts, count, time_range = _validate_get_endpoint_params(
        db_conn, user_name)
    _, max_ts_per_user = db_conn.get_timestamps_for_user(user_name)

    # If none are given, start with now and go down
    if max_ts == None and min_ts == None:
        max_ts = max_ts_per_user + 1

    listens = db_conn.fetch_listens(
        user_name,
        limit=count,
        from_ts=min_ts,
        to_ts=max_ts,
        time_range=time_range
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
def get_listen_count(user_name):
    """
        Get the number of listens for a user ``user_name``.

        The returned listen count has an element 'payload' with only key: 'count'
        which unsurprisingly contains the listen count for the user.

    :statuscode 200: Yay, you have listen counts!
    :resheader Content-Type: *application/json*
    """

    try:
        db_conn = webserver.create_timescale(current_app)
        listen_count = db_conn.get_listen_count_for_user(user_name)
        if listen_count < 0:
            raise APINotFound("Cannot find user: %s" % user_name)
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
    :resheader Content-Type: *application/json*
    """

    user = db_user.get_by_mb_id(user_name)
    if user is None:
        raise APINotFound("Cannot find user: %s" % user_name)

    playing_now_listen = redis_connection._redis.get_playing_now(user['id'])
    listen_data = []
    count = 0
    if playing_now_listen:
        count += 1
        listen_data = [{
            'track_metadata': playing_now_listen.data,
        }]

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
def get_recent_listens_for_user_list(user_list):
    """
    Fetch the most recent listens for a comma separated list of users. Take care to properly HTTP escape
    user names that contain commas!

    :statuscode 200: Fetched listens successfully.
    :statuscode 400: Your user list was incomplete or otherwise invalid.
    :resheader Content-Type: *application/json*
    """

    limit = _parse_int_arg("limit", 2)
    users = parse_param_list(user_list)
    if not len(users):
        raise APIBadRequest("user_list is empty or invalid.")

    db_conn = webserver.create_timescale(current_app)
    listens = db_conn.fetch_recent_listens_for_users(
        users,
        limit=limit
    )
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

    {
        'musicbrainz_id': the MusicBrainz ID of the user,

        'latest_import': the timestamp of the newest listen submitted in previous imports. Defaults to 0
    }

    :param user_name: the MusicBrainz ID of the user whose data is needed
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
    """
    if request.method == 'GET':
        user_name = request.args.get('user_name', '')
        user = db_user.get_by_mb_id(user_name)
        if user is None:
            raise APINotFound(
                "Cannot find user: {user_name}".format(user_name=user_name))
        return jsonify({
            'musicbrainz_id': user['musicbrainz_id'],
            'latest_import': 0 if not user['latest_import'] else int(user['latest_import'].strftime('%s'))
        })
    elif request.method == 'POST':
        user = validate_auth_header()

        try:
            ts = ujson.loads(request.get_data()).get('ts', 0)
        except ValueError:
            raise APIBadRequest('Invalid data sent')

        try:
            db_user.increase_latest_import(user['musicbrainz_id'], int(ts))
        except DatabaseException as e:
            current_app.logger.error(
                "Error while updating latest import: {}".format(e))
            raise APIInternalServerError(
                'Could not update latest_import, try again')

        return jsonify({'status': 'ok'})


@api_bp.route('/validate-token', methods=['GET'])
@ratelimit()
def validate_token():
    """
    Check whether a User Token is a valid entry in the database.

    In order to query this endpoint, send a GET request with the token to check
    as the `token` argument (example: /validate-token?token=token-to-check)

    A JSON response, with the following format, will be returned.

    - If the given token is valid::

        {
            "code": 200,
            "message": "Token valid.",
            "valid": True,
            "user": "MusicBrainz ID of the user with the passed token"
        }

    - If the given token is invalid::

        {
            "code": 200,
            "message": "Token invalid.",
            "valid": False,
        }

    :statuscode 200: The user token is valid/invalid.
    :statuscode 400: No token was sent to the endpoint.
    """
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
def delete_listen():
    """
    Delete a particular listen from a user's listen history.
    This checks for the correct authorization token and deletes the listen.

    The format of the JSON to be POSTed to this endpoint is:

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
        _ts.delete_listen(listened_at=listened_at,
                          recording_msid=recording_msid, user_name=user["musicbrainz_id"])
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

    :params count: The number of playlists to return (for pagination). Default
        :data:`~webserver.views.api.DEFAULT_NUMBER_OF_PLAYLISTS_PER_CALL`
    :params offset: The offset of into the list of playlists to return (for pagination)
    :statuscode 200: Yay, you have data!
    :statuscode 404: User not found
    :resheader Content-Type: *application/json*
    """
    user = validate_auth_header(True)

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

    :params count: The number of playlists to return (for pagination). Default
        :data:`~webserver.views.api.DEFAULT_NUMBER_OF_PLAYLISTS_PER_CALL`
    :params offset: The offset of into the list of playlists to return (for pagination)
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

    :params count: The number of playlists to return (for pagination). Default
        :data:`~webserver.views.api.DEFAULT_NUMBER_OF_PLAYLISTS_PER_CALL`
    :params offset: The offset of into the list of playlists to return (for pagination)
    :statuscode 200: Yay, you have data!
    :statuscode 404: User not found
    :resheader Content-Type: *application/json*
    """

    user = validate_auth_header(True)

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


@api_bp.route("/user/<user_name>/followers", methods=["GET", "OPTIONS"])
@crossdomain(headers="Content-Type")
@ratelimit()
def get_followers(user_name: str):
    user = db_user.get_by_mb_id(user_name)
    try:
        followers = db_user_relationship.get_followers_of_user(user["id"])
    except Exception:
        current_app.logger.critical("Error while trying to fetch followers", exc_info=True)
        raise APIInternalServerError("Something went wrong, please try again later")

    return jsonify({"followers": followers, "user": user["musicbrainz_id"]})


@api_bp.route("/user/<user_name>/following", methods=["GET", "OPTIONS"])
@crossdomain(headers="Content-Type")
@ratelimit()
def get_following(user_name: str):
    user = db_user.get_by_mb_id(user_name)
    try:
        following = db_user_relationship.get_following_for_user(user["id"])
    except Exception:
        current_app.logger.critical("Error while trying to fetch following", exc_info=True)
        raise APIInternalServerError("Something went wrong, please try again later")

    return jsonify({"following": following, "user": user["musicbrainz_id"]})


def _parse_int_arg(name, default=None):
    value = request.args.get(name)
    if value:
        try:
            return int(value)
        except ValueError:
            raise APIBadRequest("Invalid %s argument: %s" % (name, value))
    else:
        return default


def _get_listen_type(listen_type):
    return {
        'single': LISTEN_TYPE_SINGLE,
        'import': LISTEN_TYPE_IMPORT,
        'playing_now': LISTEN_TYPE_PLAYING_NOW
    }.get(listen_type)


def _validate_get_endpoint_params(db_conn: TimescaleListenStore, user_name: str) -> Tuple[int, int, int, int]:
    """ Validates parameters for listen GET endpoints like /username/listens and /username/feed/events

    Returns a tuple of integers: (min_ts, max_ts, count, time_range)
    """
    max_ts = _parse_int_arg("max_ts")
    min_ts = _parse_int_arg("min_ts")
    time_range = _parse_int_arg("time_range", DEFAULT_TIME_RANGE)

    if time_range < 1 or time_range > MAX_TIME_RANGE:
        log_raise_400("time_range must be between 1 and %d." % MAX_TIME_RANGE)

    if max_ts and min_ts:
        if max_ts < min_ts:
            log_raise_400("max_ts should be greater than min_ts")

        if (max_ts - min_ts) > MAX_TIME_RANGE * SECONDS_IN_TIME_RANGE:
            log_raise_400(
                "time_range specified by min_ts and max_ts should be less than %d days." % MAX_TIME_RANGE * 5)

    # Validate requetsed listen count is positive
    count = min(_parse_int_arg(
        "count", DEFAULT_ITEMS_PER_GET), MAX_ITEMS_PER_GET)
    if count < 0:
        log_raise_400("Number of items requested should be positive")

    return min_ts, max_ts, count, time_range
