import sys
import urllib2
import json
import socket
from flask import Blueprint, request, current_app
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

def log_and_raise_bad_request(err, data):
    """Helper function to not make the code even uglier."""

    if type(data) == dict:
        data = json.dumps(data)

    current_app.logger.debug("BadRequest: %s\nJSON: %s" % (err, data))
    raise BadRequest


def validate_listen(listen):
    """ Make sure that required keys are present, filled out and not too large."""

    #current_app.logger.info(json.dumps(listen, indent=4))

    if 'listened_at' in listen and 'track_metadata' in listen and len(listen) > 2:
        log_and_raise_bad_request("JSON document may only contain listened_at and track_metadata top level keys.", listen)

    # Validate basic metadata
    try:
        if not listen['track_metadata']['track_name']:
            log_and_raise_bad_request("JSON document does not contain required track_metadata.track_name", listen)

        if not listen['track_metadata']['artist_name']:
            log_and_raise_bad_request("JSON document does not contain required track_metadata.artist_name", listen)

    except KeyError:
        log_and_raise_bad_request("JSON document does not contain a valid metadata.track_name and/or track_metadata.artist_name", listen)

    # Validate tags
    if 'additional_info' in listen['track_metadata']:
        tags = listen['track_metadata']['additional_info']['tags']
        if len(tags) > MAX_TAGS_PER_LISTEN:
            log_and_raise_bad_request("JSON document may not contain more than %d items in track_metadata.additional_info.tags" % MAX_TAGS_PER_LISTEN, listen)

        for tag in tags:
            if len(tag) > MAX_TAG_SIZE:
                log_and_raise_bad_request("JSON document may not contain track_metadata.additional_info.tags longer than %d characters." % MAX_TAG_SIZE, listen)

@api_bp.route("/listen/user/<user_id>", methods=["POST", "OPTIONS"])
@crossdomain(headers="Authorization, Content-Type")
def submit_listen(user_id):
    """Endpoint for submitting a listen to ListenBrainz. Sanity check listen and then pass on to Kafka."""

    token = request.headers.get('Authorization')
    if not token:
        raise Unauthorized("You need to provide an Authorization header.")

    try:
        token = token.split(" ")[1]
    except IndexError:
        raise Unauthorized("Invalid Authorization header provided.")

    user = db.user.get_by_mb_id(user_id)
    if user is None:
        raise Unauthorized("User %s is not known to MusicBrainz." % user_id)

    if token != user['auth_token']:
        raise Unauthorized("Invalid authorization token.")

    raw_data = request.get_data()
    try:
        data = json.loads(raw_data.decode("utf-8"))
    except ValueError as e:
        log_and_raise_bad_request("Cannot parse JSON document: %s" % e, raw_data)

    # Sanity check the submission
    try:
        payload = data['payload']
        if len(payload) == 0:
            log_and_raise_bad_request("JSON document does not contain any listens.", payload)

        if len(raw_data) > len(payload) * MAX_LISTEN_SIZE:
            log_and_raise_bad_request("JSON document is too large. In aggregate, listens may not be larger than %d characters." % MAX_LISTEN_SIZE, payload)

        if data['listen_type'] not in ('playing_now', 'single', 'import'):
            log_and_raise_bad_request("JSON document requires a valid listen_type key", payload)

        if (data['listen_type'] == "single" or data['listen_type'] == 'playing_now') and len(payload) > 1:
            log_and_raise_bad_request("JSON document contains more than listen for a single/playing_now. "
                             "It should contain only one. ", payload)
    except KeyError:
        log_and_raise_bad_request("Invalid JSON document submitted.", raw_data)

    producer = SimpleProducer(_kafka)
    for i, listen in enumerate(payload):
        validate_listen(listen)
        listen['user_id'] = user_id

        messybrainz_dict = {
            'artist' : listen['track_metadata']['artist_name'],
            'track' : listen['track_metadata']['track_name']
        }

        if 'release_name' in listen['track_metadata']:
            messybrainz_dict['release'] = listen['track_metadata']['release_name']

        messy_data = json.dumps(messybrainz_dict)
        req = urllib2.Request(current_app.config['MESSYBRAINZ_SUBMIT_URL'], messy_data,
            {'Content-Type': 'application/json', 'Content-Length': len(messy_data)})

        messybrainz_id = None
        recording_id = None
        artist_id = None
        release_id = None
        try:
            f = urllib2.urlopen(req, timeout = current_app.config['MESSYBRAINZ_TIMEOUT'])
            response = f.read()
            f.close()

            try:
                messy_response = json.loads(response)
            except ValueError as e:
                current_app.logger.error("MessyBrainz parse error: " + str(e))

            try:
                messybrainz_id = messy_response['messybrainz_id']
            except KeyError:
                current_app.logger.error("MessyBrainz did not return a proper id")

            if 'artist_id' in messy_response:
                artist_id = messy_response['artist_id']

            if 'release_id' in messy_response:
                release_id = messy_response['release_id']

            if 'recording_id' in messy_response:
                recording_id = messy_response['recording_id']

        except urllib2.URLError as e:
            current_app.logger.error("Error calling MessyBrainz:" + str(e))

        except socket.timeout as e:
            current_app.logger.error("Timeout calling MessyBrainz.")

        listen['listen_id'] = {}
        if recording_id:
            listen['listen_id']['id_type'] = "musicbrainz"
            listen['listen_id']['id'] = recording_id
        else:
            listen['listen_id']['id_type'] = "messybrainz"
            listen['listen_id']['id'] = messybrainz_id

        if not 'additional_info' in listen['track_metadata']:
            listen['track_metadata']['additional_info'] = {}

        if not 'artist_id' in listen['track_metadata']['additional_info'] and \
            not 'release_id' in listen['track_metadata']['additional_info'] and \
            not 'recording_id' in listen['track_metadata']['additional_info']: 

            if artist_id and release_id and recording_id:
                listen['track_metadata']['additional_info']['artist_id'] = artist_id
                listen['track_metadata']['additional_info']['release'] = release_id
                listen['track_metadata']['additional_info']['recording_id'] = recording_id

        if messybrainz_id:
            listen['track_metadata']['additional_info']['messybrainz_id'] = messybrainz_id

        #print json.dumps(listen, indent=4)

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

    return ""

@api_bp.route("/listen/user/<user_id>", methods=["GET"])
def get_listens(user_id):
    count = max(request.args.get('count') or DEFAULT_ITEMS_PER_GET, MAX_ITEMS_PER_GET)
    max_ts = request.args.get('max_ts') or None

    cassandra = webserver.create_cassandra()
    listens = cassandra.fetch_listens(user_id, from_id=max_ts, limit=count)
    listen_data = []
    for listen in listens:
        temp = json.loads(listen.json)
        del temp['user_id']
        listen_data.append(temp)

    payload = {}
    payload['user_id'] = user_id
    payload['count'] = count
    payload['listens'] = listen_data

    return json.dumps({ 'payload' : payload }, indent=4)
