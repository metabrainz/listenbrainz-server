from __future__ import absolute_import
from flask import Blueprint, request, Response, jsonify, app
from werkzeug.exceptions import BadRequest, NotFound
import json
from kafka import SimpleProducer
from kconn import _kafka

api_bp = Blueprint('listen', __name__)

MAX_LISTEN_SIZE = 10240    # overall listen size, to prevent egrigrious spamming
MAX_TAGS_PER_LISTEN = 50
MAX_TAG_SIZE = 64

def validate_listen(listen):
    """ Make sure that required keys are present, filled out and not too large."""

    print json.dumps(listen, indent=4)

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

# TODO: ensure that we're logged in when we get to the oauth bit
@api_bp.route("/listen/user/<user_id>", methods=["POST"])
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

    for i, listen in enumerate(payload):
        validate_listen(listen)

        listen['user_id'] = user_id
        # TODO: Catch exception here
        producer = SimpleProducer(_kafka)

        if data['listen_type'] == 'playing_now':
            producer.send_messages(b'playing_now', json.dumps(listen).encode('utf-8'))
        else:
            producer.send_messages(b'listens', json.dumps(listen).encode('utf-8'))

    return ""
