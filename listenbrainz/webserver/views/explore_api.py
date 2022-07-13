import datetime
from flask import Blueprint, jsonify

from listenbrainz.db.upcoming_releases import get_sitewide_upcoming_releases

from listenbrainz.webserver.decorators import crossdomain
from brainzutils.ratelimit import ratelimit


explore_api_bp = Blueprint('explore_api_v1', __name__)


@explore_api_bp.route("/upcoming-releases/", methods=["GET", "OPTIONS"])
@crossdomain
@ratelimit()
def get_upcoming_releases():
    """
    This endpoint fetches upcoming and recently released releases. 

    :statuscode 200: fetch succeeded
    """

    return jsonify([ r.to_dict() for r in get_sitewide_upcoming_releases(datetime.date.today(), 30)])
