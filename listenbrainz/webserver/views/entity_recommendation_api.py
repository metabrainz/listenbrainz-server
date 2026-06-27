from brainzutils.ratelimit import ratelimit
from flask import Blueprint, jsonify, request

import listenbrainz.db.user as db_user
from listenbrainz.db import entity_recommendation
from listenbrainz.webserver import db_conn

from listenbrainz.webserver.decorators import crossdomain
from listenbrainz.webserver.errors import APINotFound, APIBadRequest
from listenbrainz.webserver.views.api_tools import get_non_negative_param, DEFAULT_ITEMS_PER_GET, MAX_ITEMS_PER_GET, \
    validate_auth_header, is_valid_uuid

allowed_entity_types = ['artist', 'release_group', 'release', 'recording']

entity_recommendation_api_bp = Blueprint('entity_recommendation_api_v1', __name__)


@entity_recommendation_api_bp.get("/user/<mb_username:user_name>/entity-recommendations")
@crossdomain
@ratelimit()
def get_entity_recommendations(user_name):
    """
    Get entity recommendations made by the user given by ``user_name``. The format for the JSON returned
    is as follows:

    .. code-block:: json

        {
            "count": 1,
            "offset": 0,
            "total_count": 5,
            "results": [
                {
                    "source_entity_type": "recording",
                    "source_entity_mbid": "bdc9e5af-54e2-4dde-9d8f-87b04f00b89c",
                    "target_entity_type": "recording",
                    "target_entity_mbid": "a6081bc1-2a76-4984-b21f-38bc3dcca3a5",
                    "specificity_score": 8,
                    "blurb": "If you like this song, you'll love this one!",
                    "created": 1668526511
                }
            ],
            "user_id": "lucifer"
        }

    :param count: Optional, number of entity recommendation items to return.
        Default: :data:`~webserver.views.api.DEFAULT_ITEMS_PER_GET` Max: :data:`~webserver.views.api.MAX_ITEMS_PER_GET`.
    :type count: ``int``
    :param offset: Optional, number of items to skip from the beginning, for pagination.
        Ex. An offset of 5 means the top 5 items will be skipped, defaults to 0.
    :type offset: ``int``
    :statuscode 200: Yay, you have data!
    :statuscode 404: User not found.
    :resheader Content-Type: *application/json*
    """
    offset = get_non_negative_param("offset", default=0)
    count = get_non_negative_param("count", default=DEFAULT_ITEMS_PER_GET)
    count = min(count, MAX_ITEMS_PER_GET)

    user = db_user.get_by_mb_id(db_conn, user_name)
    if user is None:
        raise APINotFound("Cannot find user: %s" % user_name)

    results = entity_recommendation.get(db_conn, user["id"], count, offset)
    total_count = entity_recommendation.get_total_count(db_conn, user["id"])

    return jsonify({
        "offset": offset,
        "count": len(results),
        "total_count": total_count,
        "user_id": user_name,
        "results": results
    })


@entity_recommendation_api_bp.post("/entity-recommendation/add")
@crossdomain
@ratelimit()
def add_entity_recommendation():
    """ Submit an entity-to-entity recommendation. The endpoint accepts a JSON payload of the following format:

    .. code-block:: json

        {
            "source_entity_type": "<entity type>",
            "source_entity_mbid": "<mbid of the source entity>",
            "target_entity_type": "<entity type>",
            "target_entity_mbid": "<mbid of the target entity>",
            "blurb": "Optional text explaining the recommendation"
        }

    Currently, the supported entity types are ``artist``, ``release_group``, ``release`` and ``recording``.

    The specificity score is computed automatically based on the entity types. More specific entity types
    (e.g. recordings) yield higher scores. A user can make at most 10 recommendations per day.

    :reqheader Authorization: Token <user token>
    :statuscode 200: recommendation accepted.
    :statuscode 400: invalid JSON sent, see error message for details.
    :statuscode 401: invalid authorization. See error message for details.
    :resheader Content-Type: *application/json*
    """
    user = validate_auth_header()
    data = request.json

    source_entity_type, source_entity_mbid = _parse_entity_fields(data, "source")
    target_entity_type, target_entity_mbid = _parse_entity_fields(data, "target")
    blurb = data.get("blurb")

    if blurb is not None and not isinstance(blurb, str):
        raise APIBadRequest("'blurb' must be a string")
    if blurb is not None and len(blurb) > 1000:
        raise APIBadRequest("'blurb' must be at most 1000 characters")

    try:
        entity_recommendation.insert(
            db_conn, user["id"],
            source_entity_type, source_entity_mbid,
            target_entity_type, target_entity_mbid,
            blurb
        )
    except ValueError as e:
        raise APIBadRequest(str(e))

    return jsonify({"status": "ok"})


@entity_recommendation_api_bp.post("/entity-recommendation/remove")
@crossdomain
@ratelimit()
def delete_entity_recommendation():
    """ Remove an entity recommendation. The endpoint accepts a JSON payload of the following format:

    .. code-block:: json

        {
            "source_entity_type": "<entity type>",
            "source_entity_mbid": "<mbid of the source entity>",
            "target_entity_type": "<entity type>",
            "target_entity_mbid": "<mbid of the target entity>"
        }

    Currently, the supported entity types are ``artist``, ``release_group``, ``release`` and ``recording``.

    :reqheader Authorization: Token <user token>
    :statuscode 200: recommendation removed.
    :statuscode 400: invalid JSON sent, see error message for details.
    :statuscode 401: invalid authorization. See error message for details.
    :resheader Content-Type: *application/json*
    """
    user = validate_auth_header()
    data = request.json

    source_entity_type, source_entity_mbid = _parse_entity_fields(data, "source")
    target_entity_type, target_entity_mbid = _parse_entity_fields(data, "target")

    entity_recommendation.delete(
        db_conn, user["id"],
        source_entity_type, source_entity_mbid,
        target_entity_type, target_entity_mbid
    )
    return jsonify({"status": "ok"})


def _parse_entity_fields(data, prefix):
    """Parse and validate entity type and MBID fields from request data.

    Args:
        data: the request JSON data
        prefix: 'source' or 'target'

    Returns:
        tuple of (entity_type, entity_mbid)
    """
    type_key = f"{prefix}_entity_type"
    mbid_key = f"{prefix}_entity_mbid"

    if type_key not in data:
        raise APIBadRequest(f"Required `{type_key}` key is missing")

    entity_type = data[type_key]
    if entity_type not in allowed_entity_types:
        raise APIBadRequest(
            f"Value '{entity_type}' for {type_key} key is invalid. Allowed values are: {allowed_entity_types}"
        )

    if mbid_key not in data:
        raise APIBadRequest(f"Required `{mbid_key}` key is missing")

    entity_mbid = data[mbid_key]
    if not is_valid_uuid(entity_mbid):
        raise APIBadRequest(f"Value '{entity_mbid}' for {mbid_key} key is not a valid uuid")

    return entity_type, entity_mbid
