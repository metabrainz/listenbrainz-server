from __future__ import absolute_import
from flask import Blueprint, request, Response, jsonify, app
from werkzeug.exceptions import BadRequest, NotFound
import json
from kafka import SimpleProducer
from kconn import _kafka

listen_bp = Blueprint('listen', __name__)

#def validate_listen(listen):

# TODO: ensure that we're logged in when we get to the oauth bit
@listen_bp.route("/listen/user/<user_id>", methods=["POST"])
def submit_listen(user_id):
    """Endpoint for submitting a listen to ListenBrainz."""

    raw_data = request.get_data()
    print "data: '%s'" % raw_data
    try:
        data = json.loads(raw_data.decode("utf-8"))
    except ValueError as e:
        raise BadRequest("Cannot parse JSON document: %s" % e)

    # Sanity check the submission
    payload = data['payload']
    if len(payload) == 0:
        raise BadRequest("JSON document does not contain any listens.")

    if (data['listen_type'] == "single" or data['listen_type'] == 'playing_now') and len(payload) > 1:
        raise BadRequest("JSON document contains more than listen for a single/playing_now. "
                         "It should contain only one. ")

#    for i, listen in enumerate(payload):
#        err = validate_listen(listen):
#        if not err:
#            raise BadRequest("payload index %d error: " + err)

    data['user_id'] = user_id
    print json.dumps(data, indent = 4)
    # Catch exception here
    producer = SimpleProducer(_kafka)
    producer.send_messages(b'listens', json.dumps(data).encode('utf-8'))

    return ""
