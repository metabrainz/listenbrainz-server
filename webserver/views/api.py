from __future__ import absolute_import
from flask import Blueprint
from webserver.decorators import crossdomain

api_bp = Blueprint('api', __name__)


@api_bp.route("/submit", methods=["POST"])
@crossdomain()
def submit():
    raise NotImplementedError


@api_bp.route("/<uuid:messybrainz_id>")
@crossdomain()
def get(messybrainz_id):
    raise NotImplementedError


@api_bp.route("/<uuid:messybrainz_id>/aka")
@crossdomain()
def get_aka(messybrainz_id):
    """Returns all other MessyBrainz scribbles that are known to be equivalent
    (as specified in the clusters table).
    """
    raise NotImplementedError
