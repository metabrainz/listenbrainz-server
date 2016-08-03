from __future__ import print_function
import ujson
from flask import Blueprint, request, jsonify
from werkzeug.exceptions import BadRequest, InternalServerError, Unauthorized
from webserver.decorators import crossdomain
import webserver
import db
from webserver.rate_limiter import ratelimit
from api_tools import insert_payload, log_raise_400, MAX_LISTEN_SIZE, MAX_ITEMS_PER_GET, DEFAULT_ITEMS_PER_GET

api_bp = Blueprint('api_v1', __name__)


@api_bp.route("/1/submit-listens", methods=["POST", "OPTIONS"])
@crossdomain(headers="Authorization, Content-Type")
@ratelimit()
def submit_listen():
    """
    Submit listens to the server. A user token (found on https://listenbrainz.org/user/import ) must
    be provided in the Authorization header!

    For complete details on the format of the JSON to be POSTed to this endpoint, see :ref:`json-doc`.

    :reqheader Authorization: token <user token>
    :statuscode 200: listen(s) accepted.
    :statuscode 400: invalid JSON sent, see error message for details.
    :statuscode 401: invalid authorization. See error message for details.
    :resheader Content-Type: *application/json*
    """
    user_id = _validate_auth_header()

    raw_data = request.get_data()
    try:
        data = ujson.loads(raw_data.decode("utf-8"))
    except ValueError as e:
        log_raise_400("Cannot parse JSON document: %s" % e, raw_data)

    try:
        payload = data['payload']
        if len(payload) == 0:
            return "success"

        if len(raw_data) > len(payload) * MAX_LISTEN_SIZE:
            log_raise_400("JSON document is too large. In aggregate, listens may not "
                           "be larger than %d characters." % MAX_LISTEN_SIZE, payload)

        if data['listen_type'] not in ('playing_now', 'single', 'import'):
            log_raise_400("JSON document requires a valid listen_type key.", payload)

        if (data['listen_type'] == "single" or data['listen_type'] == 'playing_now') and len(payload) > 1:
            log_raise_400("JSON document contains more than listen for a single/playing_now. "
                           "It should contain only one.", payload)
    except KeyError:
        log_raise_400("Invalid JSON document submitted.", raw_data)

    try:
        insert_payload(payload, user_id, listen_type=data['listen_type'])
    except Exception, e:
        raise InternalServerError("Something went wrong. Please try again.")

    return "success"


@api_bp.route("/1/user/<user_id>/listens")
@ratelimit()
def get_listens(user_id):
    """
    Get listens for user ``user_id``. The format for the JSON returned is defined in our :ref:`json-doc`.

    If none of the optional arguments are given, this endpoint will return the :data:`~webserver.views.api.DEFAULT_ITEMS_PER_GET` most recent listens.
    The optional ``max_ts`` and ``min_ts`` UNIX epoch timestamps control at which point in time to start returning listens. You may specify max_ts or
    min_ts, but not both in one call. Listens are always returned in descending timestamp order.

    :param max_ts: If you specify a ``max_ts`` timestamp, listens with listened_at less than (but not including) this value will be returned.
    :param min_ts: If you specify a ``min_ts`` timestamp, listens with listened_at greter than (but not including) this value will be returned.
    :param count: Optional, number of listens to return. Default: :data:`~webserver.views.api.DEFAULT_ITEMS_PER_GET` . Max: :data:`~webserver.views.api.MAX_ITEMS_PER_GET`
    :statuscode 200: Yay, you have data!
    :resheader Content-Type: *application/json*
    """

    max_ts = _parse_int_arg("max_ts")
    min_ts = _parse_int_arg("min_ts")

    if max_ts and min_ts:
        log_raise_400("You may only specify max_ts or min_ts, not both.")

    db_conn = webserver.create_postgres()
    listens = db_conn.fetch_listens(
        user_id,
        limit=min(_parse_int_arg("count", DEFAULT_ITEMS_PER_GET), MAX_ITEMS_PER_GET),
        from_ts=min_ts,
        to_ts=max_ts,
    )
    listen_data = []
    for listen in listens:
        listen_data.append({
            "track_metadata": listen.data,
            "listened_at": listen.timestamp,
            "recording_msid": listen.recording_msid,
        })

    if min_ts:
        listen_data = listen_data[::-1]

    return jsonify({'payload': {
        'user_id': user_id,
        'count': len(listen_data),
        'listens': listen_data,
    }})




def _parse_int_arg(name, default=None):
    value = request.args.get(name)
    if value:
        try:
            return int(value)
        except ValueError:
            raise BadRequest("Invalid %s argument: %s" % (name, value))
    else:
        return default


def _validate_auth_header():
    auth_token = request.headers.get('Authorization')
    if not auth_token:
        raise Unauthorized("You need to provide an Authorization header.")
    try:
        auth_token = auth_token.split(" ")[1]
    except IndexError:
        raise Unauthorized("Provided Authorization header is invalid.")

    user = db.user.get_by_token(auth_token)
    if user is None:
        raise Unauthorized("Invalid authorization token.")

    return user['musicbrainz_id']
