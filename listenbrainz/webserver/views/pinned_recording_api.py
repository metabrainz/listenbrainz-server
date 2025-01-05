import listenbrainz.db.user as db_user
import listenbrainz.db.pinned_recording as db_pinned_rec

from flask import Blueprint, current_app, jsonify, request

from listenbrainz.db.msid_mbid_mapping import fetch_track_metadata_for_items
from listenbrainz.webserver import db_conn, ts_conn
from listenbrainz.webserver.decorators import crossdomain
from listenbrainz.webserver.errors import APIInternalServerError, APINotFound
from brainzutils.ratelimit import ratelimit
from listenbrainz.webserver.views.api_tools import (
    log_raise_400,
    DEFAULT_ITEMS_PER_GET,
    MAX_ITEMS_PER_GET,
    get_non_negative_param,
    validate_auth_header,
)
from listenbrainz.db.model.pinned_recording import WritablePinnedRecording
from pydantic import ValidationError

pinned_recording_api_bp = Blueprint("pinned_rec_api_bp_v1", __name__)


@pinned_recording_api_bp.post("/pin")
@crossdomain
@ratelimit()
def pin_recording_for_user():
    """
    Pin a recording for user. A user token (found on  https://listenbrainz.org/settings/)
    must be provided in the Authorization header! Each request should contain only one pinned recording item in the payload.

    The format of the JSON to be POSTed to this endpoint should look like the following:

    .. code-block:: json

        {
            "recording_msid": "40ef0ae1-5626-43eb-838f-1b34187519bf",
            "recording_mbid": "<this field is optional>",
            "blurb_content": "Wow..",
            "pinned_until": 1824001816
        }

    :reqheader Authorization: Token <user token>
    :statuscode 200: feedback accepted.
    :statuscode 400: invalid JSON sent, see error message for details.
    :statuscode 401: invalid authorization. See error message for details.
    :resheader Content-Type: *application/json*
    """
    user = validate_auth_header()

    data = request.json

    if "recording_msid" not in data and "recording_mbid" not in data:
        log_raise_400("JSON document must contain either recording_msid or recording_mbid", data)

    try:
        recording_to_pin = WritablePinnedRecording(
            user_id=user["id"],
            recording_msid=data["recording_msid"] if "recording_msid" in data else None,
            recording_mbid=data["recording_mbid"] if "recording_mbid" in data else None,
            blurb_content=data["blurb_content"] if "blurb_content" in data else None,
            pinned_until=data["pinned_until"] if "pinned_until" in data else None,
        )
    except ValidationError as e:
        log_raise_400("Invalid JSON document submitted: %s" % str(e).replace("\n ", ":").replace("\n", " "), data)

    try:
        recording_to_pin_with_id = db_pinned_rec.pin(db_conn, recording_to_pin)
    except Exception as e:
        current_app.logger.error("Error while inserting pinned track record: {}".format(e))
        raise APIInternalServerError("Something went wrong. Please try again.")

    return jsonify({"pinned_recording": recording_to_pin_with_id.to_api()})


@pinned_recording_api_bp.post("/pin/unpin")
@crossdomain
@ratelimit()
def unpin_recording_for_user():
    """
    Unpins the currently active pinned recording for the user. A user token (found on  https://listenbrainz.org/settings/)
    must be provided in the Authorization header!

    :reqheader Authorization: Token <user token>
    :statuscode 200: recording unpinned.
    :statuscode 401: invalid authorization. See error message for details.
    :statuscode 404: could not find the active recording to unpin for the user. See error message for details.
    :resheader Content-Type: *application/json*
    """
    user = validate_auth_header()

    try:
        recording_unpinned = db_pinned_rec.unpin(db_conn, user["id"])
    except Exception as e:
        current_app.logger.error("Error while unpinning recording for user: {}".format(e))
        raise APIInternalServerError("Something went wrong. Please try again.")

    if recording_unpinned is False:
        raise APINotFound("Cannot find an active pinned recording for user '%s' to unpin" % (user["musicbrainz_id"]))

    return jsonify({"status": "ok"})


