import datetime
from flask import Blueprint, jsonify, request, current_app

from brainzutils.ratelimit import ratelimit
from brainzutils import cache
import listenbrainz.db.fresh_releases
from listenbrainz.webserver import db_conn, ts_conn
from listenbrainz.webserver.decorators import crossdomain
from listenbrainz.webserver.errors import APIBadRequest, APIInternalServerError
from listenbrainz.webserver.views.api_tools import _parse_int_arg, _parse_bool_arg
from listenbrainz.db.color import get_releases_for_color
from troi.patches.lb_radio import LBRadioPatch
from troi.patch import Patch

DEFAULT_NUMBER_OF_FRESH_RELEASE_DAYS = 14
MAX_NUMBER_OF_FRESH_RELEASE_DAYS = 90
DEFAULT_NUMBER_OF_RELEASES = 25  # 5x5 grid
DEFAULT_CACHE_EXPIRE_TIME = 3600 * 24  # 1 day
HUESOUND_PAGE_CACHE_KEY = "huesound.%s.%d"

explore_api_bp = Blueprint('explore_api_v1', __name__)


@explore_api_bp.get("/fresh-releases/")
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
    :param days: The number of days of fresh releases to show. Max 90 days.
    :param sort: The sort order of the results. Must be one of "release_date", "artist_credit_name" or "release_name".
                 Default "release_date".
    :param past: Whether to show releases in the past. Default True.
    :param future: Whether to show releases in the future. Default True.
    :statuscode 200: fetch succeeded
    :statuscode 400: invalid date or number of days passed.
    :resheader Content-Type: *application/json*
    """

    days = _parse_int_arg("days", DEFAULT_NUMBER_OF_FRESH_RELEASE_DAYS)
    if days < 1 or days > MAX_NUMBER_OF_FRESH_RELEASE_DAYS:
        raise APIBadRequest(
            f"days must be between 1 and {MAX_NUMBER_OF_FRESH_RELEASE_DAYS}.")

    sort = request.args.get("sort", "release_date")
    if sort not in ("release_date", "artist_credit_name", "release_name"):
        raise APIBadRequest(
            "sort must be one of 'release_date', 'artist_credit_name' or 'release_name'.")

    past = _parse_bool_arg("past", True)
    future = _parse_bool_arg("future", True)

    release_date = request.args.get("release_date", "")
    if release_date != "":
        try:
            release_date = datetime.datetime.strptime(
                release_date, "%Y-%m-%d").date()
        except ValueError as err:
            raise APIBadRequest(
                "Cannot parse date. Must be in YYYY-MM-DD format.")
    else:
        release_date = datetime.date.today()

    try:
        db_releases, total_count = listenbrainz.db.fresh_releases.get_sitewide_fresh_releases(
            ts_conn, release_date, days, sort, past, future
        )
    except Exception as e:
        current_app.logger.error("Server failed to get latest release: {}".format(e), exc_info=True)
        raise APIInternalServerError("Server failed to get latest release")

    return jsonify({
        "payload": {
            "releases": [r.to_dict() for r in db_releases],
            "total_count": total_count,
        }
    })


@explore_api_bp.get("/color/<color>")
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

        color_tuple = tuple(int(color[i:i + 2], 16) for i in (0, 2, 4))
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


@explore_api_bp.get("/lb-radio")
@crossdomain
@ratelimit()
def lb_radio():
    """
    Generate a playlist with LB Radio.

    :param prompt: The LB Radio prompt from which to generate playlists.
    :param mode: The mode that LB radio should use. Must be easy, medium or hard.

    .. code-block:: json

        {
            "payload": {
                "jspf" : {}, // <JSPF playlist here>
                "feedback": [] // <user feedback items>
            }
        }

    :statuscode 200: success
    :statuscode 400: bad request: some parameters are missing or invalid
    :statuscode 500: Troi encountered an error
    :resheader Content-Type: *application/json*
    """
    prompt = request.args.get("prompt", None)
    if prompt is None:
        raise APIBadRequest(f"The prompt parameter cannot be empty.")

    mode = request.args.get("mode", None)
    if mode is None or mode not in ("easy", "medium", "hard"):
        raise APIBadRequest(
            f"The mode parameter must be one of 'easy', 'medium', 'hard'.")

    try:
        patch = LBRadioPatch({ "mode": mode, "prompt": prompt, "quiet": True, "min_recordings": 1})
        playlist = patch.generate_playlist()
    except RuntimeError as err:
        raise APIBadRequest(f"LB Radio generation failed: {err}")

    jspf = playlist.get_jspf() if playlist is not None else {
        "playlist": {"tracks": []}}
    feedback = patch.user_feedback()

    return jsonify({"payload": {"jspf": jspf, "feedback": feedback}})
