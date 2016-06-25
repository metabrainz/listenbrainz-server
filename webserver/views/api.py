import sys
import ujson
from flask import Blueprint, request, jsonify
from werkzeug.exceptions import BadRequest, Unauthorized
from webserver.decorators import crossdomain
import webserver
import db.user
from webserver.rate_limiter import ratelimit
from api_tools import api_tools

api_bp = Blueprint('api_v1', __name__)

#: Maximum overall listen size in bytes, to prevent egregious spamming.
MAX_LISTEN_SIZE = 10240

#: The maximum number of tags per listen.
MAX_TAGS_PER_LISTEN = 50

#: The maximum length of a tag
MAX_TAG_SIZE = 64

#: The maximum number of listens returned in a single GET request.
MAX_ITEMS_PER_GET = 100

#: The default number of listens returned in a single GET request.
DEFAULT_ITEMS_PER_GET = 25

MAX_ITEMS_PER_MESSYBRAINZ_LOOKUP = 10


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
        _log_raise_400("Cannot parse JSON document: %s" % e, raw_data)

    try:
        payload = data['payload']
        if len(payload) == 0:
            return "success"

        if len(raw_data) > len(payload) * MAX_LISTEN_SIZE:
            _log_raise_400("JSON document is too large. In aggregate, listens may not "
                           "be larger than %d characters." % MAX_LISTEN_SIZE, payload)

        if data['listen_type'] not in ('playing_now', 'single', 'import'):
            _log_raise_400("JSON document requires a valid listen_type key.", payload)

        if (data['listen_type'] == "single" or data['listen_type'] == 'playing_now') and len(payload) > 1:
            _log_raise_400("JSON document contains more than listen for a single/playing_now. "
                           "It should contain only one.", payload)
    except KeyError:
        _log_raise_400("Invalid JSON document submitted.", raw_data)

    augmented_listens = []
    msb_listens = []
    for listen in payload:
        api_tools("_validate_listen", listen)
        listen['user_id'] = user_id

        msb_listens.append(listen)
        if len(msb_listens) >= MAX_ITEMS_PER_MESSYBRAINZ_LOOKUP:
            augmented_listens.extend(api_tools("_messybrainz_lookup", msb_listens))
            msb_listens = []

    if msb_listens:
        augmented_listens.extend(api_tools("_messybrainz_lookup", msb_listens))

    api_tools("_send_listens_to_redis", data['listen_type'], augmented_listens)

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
        _log_raise_400("You may only specify max_ts or min_ts, not both.")

    db_conn = webserver.create_postgres()
    listens = db_conn.fetch_listens(
        user_id,
        limit=min(_parse_int_arg("count", DEFAULT_ITEMS_PER_GET), MAX_ITEMS_PER_GET),
        from_id=min_ts,
        to_id=max_ts,
    )
    listen_data = []
    for listen in listens:
        listen_data.append({
                             "track_metadata" : listen.data,
                             "listened_at" : listen.timestamp,
                             "recording_msid" : listen.recording_msid,
                           })

    if min_ts:
        listen_data = listen_data[::-1]

    return jsonify({'payload': {
        'user_id': user_id,
        'count': len(listen_data),
        'listens': listen_data,
    }})


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


def _parse_int_arg(name, default=None):
    value = request.args.get(name)
    if value:
        try:
            return int(value)
        except ValueError:
            raise BadRequest("Invalid %s argument: %s" % (name, value))
    else:
        return default


def _log_raise_400(msg, data):
    """Helper function for logging issues with request data and showing error page.

    Logs the message and data, raises BadRequest exception which shows 400 Bad
    Request to the user.
    """

    if type(data) == dict:
        data = ujson.dumps(data)

    current_app.logger.debug("BadRequest: %s\nJSON: %s" % (msg, data))
    raise BadRequest(msg)
