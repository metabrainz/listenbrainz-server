from __future__ import absolute_import
from flask import Blueprint, request, Response
from webserver.decorators import crossdomain, ip_filter
from werkzeug.exceptions import BadRequest, NotFound
import db.data
import db.exceptions
import ujson

api_bp = Blueprint('api', __name__)

def ujsonify(*args, **kwargs):
    """An implementation of flask's jsonify which uses ujson
    instead of json. Doesn't have as many bells and whistles
    (no indent/separator support).
    """
    return Response((ujson.dumps(dict(*args, **kwargs)), '\n'),
                        mimetype='application/json')

@api_bp.route("/submit", methods=["POST"])
@crossdomain()
@ip_filter
def submit():
    raw_data = request.get_data()
    try:
        data = ujson.loads(raw_data.decode("utf-8"))
    except ValueError as e:
        raise BadRequest("Cannot parse JSON document: %s" % e)

    keys = data.keys()
    if "artist" not in keys or "title" not in keys:
        raise BadRequest("Require artist and title keys in submission")

    try:
        gid = db.data.get_id_from_recording(data)
        if not gid:
            gid = db.data.submit_recording(data)
        data = db.data.load_recording(gid)
        return ujsonify(data)
    except db.exceptions.BadDataException as e:
        raise BadRequest(e)


@api_bp.route("/<uuid:messybrainz_id>")
@crossdomain()
def get(messybrainz_id):
    try:
        data = db.data.load_recording(messybrainz_id)
        return ujsonify(data)
    except db.exceptions.NoDataFoundException:
        raise NotFound


@api_bp.route("/<uuid:messybrainz_id>/aka")
@crossdomain()
def get_aka(messybrainz_id):
    """Returns all other MessyBrainz recordings that are known to be equivalent
    (as specified in the clusters table).
    """
    raise NotImplementedError
