import sys
import urllib2
import ujson
import socket
from flask import Blueprint, request, current_app, jsonify
from werkzeug.exceptions import BadRequest, InternalServerError, Unauthorized, ServiceUnavailable
from kafka import SimpleProducer
from webserver.kafka_connection import _kafka
from webserver.decorators import crossdomain
import webserver
import db.user
import messybrainz

api_bp = Blueprint('api_v1', __name__)

MAX_LISTEN_SIZE = 10240    # overall listen size, to prevent egregious spamming
MAX_TAGS_PER_LISTEN = 50
MAX_TAG_SIZE = 64

MAX_ITEMS_PER_GET = 100
DEFAULT_ITEMS_PER_GET = 25
MAX_ITEMS_PER_MESSYBRAINZ_LOOKUP = 10

@api_bp.route("/1/submit-listens", methods=["POST", "OPTIONS"])
@crossdomain(headers="Authorization, Content-Type")
def submit_listen():
    """Endpoint for submitting a listen to ListenBrainz.

    Sanity check listen and then pass on to Kafka.
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
        _validate_listen(listen)
        listen['user_id'] = user_id

        msb_listens.append(listen)
        if len(msb_listens) >= MAX_ITEMS_PER_MESSYBRAINZ_LOOKUP:
            augmented_listens.extend(_messybrainz_lookup(msb_listens))
            msb_listens = []

    if msb_listens:
        augmented_listens.extend(_messybrainz_lookup(msb_listens))

    _send_listens_to_kafka(data['listen_type'], augmented_listens)

    return "success"


@api_bp.route("/1/user/<user_id>/listens")
def get_listens(user_id):

    max_ts = _parse_int_arg("max_ts")
    min_ts = _parse_int_arg("min_ts")

    if max_ts and min_ts:
        _log_and_raise_400("You may only specify max_ts or min_ts, not both.")

    cassandra = webserver.create_cassandra()
    listens = cassandra.fetch_listens(
        user_id,
        limit=min(_parse_int_arg("count", DEFAULT_ITEMS_PER_GET), MAX_ITEMS_PER_GET),
        from_id=min_ts,
        to_id=max_ts
    )
    listen_data = []
    for listen in listens:
        listen_data.append({
                             "track_metadata" : listen.data,
                             "listened_at" : listen.timestamp,
                             "recording_msid" : listen.recording_msid,
                           })

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


def _send_listens_to_kafka(listen_type, listens):

    producer = SimpleProducer(_kafka)

    for listen in listens:
        if listen_type == 'playing_now':
            try:
                producer.send_messages(b'playing_now', ujson.dumps(listen).encode('utf-8'))
            except:
                current_app.logger.error("Kafka playing_now write error: " + str(sys.exc_info()[0]))
                raise InternalServerError("Cannot record playing_now at this time.")
        else:
            try:
                producer.send_messages(b'listens', ujson.dumps(listen).encode('utf-8'))
            except:
                current_app.logger.error("Kafka listens write error: " + str(sys.exc_info()[0]))
                raise InternalServerError("Cannot record listen at this time.")


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
        msb_responses = messybrainz.submit_listens_and_sing_me_a_sweet_song(msb_listens)
    except messybrainz.exceptions.BadDataException as e:
        _log_and_raise_400(str(e))
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
                listen['track_metadata']['additional_info']['artist_id'] = artist_mbid
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

    # Tags
    if 'additional_info' in listen['track_metadata']:
        if 'tags' in listen['track_metadata']['additional_info']:
            tags = listen['track_metadata']['additional_info']['tags']
            if len(tags) > MAX_TAGS_PER_LISTEN:
                _log_raise_400("JSON document may not contain more than %d items in "
                               "track_metadata.additional_info.tags." % MAX_TAGS_PER_LISTEN, listen)
            for tag in tags:
                if len(tag) > MAX_TAG_SIZE:
                    _log_raise_400("JSON document may not contain track_metadata.additional_info.tags "
                                   "longer than %d characters." % MAX_TAG_SIZE, listen)


def _log_raise_400(msg, data):
    """Helper function for logging issues with request data and showing error page.

    Logs the message and data, raises BadRequest exception which shows 400 Bad
    Request to the user.
    """

    if type(data) == dict:
        data = ujson.dumps(data)

    current_app.logger.debug("BadRequest: %s\nJSON: %s" % (msg, data))
    raise BadRequest(msg)
