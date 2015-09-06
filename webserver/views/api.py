import sys
import urllib2
import json
import config
from flask import Blueprint, request, Response, jsonify, current_app
from werkzeug.exceptions import BadRequest, NotFound, InternalServerError
from kafka import SimpleProducer
from webserver.kafka_connection import _kafka
from webserver.cassandra_connection import _cassandra
from webserver.decorators import crossdomain

api_bp = Blueprint('listen', __name__)

MAX_LISTEN_SIZE = 10240    # overall listen size, to prevent egregious spamming
MAX_TAGS_PER_LISTEN = 50
MAX_TAG_SIZE = 64

MAX_ITEMS_PER_GET = 100
DEFAULT_ITEMS_PER_GET = 25

def validate_listen(listen):
    """ Make sure that required keys are present, filled out and not too large."""

    #current_app.logger.info(json.dumps(listen, indent=4))

    if 'listened_at' in listen and 'track_metadata' in listen and len(listen) > 2:
        raise BadRequest("JSON document may only contain listened_at and track_metadata top level keys.")

    # Validate basic metadata
    try:
        if not listen['track_metadata']['track_name']:
            raise BadRequest("JSON document does not contain required track_metadata.track_name")

        if not listen['track_metadata']['artist_name']:
            raise BadRequest("JSON document does not contain required track_metadata.artist_name")

    except KeyError:
        raise BadRequest("JSON document does not contain a valid metadata.track_name and/or track_metadata.artist_name")

    # Validate tags
    if 'additional_info' in listen['track_metadata']:
        tags = listen['track_metadata']['additional_info']['tags']
        if len(tags) > MAX_TAGS_PER_LISTEN:
            raise BadRequest("JSON document may not contain more than %d items in track_metadata.additional_info.tags" % MAX_TAGS_PER_LISTEN)

        for tag in tags:
            if len(tag) > MAX_TAG_SIZE:
                raise BadRequest("JSON document may not contain track_metadata.additional_info.tags longer than %d characters." % MAX_TAG_SIZE)

@api_bp.route("/listen/user/<user_id>", methods=["POST", "OPTIONS"])
@crossdomain(headers="Authorization, Content-Type")
def submit_listen(user_id):
    """Endpoint for submitting a listen to ListenBrainz. Sanity check listen and then pass on to Kafka."""

    raw_data = request.get_data()
    try:
        data = json.loads(raw_data.decode("utf-8"))
    except ValueError as e:
        raise BadRequest("Cannot parse JSON document: %s" % e)

    # Sanity check the submission
    try:
        payload = data['payload']
        if len(payload) == 0:
            raise BadRequest("JSON document does not contain any listens.")

        if len(raw_data) > len(payload) * MAX_LISTEN_SIZE:
            raise BadRequest("JSON document is too large. In aggregate, listens may not be larger than %d characters." % MAX_LISTEN_SIZE)

        if data['listen_type'] not in ('playing_now', 'single', 'import'):
            raise BadRequest("JSON document requires a valid listen_type key")

        if (data['listen_type'] == "single" or data['listen_type'] == 'playing_now') and len(payload) > 1:
            raise BadRequest("JSON document contains more than listen for a single/playing_now. "
                             "It should contain only one. ")
    except KeyError:
        raise BadRequest("Invalid JSON document submitted.")

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
        try:
            f = urllib2.urlopen(req, timeout = current_app.config['MESSYBRAINZ_TIMEOUT'])
            response = f.read()
            f.close()

            try:
                messy_response = json.loads(response)
            except ValueError, e:
                current_app.logging.error("MessyBrainz parse error: " + str(e))

            try:
                messybrainz_id = messy_response['messybrainz_id']
            except KeyError:
                current_app.logging.error("MessyBrainz did not return a proper id")

            if 'recording_id' in messy_response:
                recording_id = messy_response['recording_id']

        except urllib2.URLError, e:
            current_app.logging.error("Error calling MessyBrainz:" + str(e))

        except socket.timeout, e:
            current_app.logging.error("Timeout calling MessyBrainz.")

        if not 'additional_info' in listen['track_metadata']:
            listen['track_metadata']['additional_info'] = {}

        if recording_id:
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

    listens = _cassandra.fetch_listens(user_id, from_id=max_ts, limit=count)
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
