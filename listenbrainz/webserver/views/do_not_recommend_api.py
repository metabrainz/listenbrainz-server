from brainzutils.ratelimit import ratelimit
from flask import Blueprint, jsonify, request

import listenbrainz.db.user as db_user
from listenbrainz.db import do_not_recommend
from listenbrainz.webserver import db_conn

from listenbrainz.webserver.decorators import crossdomain
from listenbrainz.webserver.errors import APINotFound, APIBadRequest
from listenbrainz.webserver.views.api_tools import get_non_negative_param, DEFAULT_ITEMS_PER_GET, MAX_ITEMS_PER_GET, \
    validate_auth_header, is_valid_uuid

allowed_entity_types = ['artist', 'release', 'release_group', 'recording']

do_not_recommend_api_bp = Blueprint('do_not_recommend_api_v1', __name__)


@do_not_recommend_api_bp.get("/user/<user_name>/do-not-recommend")
@crossdomain
@ratelimit()
def get_do_not_recommends(user_name):
    """
    Get do not recommends for the user given by ``user_name``. The format for the JSON returned is as follows:

    .. code-block:: json

        {
            "count": 1,
            "offset": 0,
            "total_count": 5,
            "results": [
                {
                    "created": 1668526511,
                    "entity": "recording",
                    "entity_mbid": "bdc9e5af-54e2-4dde-9d8f-87b04f00b89c"
                }
            ],
            "user_id": "lucifer"
        }

    :param count: Optional, number of do not recommend items to return.
        Default: :data:`~webserver.views.api.DEFAULT_ITEMS_PER_GET` Max: :data:`~webserver.views.api.MAX_ITEMS_PER_GET`.
    :type count: ``int``
    :param offset: Optional, number of feedback items to skip from the beginning, for pagination.
        Ex. An offset of 5 means the top 5 feedback will be skipped, defaults to 0.
    :type offset: ``int``
    :statuscode 200: Yay, you have data!
    :resheader Content-Type: *application/json*
    """
    offset = get_non_negative_param("offset", default=0)
    count = get_non_negative_param("count", default=DEFAULT_ITEMS_PER_GET)
    count = min(count, MAX_ITEMS_PER_GET)

    user = db_user.get_by_mb_id(db_conn, user_name)
    if user is None:
        raise APINotFound("Cannot find user: %s" % user_name)

    results = do_not_recommend.get(db_conn, user["id"], count, offset)
    total_count = do_not_recommend.get_total_count(db_conn, user["id"])

    return jsonify({
        "offset": offset,
        "count": len(results),
        "total_count": total_count,
        "user_id": user_name,
        "results": results
    })


@do_not_recommend_api_bp.post("/do-not-recommend/add")
@crossdomain
@ratelimit()
def add_do_not_recommend():
    """ Submit a/an artist/release/release-group/recording that should not be recommended to the specified user forever
    or for some specified time. The endpoint accepts a json payload of the following format:

    .. code-block:: json

        {
            "entity": "<entity type>",
            "entity_mbid": "<mbid of the entity>",
            "until": 1669022475
        }

    Currently, the supported entity types are ``artist``, ``release``, ``release_group`` and ``recording``. The ``until``
    key in the json body is optional. If absent, the don't recommend entry will be added forever. If present, it should
    be an utc timestamp in seconds denoting the time till which the entity should not be recommended.

    :reqheader Authorization: Token <user token>
    :statuscode 200: feedback accepted.
    :statuscode 400: invalid JSON sent, see error message for details.
    :statuscode 401: invalid authorization. See error message for details.
    :resheader Content-Type: *application/json*
    """
    user, entity, entity_mbid, until = _parse_json_params()
    do_not_recommend.insert(db_conn, user["id"], entity, entity_mbid, until)
    return jsonify({"status": "ok"})


@do_not_recommend_api_bp.post("/do-not-recommend/remove")
@crossdomain
@ratelimit()
def delete_do_not_recommend():
    """ Remove a do not recommend entry specified artist/release/release-group/recording so that it can be recommended
    again. The endpoint accepts a json payload of the following format:

    .. code-block:: json

        {
            "entity": "<entity type>",
            "entity_mbid": "<mbid of the entity>"
        }

    Currently, the supported entity types are ``artist``, ``release``, ``release_group`` and ``recording``.

    :reqheader Authorization: Token <user token>
    :statuscode 200: feedback accepted.
    :statuscode 400: invalid JSON sent, see error message for details.
    :statuscode 401: invalid authorization. See error message for details.
    :resheader Content-Type: *application/json*
    """
    user, entity, entity_mbid, until = _parse_json_params()
    do_not_recommend.delete(db_conn, user["id"], entity, entity_mbid)
    return jsonify({"status": "ok"})


def _parse_json_params():
    user = validate_auth_header()
    data = request.json

    if "entity" not in data:
        raise APIBadRequest("Required `entity` key is missing")

    entity = data["entity"]
    if entity not in allowed_entity_types:
        raise APIBadRequest(f"Value '{entity}' for entity key is invalid. Allowed values are: {allowed_entity_types}")

    if "entity_mbid" not in data:
        raise APIBadRequest(f"Required `entity_mbid` is missing")

    entity_mbid = data["entity_mbid"]
    if not is_valid_uuid(entity_mbid):
        raise APIBadRequest(f"Value '{entity_mbid}' for entity_mbid key is not a valid uuid")

    # until field is optional add endpoint and not needed in remove endpoint
    until = data.get("until")
    if until is not None and (not isinstance(until, int) or until <= 0):
        raise APIBadRequest(f"Value '{until}' for until key is invalid. 'until' should be a positive integer")

    return user, entity, entity_mbid, until
