from flask import Blueprint, jsonify

from listenbrainz.webserver.decorators import crossdomain
from listenbrainz.webserver.errors import APIBadRequest
from brainzutils.ratelimit import ratelimit
from listenbrainz.webserver.views.api import _parse_int_arg
from listenbrainz.db.color import get_releases_for_color


DEFAULT_NUMBER_OF_RELEASES = 25  # 5x5 grid

color_api_bp = Blueprint('color_api_v1', __name__)


@color_api_bp.route("/<color>", methods=["GET", "OPTIONS"])
@crossdomain(headers="Content-Type")
@ratelimit()
def color_releases(color):
    """
    Fetch a list of releases that have a cover close to a given color.

    :statuscode 200: success
    :statuscode 404: no items found
    :resheader Content-Type: *application/json*
    """

    try:
        if len(color) != 6:
            raise ValueError()

        color_tuple = tuple(int(color[i:i+2], 16) for i in (0, 2, 4))
    except ValueError:
        raise APIBadRequest("color must be a 6 digit hex color code.")

    count = _parse_int_arg("count", DEFAULT_NUMBER_OF_RELEASES)

    results = get_releases_for_color(*color_tuple, count)
    results = [c.to_api() for c in results]

    return jsonify({"payload": {"releases": results}})
