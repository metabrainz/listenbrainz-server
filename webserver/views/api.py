from __future__ import absolute_import
from flask import Blueprint, request, Response, jsonify
from db.data import load_low_level, load_high_level, submit_low_level_data, count_lowlevel
from db.exceptions import NoDataFoundException, BadDataException
from webserver.decorators import crossdomain
from werkzeug.exceptions import BadRequest, NotFound
import json

api_bp = Blueprint('api', __name__)

@api_bp.route("/<uuid:mbid>/low-level", methods=["POST"])
def submit_low_level(mbid):
    """Endpoint for submitting low-level information to AcousticBrainz."""
    raw_data = request.get_data()
    try:
        data = json.loads(raw_data.decode("utf-8"))
    except ValueError as e:
        raise BadRequest("Cannot parse JSON document: %s" % e)

    try:
        submit_low_level_data(mbid, data)
    except BadDataException as e:
        raise BadRequest(e)
    return ""