@pinned_recording_api_bp.post("/pin/delete/<row_id>")
@crossdomain
@ratelimit()
def delete_pin_for_user(row_id):
    """
    Deletes the pinned recording with given ``row_id`` from the server.
    A user token (found on  https://listenbrainz.org/settings/) must be provided in the Authorization header!

    :reqheader Authorization: Token <user token>
    :param row_id: the row_id of the pinned recording that should be deleted.
    :type row_id: ``int``
    :statuscode 200: recording unpinned.
    :statuscode 401: invalid authorization. See error message for details.
    :statuscode 404: the requested row_id for the user was not found.
    :resheader Content-Type: *application/json*
    """
    user = validate_auth_header()

    try:
        recording_deleted = db_pinned_rec.delete(db_conn, row_id, user["id"])
    except Exception as e:
        current_app.logger.error("Error while unpinning recording for user: {}".format(e))
        raise APIInternalServerError("Something went wrong. Please try again.")

    if recording_deleted is False:
        raise APINotFound("Cannot find pin with row_id '%s' for user '%s'" % (row_id, user["musicbrainz_id"]))

    return jsonify({"status": "ok"})


@pinned_recording_api_bp.get("/<user_name>/pins")
@crossdomain
@ratelimit()
def get_pins_for_user(user_name):
    """
    Get a list of all recordings ever pinned by a user with given ``user_name`` in descending order of the time
    they were originally pinned. The JSON returned by the API will look like the following:

    .. code-block:: json

        {
            "count": 10,
            "offset": 0,
            "pinned_recordings": [
                {
                    "blurb_content": "Awesome recording!",
                    "created": 1623997168,
                    "row_id": 10,
                    "pinned_until": 1623997485,
                    "recording_mbid": null,
                    "recording_msid": "fd7d9162-a284-4a10-906c-faae4f1e166b"
                    "track_metadata": {
                        "artist_name": "Rick Astley",
                        "track_name": "Never Gonna Give You Up"
                    }
                },
                "-- more pinned recording items here ---"
            ],
            "total_count": 10,
            "user_name": "-- the MusicBrainz ID of the user --"
        }

    :param user_name: the MusicBrainz ID of the user whose pin track history requested.
    :type user_name: ``str``
    :param count: Optional, number of pinned recording items to return,
        Default: :data:`~webserver.views.api.DEFAULT_ITEMS_PER_GET`
        Max: :data:`~webserver.views.api.MAX_ITEMS_PER_GET`
    :type count: ``int``
    :param offset: Optional, number of pinned recording items to skip from the beginning, for pagination.
        Ex. An offset of 5 means the most recent 5 pinned recordings from the user will be skipped, defaults to 0
    :type offset: ``int``
    :statuscode 200: Yay, you have data!
    :statuscode 400: Invalid query parameters. See error message for details.
    :statuscode 404: The requested user was not found.
    :resheader Content-Type: *application/json*
    """
    offset = get_non_negative_param("offset", default=0)
    count = get_non_negative_param("count", default=DEFAULT_ITEMS_PER_GET)

    count = min(count, MAX_ITEMS_PER_GET)

    user = db_user.get_by_mb_id(db_conn, user_name)
    if user is None:
        raise APINotFound("Cannot find user: %s" % user_name)

    try:
        pinned_recordings = db_pinned_rec.get_pin_history_for_user(
            db_conn, user_id=user["id"], count=count, offset=offset
        )
    except Exception as e:
        current_app.logger.error("Error while retrieving pins for user: {}".format(e))
        raise APIInternalServerError("Something went wrong. Please try again.")

    pinned_recordings = fetch_track_metadata_for_items(ts_conn, pinned_recordings)
    pinned_recordings = [pin.to_api() for pin in pinned_recordings]
    total_count = db_pinned_rec.get_pin_count_for_user(db_conn, user_id=user["id"])

    return jsonify(
        {
            "pinned_recordings": pinned_recordings,
            "total_count": total_count,
            "count": len(pinned_recordings),
            "offset": offset,
            "user_name": user_name,
        }
    )


