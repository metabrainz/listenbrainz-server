import sentry_sdk
import datetime

from brainzutils.ratelimit import ratelimit
from flask import Blueprint, jsonify, request

import listenbrainz.db.user as db_user
from listenbrainz.db.fresh_releases import get_fresh_releases
from listenbrainz.webserver import db_conn
from listenbrainz.webserver.decorators import crossdomain
from listenbrainz.webserver.errors import APINoContent, APINotFound, APIBadRequest
from listenbrainz.webserver.views.api_tools import _parse_bool_arg


fresh_releases_bp = Blueprint('fresh_releases_v1', __name__)


@fresh_releases_bp.get("/user/<user_name>/fresh_releases")
@crossdomain
@ratelimit()
def get_releases(user_name):
    """
    Get fresh releases data for the given user.

    .. code-block:: json

        {
            "artist_credit_name":"Santi & Tu\u011f\u00e7e",
            "artist_mbids":[
               "4690076b-1446-43f4-8a84-cfec56dc3601"
            ],
            "caa_id":37026686379,
            "caa_release_mbid":"9432fb06-bd84-4f2e-9386-b2f14e0de54d",
            "confidence":2,
            "release_date":"2023-10-20",
            "release_group_mbid":"30ac1ded-c254-46ac-a41f-7453dada6ae7",
            "release_group_primary_type":"Album",
            "release_group_secondary_type":null,
            "release_mbid":"9432fb06-bd84-4f2e-9386-b2f14e0de54d",
            "release_name":"The Marvelous Real",
            "release_tags":null
        }

    :param sort: The sort order of the results. Must be one of "release_date", "artist_credit_name", "release_name",
            or "confidence". Default "release_date".
    :param past: Whether to show releases in the past. Default True.
    :param future: Whether to show releases in the future. Default True.

    :statuscode 200: fetch succeeded
    :statuscode 400: invalid date or number of days passed.
    :resheader Content-Type: *application/json*
    """
    user = db_user.get_by_mb_id(db_conn, user_name)
    if not user:
        raise APINotFound("User %s not found" % user_name)

    sort = request.args.get("sort", "release_date")
    if sort not in ("release_date", "artist_credit_name", "release_name", "confidence"):
        raise APIBadRequest(
            "sort must be one of 'release_date', 'artist_credit_name', 'release_name', or 'confidence'.")

    past = _parse_bool_arg("past", True)
    future = _parse_bool_arg("future", True)

    try:
        data = get_fresh_releases(user["id"])
        releases = data["releases"] if data else []

        if sort == "confidence":
            releases = sorted(
                releases, key=lambda k: k.get("confidence", ""), reverse=True)
        else:
            releases = sorted(releases, key=lambda k: k.get(sort, ""))

        if not past:
            releases = [r for r in releases if "release_date" in r and datetime.datetime.strptime(
                r["release_date"], '%Y-%m-%d').date() >= datetime.date.today()]

        if not future:
            releases = [r for r in releases if "release_date" in r and datetime.datetime.strptime(
                r["release_date"], '%Y-%m-%d').date() <= datetime.date.today()]

        return jsonify({
            "payload": {
                "releases": releases,
                "user_id": user_name
            }
        })
    except Exception as e:
        sentry_sdk.capture_exception(e)
        raise APINoContent("")
