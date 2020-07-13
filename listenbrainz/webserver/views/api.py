import ujson
from flask import Blueprint, request, jsonify, current_app
from listenbrainz.webserver.errors import APIBadRequest, APIInternalServerError, APIUnauthorized, APINotFound, APIServiceUnavailable
from listenbrainz.db.exceptions import DatabaseException
from listenbrainz.webserver.decorators import crossdomain
from listenbrainz.webserver.views.follow import parse_user_list
from listenbrainz import webserver
import listenbrainz.db.user as db_user
from listenbrainz.webserver.rate_limiter import ratelimit
import listenbrainz.webserver.redis_connection as redis_connection
from listenbrainz.webserver.views.api_tools import insert_payload, log_raise_400, validate_listen, MAX_LISTEN_SIZE, MAX_ITEMS_PER_GET,\
    DEFAULT_ITEMS_PER_GET, LISTEN_TYPE_SINGLE, LISTEN_TYPE_IMPORT, LISTEN_TYPE_PLAYING_NOW
import time

api_bp = Blueprint('api_v1', __name__)


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
    :statuscode 200: listen(s) accepted.
    :statuscode 400: invalid JSON sent, see error message for details.
    :statuscode 401: invalid authorization. See error message for details.
    :resheader Content-Type: *application/json*
    """
    user = _validate_auth_header()

    raw_data = request.get_data()
    try:
        data = ujson.loads(raw_data.decode("utf-8"))
    except ValueError as e:
        log_raise_400("Cannot parse JSON document: %s" % e, raw_data)

    try:
        payload = data['payload']
        if len(payload) == 0:
            log_raise_400("JSON document does not contain any listens", payload)

        if len(raw_data) > len(payload) * MAX_LISTEN_SIZE:
            log_raise_400("JSON document is too large. In aggregate, listens may not "
                          "be larger than %d characters." % MAX_LISTEN_SIZE, payload)

        if data['listen_type'] not in ('playing_now', 'single', 'import'):
            log_raise_400("JSON document requires a valid listen_type key.", payload)

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
        insert_payload(payload, user, listen_type=_get_listen_type(data['listen_type']))
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
    :statuscode 200: Yay, you have data!
    :resheader Content-Type: *application/json*
    """

    current_time = int(time.time())
    max_ts = _parse_int_arg("max_ts")
    min_ts = _parse_int_arg("min_ts")

    # if no max given, use now()

    if max_ts and min_ts:
        log_raise_400("You may only specify max_ts or min_ts, not both.")

    # If none are given, start with now and go down
    if max_ts == None and min_ts == None:
        max_ts = current_time

    db_conn = webserver.create_timescale(current_app)
    listens = db_conn.fetch_listens(
        user_name,
        limit=min(_parse_int_arg("count", DEFAULT_ITEMS_PER_GET), MAX_ITEMS_PER_GET),
        from_ts=min_ts,
        to_ts=max_ts,
    )
    listen_data = []
    for listen in listens:
        listen_data.append(listen.to_api())

    latest_listen = db_conn.fetch_listens(
        user_name,
        limit=1,
        to_ts=current_time,
    )
    latest_listen_ts = latest_listen[0].ts_since_epoch if len(latest_listen) > 0 else 0

    if min_ts:
        listen_data = listen_data[::-1]

    return jsonify({'payload': {
        'user_id': user_name,
        'count': len(listen_data),
        'listens': listen_data,
        'latest_listen_ts': latest_listen_ts,
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
    users = parse_user_list(user_list)
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
    :statuscode 200: latest import timestamp updated
    :statuscode 400: invalid JSON sent, see error message for details.
    :statuscode 401: invalid authorization. See error message for details.
    """
    if request.method == 'GET':
        user_name = request.args.get('user_name', '')
        user = db_user.get_by_mb_id(user_name)
        if user is None:
            raise APINotFound("Cannot find user: {user_name}".format(user_name=user_name))
        return jsonify({
            'musicbrainz_id': user['musicbrainz_id'],
            'latest_import': 0 if not user['latest_import'] else int(user['latest_import'].strftime('%s'))
        })
    elif request.method == 'POST':
        user = _validate_auth_header()

        try:
            ts = ujson.loads(request.get_data()).get('ts', 0)
        except ValueError:
            raise APIBadRequest('Invalid data sent')

        try:
            db_user.increase_latest_import(user['musicbrainz_id'], int(ts))
        except DatabaseException as e:
            current_app.logger.error("Error while updating latest import: {}".format(e))
            raise APIInternalServerError('Could not update latest_import, try again')

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


def _parse_int_arg(name, default=None):
    value = request.args.get(name)
    if value:
        try:
            return int(value)
        except ValueError:
            raise APIBadRequest("Invalid %s argument: %s" % (name, value))
    else:
        return default


def _validate_auth_header():
    auth_token = request.headers.get('Authorization')
    if not auth_token:
        raise APIUnauthorized("You need to provide an Authorization header.")
    try:
        auth_token = auth_token.split(" ")[1]
    except IndexError:
        raise APIUnauthorized("Provided Authorization header is invalid.")

    user = db_user.get_by_token(auth_token)
    if user is None:
        raise APIUnauthorized("Invalid authorization token.")

    return user


def _get_listen_type(listen_type):
    return {
        'single': LISTEN_TYPE_SINGLE,
        'import': LISTEN_TYPE_IMPORT,
        'playing_now': LISTEN_TYPE_PLAYING_NOW
    }.get(listen_type)
