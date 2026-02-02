from flask import Blueprint, jsonify

from listenbrainz.webserver import db_conn
from listenbrainz.webserver.decorators import crossdomain
from listenbrainz.webserver.errors import APIBadRequest
from brainzutils.ratelimit import ratelimit
from listenbrainz.webserver.views.api_tools import _parse_int_arg
from listenbrainz.db.color import get_releases_for_color
from brainzutils import cache


DEFAULT_NUMBER_OF_RELEASES = 25  # 5x5 grid
DEFAULT_CACHE_EXPIRE_TIME = 3600 * 24  # 1 day
HUESOUND_PAGE_CACHE_KEY = "huesound.%s.%d"

color_api_bp = Blueprint('color_api_v1', __name__)


@color_api_bp.get("/<color>")
@crossdomain
@ratelimit()
def huesound(color):
    """
    Fetch a list of releases that have cover art that has a predominant
    color that is close to the given color.

    .. code-block:: json

        {
            "payload": {
                "releases" : [
                    {
                      "artist_name": "Letherette",
                      "color": [ 250, 90, 192 ],
                      "dist": 109.973,
                      "release_mbid": "00a109da-400c-4350-9751-6e6f25e89073",
                      "caa_id": 34897349734,
                      "release_name": "EP5",
                      "recordings": "< array of listen formatted metadata >",
                      },
                    ". . ."
                ]
            }
        }

    :statuscode 200: success
    :resheader Content-Type: *application/json*
    """

    try:
        if len(color) != 6:
            raise ValueError()

        color_tuple = tuple(int(color[i:i+2], 16) for i in (0, 2, 4))
    except ValueError:
        raise APIBadRequest("color must be a 6 digit hex color code.")

    count = _parse_int_arg("count", DEFAULT_NUMBER_OF_RELEASES)

    cache_key = HUESOUND_PAGE_CACHE_KEY % (color, count)
    results = cache.get(cache_key, decode=True)
    if not results:
        results = get_releases_for_color(db_conn, *color_tuple, count)
        results = [c.to_api() for c in results]
        cache.set(cache_key, results, DEFAULT_CACHE_EXPIRE_TIME, encode=True)

    return jsonify({"payload": {"releases": results}})
