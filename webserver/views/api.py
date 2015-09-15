import sys
import urllib2
import json
import socket
from flask import Blueprint, request, current_app, jsonify
from werkzeug.exceptions import BadRequest, InternalServerError, Unauthorized
from kafka import SimpleProducer
from webserver.kafka_connection import _kafka
from webserver.decorators import crossdomain
import webserver
import db.user

api_bp = Blueprint('listen', __name__)

MAX_LISTEN_SIZE = 10240    # overall listen size, to prevent egregious spamming
MAX_TAGS_PER_LISTEN = 50
MAX_TAG_SIZE = 64

MAX_ITEMS_PER_GET = 100
DEFAULT_ITEMS_PER_GET = 25


@api_bp.route("/listen/user/<user_id>", methods=["POST", "OPTIONS"])
@crossdomain(headers="Authorization, Content-Type")
def submit_listen(user_id):
    """Endpoint for submitting a listen to ListenBrainz.

    Sanity check listen and then pass on to Kafka.
    """
    _validate_auth_header(user_id)

    raw_data = request.get_data()
    try:
        data = json.loads(raw_data.decode("utf-8"))
    except ValueError as e:
        _log_raise_400("Cannot parse JSON document: %s" % e, raw_data)

    try:
        payload = data['payload']
        if len(payload) == 0:
            _log_raise_400("JSON document does not contain any listens.", payload)

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

    producer = SimpleProducer(_kafka)
    for i, listen in enumerate(payload):
        _validate_listen(listen)
        listen['user_id'] = user_id

        messybrainz_resp = get_messybrainz_data(listen)

        try:
            messybrainz_id = messybrainz_resp['messybrainz_id']
        except KeyError:
            current_app.logger.error("MessyBrainz did not return a proper id")
            raise InternalServerError

        recording_id = messybrainz_resp.get('recording_id', None)
        artist_id = messybrainz_resp.get('artist_id', None)
        release_id = messybrainz_resp.get('release_id', None)

        listen['listen_id'] = {}
        if recording_id:
            listen['listen_id']['id_type'] = "musicbrainz"
            listen['listen_id']['id'] = recording_id
        else:
            listen['listen_id']['id_type'] = "messybrainz"
            listen['listen_id']['id'] = messybrainz_id

        if 'additional_info' not in listen['track_metadata']:
            listen['track_metadata']['additional_info'] = {}

        if 'artist_id'    not in listen['track_metadata']['additional_info'] and \
           'release_id'   not in listen['track_metadata']['additional_info'] and \
           'recording_id' not in listen['track_metadata']['additional_info']:

            if artist_id and release_id and recording_id:
                listen['track_metadata']['additional_info']['artist_id'] = artist_id
                listen['track_metadata']['additional_info']['release'] = release_id
                listen['track_metadata']['additional_info']['recording_id'] = recording_id

        if messybrainz_id:
            listen['track_metadata']['additional_info']['messybrainz_id'] = messybrainz_id

        if data['listen_type'] == 'playing_now':
            try:
                producer.send_messages(b'playing_now', json.dumps(listen).encode('utf-8'))
            except:
                current_app.logger.error("Kafka playing_now write error: " + str(sys.exc_info()[0]))
                raise InternalServerError("Cannot record playing_now at this time.")
        else:
            try:
                producer.send_messages(b'listens', json.dumps(listen).encode('utf-8'))
            except:
                current_app.logger.error("Kafka listens write error: " + str(sys.exc_info()[0]))
                raise InternalServerError("Cannot record listen at this time.")

    return "success"


@api_bp.route("/listen/user/<user_id>")
def get_listens(user_id):
    count = min(request.args.get('count') or DEFAULT_ITEMS_PER_GET, MAX_ITEMS_PER_GET)
    max_ts = request.args.get('max_ts') or None

    cassandra = webserver.create_cassandra()
    listens = cassandra.fetch_listens(user_id, from_id=max_ts, limit=count)
    listen_data = []
    for listen in listens:
        temp = json.loads(listen.json)
        del temp['user_id']
        listen_data.append(temp)

    return jsonify({'payload': {
        'user_id': user_id,
        'count': len(listen_data),
        'listens': listen_data,
    }})


def _validate_auth_header(user_id):
    auth_token = request.headers.get('Authorization')
    if not auth_token:
        raise Unauthorized("You need to provide an Authorization header.")
    try:
        auth_token = auth_token.split(" ")[1]
    except IndexError:
        raise Unauthorized("Provided Authorization header is invalid.")

    user = db.user.get_by_mb_id(user_id)
    if user is None:
        raise Unauthorized("User %s is not known to MusicBrainz." % user_id)
    if auth_token != user['auth_token']:
        raise Unauthorized("Invalid authorization token.")


def get_messybrainz_data(listen):
    messy_dict = {
        'artist': listen['track_metadata']['artist_name'],
        'track': listen['track_metadata']['track_name'],
    }
    if 'release_name' in listen['track_metadata']:
        messy_dict['release'] = listen['track_metadata']['release_name']

    messy_data = json.dumps(messy_dict)
    req = urllib2.Request(current_app.config['MESSYBRAINZ_SUBMIT_URL'], messy_data, {
        'Content-Type': 'application/json',
        'Content-Length': len(messy_data),
    })

    try:
        f = urllib2.urlopen(req, timeout=current_app.config['MESSYBRAINZ_TIMEOUT'])
        response = f.read()
        f.close()
    except urllib2.URLError as e:
        current_app.logger.error("Error calling MessyBrainz:" + str(e))
    except socket.timeout:
        current_app.logger.error("Timeout calling MessyBrainz.")

    try:
        messy_response = json.loads(response)
    except ValueError as e:
        current_app.logger.error("MessyBrainz parse error: " + str(e))
        raise InternalServerError

    return messy_response


def _validate_listen(listen):
    """Make sure that required keys are present, filled out and not too large."""
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
        data = json.dumps(data)

    current_app.logger.debug("BadRequest: %s\nJSON: %s" % (msg, data))
    raise BadRequest(msg)
