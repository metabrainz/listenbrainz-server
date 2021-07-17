import ujson
from flask import Blueprint, request, Response
from messybrainz.webserver.decorators import crossdomain, ip_filter
from werkzeug.exceptions import BadRequest, NotFound

import messybrainz
import messybrainz.db.exceptions
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

    if not isinstance(data, list):
        raise BadRequest("submitted data must be a list")

    try:
        result = messybrainz.submit_listens_and_sing_me_a_sweet_song(data)
        return ujsonify(result)
    except messybrainz.exceptions.BadDataException as e:
        raise BadRequest(e)


@api_bp.route("/<uuid:messybrainz_id>")
@crossdomain()
def get(messybrainz_id):
    try:
        data = messybrainz.load_recording_from_msid(messybrainz_id)
    except messybrainz.exceptions.NoDataFoundException:
        raise NotFound

    return Response(ujson.dumps(data), mimetype='application/json')


@api_bp.route("/<uuid:messybrainz_id>/aka")
@crossdomain()
def get_aka(messybrainz_id):
    """Returns all other MessyBrainz recordings that are known to be equivalent
    (as specified in the clusters table).
    """
    raise NotImplementedError