@pinned_recording_api_bp.get("/<user_name>/pins/following")
@crossdomain
@ratelimit()
def get_pins_for_user_following(user_name):
    """
    Get a list containing the active pinned recordings for all users in a user's ``user_name``
    following list. The returned pinned recordings are sorted in descending order of the time they were pinned.
    The JSON returned by the API will look like the following:

    .. code-block:: json

        {
            "count": 1,
            "offset": 0,
            "pinned_recordings": [
                {
                "blurb_content": "Spectacular recording!",
                "created": 1624000841,
                "row_id": 1,
                "pinned_until": 1624605641,
                "recording_mbid": null,
                "recording_msid": "40ef0ae1-5626-43eb-838f-1b34187519bf",
                "track_metadata": {
                    "artist_name": "Rick Astley",
                    "track_name": "Never Gonna Give You Up"
                },
                "user_name": "-- the MusicBrainz ID of the user who pinned this recording --"
                },
                "-- more pinned recordings from different users here ---"
            ],
            "user_name": "-- the MusicBrainz ID of the original user --"
        }

    :param user_name: the MusicBrainz ID of the user whose followed user's pinned recordings are being requested.
    :type user_name: ``str``
    :param count: Optional, number of pinned recording items to return,
        Default: :data:`~webserver.views.api.DEFAULT_ITEMS_PER_GET`
        Max: :data:`~webserver.views.api.MAX_ITEMS_PER_GET`
    :type count: ``int``
    :param offset: Optional, number of pinned recording items to skip from the beginning, for pagination.
        Ex. An offset of 5 means the most recent pinned recordings from the first 5 users will be skipped, defaults to 0
    :type offset: ``int``
    :statuscode 200: Yay, you have data!
    :statuscode 400: Invalid query parameters. See error message for details.
    :statuscode 404: The requested user was not found.
    :resheader Content-Type: *application/json*
    """

    count = get_non_negative_param("count", default=DEFAULT_ITEMS_PER_GET)
    offset = get_non_negative_param("offset", default=0)

    count = min(count, MAX_ITEMS_PER_GET)

    user = db_user.get_by_mb_id(db_conn, user_name)
    if user is None:
        raise APINotFound("Cannot find user: %s" % user_name)

    pinned_recordings = db_pinned_rec.get_pins_for_user_following(
        db_conn, user_id=user["id"], count=count, offset=offset
    )
    pinned_recordings = fetch_track_metadata_for_items(ts_conn, pinned_recordings)
    pinned_recordings = [pin.to_api() for pin in pinned_recordings]

    return jsonify(
        {
            "pinned_recordings": pinned_recordings,
            "count": len(pinned_recordings),
            "offset": offset,
            "user_name": user_name,
        }
    )


@pinned_recording_api_bp.get("/<user_name>/pins/current")
@crossdomain
@ratelimit()
def get_current_pin_for_user(user_name):
    """
    Get the currently pinned recording by a user with given ``user_name``. The JSON returned by the API will look
    like the following:

    .. code-block:: json

        {
            "pinned_recording": {
                "blurb_content": "Awesome recording!",
                "created": 1623997168,
                "row_id": 10,
                "pinned_until": 1623997485,
                "recording_mbid": null,
                "recording_msid": "fd7d9162-a284-4a10-906c-faae4f1e166b"
                "track_metadata": {
                    "artist_name": "Rick Astley",
                    "track_name": "Never Gonna Give You Up"
                }
            },
            "user_name": "-- the MusicBrainz ID of the user --"
        }


    If there is no current pin for the user, "pinned_recording" field will be null.

    :param user_name: the MusicBrainz ID of the user whose pin track history requested.
    :type user_name: ``str``
    :statuscode 200: Yay, you have data!
    :statuscode 404: The requested user was not found.
    :resheader Content-Type: *application/json*
    """
    user = db_user.get_by_mb_id(db_conn, user_name)
    if user is None:
        raise APINotFound("Cannot find user: %s" % user_name)

    pin = db_pinned_rec.get_current_pin_for_user(db_conn, user_id=user.id)
    if pin:
        pin = fetch_track_metadata_for_items(ts_conn, [pin])[0].to_api()

    return jsonify({
        "pinned_recording": pin,
        "user_name": user_name,
    })


@pinned_recording_api_bp.post("/pin/update/<row_id>")
@crossdomain
@ratelimit()
def update_blurb_content_pinned_recording(row_id):
    """
    Updates the blurb content of a pinned recording for the user. A user token (found on  https://listenbrainz.org/settings/)
    must be provided in the Authorization header! Each request should contain only one pinned recording item in the payload.

    The format of the JSON to be POSTed to this endpoint should look like the following:

    .. code-block:: json

        {
            "blurb_content": "Wow..",
        }

    :reqheader Authorization: Token <user token>
    :statuscode 200: feedback accepted.
    :statuscode 400: invalid JSON sent, see error message for details.
    :statuscode 401: invalid authorization. See error message for details.
    :resheader Content-Type: *application/json*
    """
    validate_auth_header()

    data = request.json
    try:
        row_id = int(row_id)
    except ValueError:
        log_raise_400("Invalid row_id provided")
    if "blurb_content" not in data:
        log_raise_400("JSON document must contain blurb_content", data)

    try:
        blurb_content = data["blurb_content"]
    except ValidationError as e:
        log_raise_400("Invalid JSON document submitted: %s" % str(e).replace("\n ", ":").replace("\n", " "), data)

    try:
        status = db_pinned_rec.update_comment(db_conn, row_id, blurb_content)
    except Exception as e:
        current_app.logger.error("Error while inserting pinned track record: {}".format(e))
        raise APIInternalServerError("Something went wrong. Please try again.")

    return jsonify({"status": status})
