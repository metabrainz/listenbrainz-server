from __future__ import absolute_import
from flask import Blueprint, request, Response, jsonify
from webserver.decorators import crossdomain
from werkzeug.exceptions import BadRequest, NotFound
import db.data
import db.exceptions
import json

api_bp = Blueprint('api', __name__)


@api_bp.route("/submit", methods=["POST"])
@crossdomain()
def submit():
    raw_data = request.get_data()
    try:
        data = json.loads(raw_data.decode("utf-8"))
    except ValueError as e:
        raise BadRequest("Cannot parse JSON document: %s" % e)

    try:
        gid = db.data.get_id_from_scribble(data)
        if gid:
            status = "known"
            data = db.data.load_scribble(gid)
            musicbrainz_recording_id = data["musicbrainz_recording_id"]
            if musicbrainz_recording_id:
                status = "matched"
        else:
            status = "new"
            musicbrainz_recording_id = None
            gid = db.data.submit_scribble(data)
        response = {"status": status,
                    "musicbrainz_recording_id": musicbrainz_recording_id,
                    "messybrainz_id": gid
                   }
        return jsonify(response)
    except db.exceptions.BadDataException as e:
        raise BadRequest(e)


@api_bp.route("/<uuid:messybrainz_id>")
@crossdomain()
def get(messybrainz_id):
    try:
        data = db.data.load_scribble(messybrainz_id)
        status = "unmatched"
        if data["musicbrainz_recording_id"]:
            status = "matched"
        response = {"status": status, "payload": data}
        return jsonify(response)
    except db.exceptions.NoDataFoundException:
        raise NotFound

@api_bp.route("/<uuid:messybrainz_id>/aka")
@crossdomain()
def get_aka(messybrainz_id):
    """Returns all other MessyBrainz scribbles that are known to be equivalent
    (as specified in the clusters table).
    """
    raise NotImplementedError
