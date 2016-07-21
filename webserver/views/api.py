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

# Max time in seconds after which the playing_now stream will expire.
PLAYING_NOW_MAX_DURATION = 5 * 60

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


def _send_listens_to_redis(listen_type, listens):


    p = _redis.pipeline()
    for listen in listens:
        if listen_type == 'playing_now':
            try:
                p.setex('playing_now' + ':' + listen['user_id'],
                        ujson.dumps(listen).encode('utf-8'), PLAYING_NOW_MAX_DURATION)
            except:
                current_app.logger.error("Redis rpush playing_now write error: " + str(sys.exc_info()[0]))
                raise InternalServerError("Cannot record playing_now at this time.")
        else:
            try:
                p.rpush('listens', ujson.dumps(listen).encode('utf-8'))
            except:
                current_app.logger.error("Redis rpush listens write error: " + str(sys.exc_info()[0]))
                raise InternalServerError("Cannot record listen at this time.")

    p.execute()

def _messybrainz_lookup(listens):

    msb_listens = []
    for listen in listens:
        messy_dict = {
            'artist': listen['track_metadata']['artist_name'],
            'title': listen['track_metadata']['track_name'],
        }
        if 'release_name' in listen['track_metadata']:
            messy_dict['release'] = listen['track_metadata']['release_name']

        if 'additional_info' in listen['track_metadata']:
            ai = listen['track_metadata']['additional_info']
            if 'artist_mbids' in ai and type(ai['artist_mbids']) == list:
                messy_dict['artist_mbids'] = ai['artist_mbids']
            if 'release_mbid' in ai:
                messy_dict['release_mbid'] = ai['release_mbid']
            if 'recording_mbid' in ai:
                messy_dict['recording_mbid'] = ai['recording_mbid']
            if 'track_number' in ai:
                messy_dict['track_number'] = ai['track_number']
            if 'spotify_id' in ai:
                messy_dict['spotify_id'] = ai['spotify_id']
        msb_listens.append(messy_dict)

    try:
        msb_responses = messybrainz.submit_listens(msb_listens)
    except messybrainz.exceptions.BadDataException as e:
        _log_raise_400(str(e))
    except messybrainz.exceptions.NoDataFoundException:
        return []
    except messybrainz.exceptions.ErrorAddingException as e:
        raise ServiceUnavailable(str(e))

    augmented_listens = []
    for listen, messybrainz_resp in zip(listens, msb_responses['payload']):
        messybrainz_resp = messybrainz_resp['ids']

        if 'additional_info' not in listen['track_metadata']:
            listen['track_metadata']['additional_info'] = {}

        try:
            listen['recording_msid'] = messybrainz_resp['recording_msid']
            listen['track_metadata']['additional_info']['artist_msid'] = messybrainz_resp['artist_msid']
        except KeyError:
            current_app.logger.error("MessyBrainz did not return a proper set of ids")
            raise InternalServerError

        try:
            listen['track_metadata']['additional_info']['release_msid'] = messybrainz_resp['release_msid']
        except KeyError:
            pass

        artist_mbids = messybrainz_resp.get('artist_mbids', [])
        release_mbid = messybrainz_resp.get('release_mbid', None)
        recording_mbid = messybrainz_resp.get('recording_mbid', None)

        if 'artist_mbids'    not in listen['track_metadata']['additional_info'] and \
           'release_mbid'   not in listen['track_metadata']['additional_info'] and \
           'recording_mbid' not in listen['track_metadata']['additional_info']:

            if len(artist_mbids) > 0 and release_mbid and recording_mbid:
                listen['track_metadata']['additional_info']['artist_mbids'] = artist_mbids
                listen['track_metadata']['additional_info']['release_mbid'] = release_mbid
                listen['track_metadata']['additional_info']['recording_mbid'] = recording_mbid

        augmented_listens.append(listen)

    return augmented_listens


