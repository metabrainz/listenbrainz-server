import datetime
from flask import Blueprint, jsonify, request

import listenbrainz.db.fresh_releases
from listenbrainz.webserver.decorators import crossdomain
from listenbrainz.webserver.errors import APIBadRequest
from listenbrainz.webserver.views.api_tools import _parse_int_arg
from listenbrainz.db.color import get_releases_for_color
from brainzutils.ratelimit import ratelimit
from brainzutils import cache

DEFAULT_NUMBER_OF_FRESH_RELEASE_DAYS = 14
MAX_NUMBER_OF_FRESH_RELEASE_DAYS = 30
DEFAULT_NUMBER_OF_RELEASES = 25  # 5x5 grid
DEFAULT_CACHE_EXPIRE_TIME = 3600 * 24  # 1 day
HUESOUND_PAGE_CACHE_KEY = "huesound.%s.%d"

explore_api_bp = Blueprint('explore_api_v1', __name__)


@explore_api_bp.route("/fresh-releases/", methods=["GET", "OPTIONS"])
@crossdomain
@ratelimit()
def get_fresh_releases():
    """
    This endpoint fetches upcoming and recently released (fresh) releases and returns a list of:

    .. code-block:: json

        {
            "artist_credit_name": "R\u00f6yksopp",
            "artist_mbids": [
              "1c70a3fc-fa3c-4be1-8b55-c3192db8a884"
            ],
            "release_date": "2022-04-29",
            "release_group_mbid": "4f1c579a-8a9c-4f96-92ae-befcdf3e0d32",
            "release_group_primary_type": "Album",
            "release_mbid": "1f1db316-8361-4a40-9633-550b259642f5",
            "release_name": "Profound Mysteries"
        }

    :param release_date: Fresh releases will be shown around this pivot date.
                         Must be in YYYY-MM-DD format
    :param days: The number of days of fresh releases to show. Max 30 days.
    :statuscode 200: fetch succeeded
    :statuscode 400: invalid date or number of days passed.
    :resheader Content-Type: *application/json*
    """

    days = _parse_int_arg("days", DEFAULT_NUMBER_OF_FRESH_RELEASE_DAYS)
    if days < 1 or days > MAX_NUMBER_OF_FRESH_RELEASE_DAYS:
        raise APIBadRequest(f"days must be between 1 and {MAX_NUMBER_OF_FRESH_RELEASE_DAYS}.")

    release_date = request.args.get("release_date", "")
    if release_date != "":
        try:
            release_date = datetime.datetime.strptime(release_date, "%Y-%m-%d").date()
        except ValueError as err:
            raise APIBadRequest("Cannot parse date. Must be in YYYY-MM-DD format.")
    else:
        release_date = datetime.date.today()

    return jsonify([r.to_dict() for r in listenbrainz.db.fresh_releases.get_sitewide_fresh_releases(release_date, days)])


@explore_api_bp.route("/color/<color>", methods=["GET", "OPTIONS"])
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
        results = get_releases_for_color(*color_tuple, count)
        results = [c.to_api() for c in results]
        cache.set(cache_key, results, DEFAULT_CACHE_EXPIRE_TIME, encode=True)

    return jsonify({"payload": {"releases": results}})
