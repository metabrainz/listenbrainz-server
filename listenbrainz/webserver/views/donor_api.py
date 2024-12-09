from brainzutils.ratelimit import ratelimit
from flask import Blueprint, jsonify, current_app

from listenbrainz.db.donation import get_recent_donors, get_biggest_donors
from listenbrainz.webserver import db_conn, meb_conn
from listenbrainz.webserver.decorators import crossdomain
from listenbrainz.webserver.views.api_tools import _parse_int_arg

donor_api_bp = Blueprint('donor_api_v1', __name__)


DEFAULT_DONOR_COUNT = 25


@donor_api_bp.route("/recent", methods=["GET", "OPTIONS"])
@crossdomain
@ratelimit()
def recent_donors():
    """ Get a list of most recent MeB donors with flairs.

    """
    count = _parse_int_arg("count", DEFAULT_DONOR_COUNT)
    offset = _parse_int_arg("offset", 0)

    if not current_app.config["SQLALCHEMY_METABRAINZ_URI"]:
        return []

    donors, _ = get_recent_donors(meb_conn, db_conn, count, offset)
    return jsonify(donors)


@donor_api_bp.route("/biggest", methods=["GET", "OPTIONS"])
@crossdomain
@ratelimit()
def biggest_donors():
    """ Get a list of the biggest MeB donors with flairs.

    """
    count = _parse_int_arg("count", DEFAULT_DONOR_COUNT)
    offset = _parse_int_arg("offset", 0)

    if not current_app.config["SQLALCHEMY_METABRAINZ_URI"]:
        return []

    donors, _ = get_biggest_donors(meb_conn, db_conn, count, offset)
    return jsonify(donors)