def _validate_listen(listen):
    """Make sure that required keys are present, filled out and not too large."""

    if not 'listened_at' in listen:
        _log_raise_400("JSON document must contain the key listened_at at the top level.", listen)

    try:
        listen['listened_at'] = int(listen['listened_at'])
    except ValueError:
        _log_raise_400("JSON document must contain an int value for listened_at.", listen)

    if 'listened_at' in listen and 'track_metadata' in listen and len(listen) > 2:
        _log_raise_400("JSON document may only contain listened_at and "
                       "track_metadata top level keys", listen)

    # Basic metadata
    try:
        if not listen['track_metadata']['track_name']:
            _log_raise_400("JSON document does not contain required "
                           "track_metadata.track_name.", listen)
        if not listen['track_metadata']['artist_name']:
            _log_raise_400("JSON document does not contain required "
                           "track_metadata.artist_name.", listen)
    except KeyError:
        _log_raise_400("JSON document does not contain a valid metadata.track_name "
                       "and/or track_metadata.artist_name.", listen)

    if 'additional_info' in listen['track_metadata']:
        # Tags
        if 'tags' in listen['track_metadata']['additional_info']:
            tags = listen['track_metadata']['additional_info']['tags']
            if len(tags) > MAX_TAGS_PER_LISTEN:
                _log_raise_400("JSON document may not contain more than %d items in "
                               "track_metadata.additional_info.tags." % MAX_TAGS_PER_LISTEN, listen)
            for tag in tags:
                if len(tag) > MAX_TAG_SIZE:
                    _log_raise_400("JSON document may not contain track_metadata.additional_info.tags "
                                   "longer than %d characters." % MAX_TAG_SIZE, listen)
        # MBIDs
        if 'release_mbid' in listen['track_metadata']['additional_info']:
            lmbid = listen['track_metadata']['additional_info']['release_mbid']
            if not is_valid_uuid(lmbid):
                _log_raise_400("Release MBID format invalid.", listen)
        if 'recording_mbid' in listen['track_metadata']['additional_info']:
            cmbid = listen['track_metadata']['additional_info']['recording_mbid']
            if not is_valid_uuid(cmbid):
                _log_raise_400("Recording MBID format invalid.", listen)
        ambids = listen['track_metadata']['additional_info'].get('artist_mbids', [])
        for ambid in ambids:
            if not is_valid_uuid(ambid):
                _log_raise_400("Artist MBID format invalid.", listen)


def _convert_to_native_format(data):
    """
    Converts the imported listen-payload from the lastfm backup file
    to the native payload format.
    """
    payload = []
    for native_lis in data:
        listen = {}
        listen['track_metadata'] = {}
        listen['track_metadata']['additional_info'] = {}

        if 'timestamp' in native_lis and 'unixtimestamp' in native_lis['timestamp']:
            listen['listened_at'] = native_lis['timestamp']['unixtimestamp']

        if 'track' in native_lis:
            if 'name' in native_lis['track']:
                listen['track_metadata']['track_name'] = native_lis['track']['name']
            if 'mbid' in native_lis['track']:
                listen['track_metadata']['additional_info']['recording_mbid'] = native_lis['track']['mbid']
            if 'artist' in native_lis['track']:
                if 'name' in native_lis['track']['artist']:
                    listen['track_metadata']['artist_name'] = native_lis['track']['artist']['name']
                if 'mbid' in native_lis['track']['artist']:
                    listen['track_metadata']['additional_info']['artist_mbids'] = [native_lis['track']['artist']['mbid']]
        payload.append(listen)
    return payload


def _payload_to_augmented_list(payload, user_id):
    """ Converts the payload to augmented list after lookup
        in the MessyBrainz database
    """
    augmented_listens = []
    msb_listens = []
    for listen in payload:
        _validate_listen(listen)
        listen['user_id'] = user_id

        msb_listens.append(listen)
        if len(msb_listens) >= MAX_ITEMS_PER_MESSYBRAINZ_LOOKUP:
            augmented_listens.extend(_messybrainz_lookup(msb_listens))
            msb_listens = []

    if msb_listens:
        augmented_listens.extend(_messybrainz_lookup(msb_listens))
    return augmented_listens


def _log_raise_400(msg, data):
    """Helper function for logging issues with request data and showing error page.

    Logs the message and data, raises BadRequest exception which shows 400 Bad
    Request to the user.
    """

    if type(data) == dict:
        data = ujson.dumps(data)

    current_app.logger.debug("BadRequest: %s\nJSON: %s" % (msg, data))
    raise BadRequest(msg)

# lifted from AcousticBrainz
def is_valid_uuid(u):
    try:
        u = uuid.UUID(u)
        return True
    except ValueError:
        return False
