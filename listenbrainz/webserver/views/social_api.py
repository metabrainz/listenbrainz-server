from flask import Blueprint, current_app, jsonify, request

import listenbrainz.db.user as db_user
import listenbrainz.db.user_relationship as db_user_relationship
import listenbrainz.db.user_artist_relationship as db_user_artist_relationship
import listenbrainz.db.event_feed as db_event_feed
import listenbrainz.db.event_interaction as db_event_interaction
import listenbrainz.db.stats as db_stats
from data.model.user_entity import EntityRecord
from listenbrainz.webserver import db_conn, ts_conn

from listenbrainz.webserver.decorators import crossdomain
from listenbrainz.webserver.errors import APINotFound, APIInternalServerError, APIBadRequest, APIForbidden
from brainzutils.ratelimit import ratelimit
from listenbrainz.webserver.views.api_tools import validate_auth_header, is_valid_uuid, log_raise_400, \
    get_non_negative_param, DEFAULT_ITEMS_PER_GET, MAX_ITEMS_PER_GET
from listenbrainz.webserver.views.explore_api import _parse_event_window_args

social_api_bp = Blueprint('social_api_v1', __name__)


@social_api_bp.get("/user/<mb_username:user_name>/followers")
@crossdomain
@ratelimit()
def get_followers(user_name: str):
    """
    Fetch the list of followers of the user ``user_name``. Returns a JSON with an array of usernames like these:

    .. code-block:: json

        {
            "followers": ["rob", "mr_monkey", "..."],
            "user": "shivam-kapila"
        }

    :statuscode 200: Yay, you have data!
    :statuscode 404: User not found
    """
    user = db_user.get_by_mb_id(db_conn, user_name)

    if not user:
        raise APINotFound("User %s not found" % user_name)

    try:
        followers = db_user_relationship.get_followers_of_user(db_conn, user["id"])
        followers = [user["musicbrainz_id"] for user in followers]
    except Exception as e:
        current_app.logger.error("Error while trying to fetch followers: %s", str(e))
        raise APIInternalServerError("Something went wrong, please try again later")

    return jsonify({"followers": followers, "user": user["musicbrainz_id"]})


@social_api_bp.get("/user/<mb_username:user_name>/following")
@crossdomain
@ratelimit()
def get_following(user_name: str):
    """
    Fetch the list of users followed by the user ``user_name``. Returns a JSON with an array of usernames like these:

    .. code-block:: json

        {
            "following": ["rob", "mr_monkey", "..."],
            "user": "shivam-kapila"
        }

    :statuscode 200: Yay, you have data!
    :statuscode 404: User not found
    """
    user = db_user.get_by_mb_id(db_conn, user_name)

    if not user:
        raise APINotFound("User %s not found" % user_name)

    try:
        following = db_user_relationship.get_following_for_user(db_conn, user["id"])
        following = [user["musicbrainz_id"] for user in following]
    except Exception as e:
        current_app.logger.error("Error while trying to fetch following: %s", str(e))
        raise APIInternalServerError("Something went wrong, please try again later")

    return jsonify({"following": following, "user": user["musicbrainz_id"]})


@social_api_bp.post("/user/<mb_username:user_name>/follow")
@crossdomain
@ratelimit()
def follow_user(user_name: str):
    """
    Follow the user ``user_name``. A user token (found on  https://listenbrainz.org/settings/ ) must
    be provided in the Authorization header!

    :reqheader Authorization: Token <user token>
    :reqheader Content-Type: *application/json*
    :statuscode 200: Successfully followed the user ``user_name``.
    :statuscode 400:
                    - Already following the user ``user_name``.
                    - Trying to follow yourself.
    :statuscode 401: invalid authorization. See error message for details.
    :resheader Content-Type: *application/json*
    """
    current_user = validate_auth_header()
    user = db_user.get_by_mb_id(db_conn, user_name)

    if not user:
        raise APINotFound("User %s not found" % user_name)

    if user["musicbrainz_id"] == current_user["musicbrainz_id"]:
        raise APIBadRequest("Whoops, cannot follow yourself.")

    if db_user_relationship.is_following_user(db_conn, current_user["id"], user["id"]):
        raise APIBadRequest("%s is already following user %s" % (current_user["musicbrainz_id"], user["musicbrainz_id"]))

    try:
        db_user_relationship.insert(db_conn, current_user["id"], user["id"], "follow")
    except Exception as e:
        current_app.logger.error("Error while trying to insert a relationship: %s", str(e))
        raise APIInternalServerError("Something went wrong, please try again later")

    return jsonify({"status": "ok"})


@social_api_bp.post("/user/<mb_username:user_name>/unfollow")
@crossdomain
@ratelimit()
def unfollow_user(user_name: str):
    """
    Unfollow the user ``user_name``. A user token (found on  https://listenbrainz.org/settings/ ) must
    be provided in the Authorization header!

    :reqheader Authorization: Token <user token>
    :reqheader Content-Type: *application/json*
    :statuscode 200: Successfully unfollowed the user ``user_name``.
    :statuscode 401: invalid authorization. See error message for details.
    :resheader Content-Type: *application/json*
    """
    current_user = validate_auth_header()
    user = db_user.get_by_mb_id(db_conn, user_name)

    if not user:
        raise APINotFound("User %s not found" % user_name)

    try:
        db_user_relationship.delete(db_conn, current_user["id"], user["id"], "follow")
    except Exception as e:
        current_app.logger.error("Error while trying to delete a relationship: %s", str(e))
        raise APIInternalServerError("Something went wrong, please try again later")

    return jsonify({"status": "ok"})


@social_api_bp.post("/followed-artists/add")
@crossdomain
@ratelimit()
def follow_artist():
    """
    Follow the artist with the given ``artist_mbid``, sent in the request body as
    ``{"artist_mbid": "<artist_mbid>"}``. A user token (found on  https://listenbrainz.org/settings/ )
    must be provided in the Authorization header!

    :reqheader Authorization: Token <user token>
    :reqheader Content-Type: *application/json*
    :statuscode 200: Successfully followed the artist.
    :statuscode 400:
                    - Missing or invalid artist_mbid.
                    - Already following the artist.
    :statuscode 401: invalid authorization. See error message for details.
    :resheader Content-Type: *application/json*
    """
    current_user = validate_auth_header()

    data = request.json

    if "artist_mbid" not in data:
        log_raise_400("JSON document must contain artist_mbid", data)

    if not is_valid_uuid(data["artist_mbid"]):
        log_raise_400("artist_mbid %s is not valid" % data["artist_mbid"], data)

    if db_user_artist_relationship.is_following_artist(db_conn, current_user["id"], data["artist_mbid"]):
        raise APIBadRequest("%s is already following artist %s" % (current_user["musicbrainz_id"], data["artist_mbid"]))

    try:
        db_user_artist_relationship.insert(db_conn, current_user["id"], data["artist_mbid"], "follow")
    except Exception as e:
        current_app.logger.error("Error while trying to insert an artist relationship: %s", str(e))
        raise APIInternalServerError("Something went wrong, please try again later")

    return jsonify({"status": "ok"})


@social_api_bp.post("/followed-artists/remove")
@crossdomain
@ratelimit()
def unfollow_artist():
    """
    Unfollow the artist with the given ``artist_mbid``, sent in the request body as
    ``{"artist_mbid": "<artist_mbid>"}``. A user token (found on  https://listenbrainz.org/settings/ )
    must be provided in the Authorization header! Unfollowing an artist that is not followed does nothing.

    :reqheader Authorization: Token <user token>
    :reqheader Content-Type: *application/json*
    :statuscode 200: Successfully unfollowed the artist.
    :statuscode 400: Missing or invalid artist_mbid.
    :statuscode 401: invalid authorization. See error message for details.
    :resheader Content-Type: *application/json*
    """
    current_user = validate_auth_header()

    data = request.json

    if "artist_mbid" not in data:
        log_raise_400("JSON document must contain artist_mbid", data)

    if not is_valid_uuid(data["artist_mbid"]):
        log_raise_400("artist_mbid %s is not valid" % data["artist_mbid"], data)

    try:
        db_user_artist_relationship.delete(db_conn, current_user["id"], data["artist_mbid"], "follow")
    except Exception as e:
        current_app.logger.error("Error while trying to delete an artist relationship: %s", str(e))
        raise APIInternalServerError("Something went wrong, please try again later")

    return jsonify({"status": "ok"})


@social_api_bp.get("/user/<mb_username:user_name>/followed-artists")
@crossdomain
@ratelimit()
def get_followed_artists(user_name: str):
    """
    Fetch the list of artists followed by the user ``user_name``, most recently followed first. Returns a JSON like:

    .. code-block:: json

        {
            "followed_artists": ["<artist_mbid>", "..."],
            "user": "user_name",
            "count": 5,
            "offset": 0
        }

    :param count: The number of artists to return, at most 1000. Default 25.
    :param offset: The number of artists to skip from the beginning. Default 0.
    :statuscode 200: Yay, you have data!
    :statuscode 400: invalid count or offset passed.
    :statuscode 404: User not found
    """
    user = db_user.get_by_mb_id(db_conn, user_name)

    if not user:
        raise APINotFound("User %s not found" % user_name)

    count = get_non_negative_param("count", DEFAULT_ITEMS_PER_GET)
    count = min(count, MAX_ITEMS_PER_GET)

    offset = get_non_negative_param("offset", 0)

    try:
        artists = db_user_artist_relationship.get_followed_artist_mbids(db_conn, user["id"], count, offset)
    except Exception as e:
        current_app.logger.error("Error while trying to fetch followed artists: %s", str(e))
        raise APIInternalServerError("Something went wrong, please try again later")

    return jsonify({
        "followed_artists": [artist["artist_mbid"] for artist in artists],
        "user": user["musicbrainz_id"],
        "count": len(artists),
        "offset": offset,
    })


@social_api_bp.get("/user/<mb_username:user_name>/followed-artists/<artist_mbid>")
@crossdomain
@ratelimit()
def get_artist_follow_status(user_name: str, artist_mbid: str):
    """
    Check whether the user ``user_name`` follows the artist with the given ``artist_mbid``. Returns a JSON like:

    .. code-block:: json

        {
            "artist_mbid": "<artist_mbid>",
            "following": true,
            "user": "user_name"
        }

    :statuscode 200: Yay, you have data!
    :statuscode 400: invalid artist_mbid passed.
    :statuscode 404: User not found
    """
    user = db_user.get_by_mb_id(db_conn, user_name)

    if not user:
        raise APINotFound("User %s not found" % user_name)

    if not is_valid_uuid(artist_mbid):
        log_raise_400("artist_mbid %s is not valid" % artist_mbid)

    try:
        following = db_user_artist_relationship.is_following_artist(db_conn, user["id"], artist_mbid)
    except Exception as e:
        current_app.logger.error("Error while trying to check an artist relationship: %s", str(e))
        raise APIInternalServerError("Something went wrong, please try again later")

    return jsonify({
        "artist_mbid": artist_mbid,
        "following": following,
        "user": user["musicbrainz_id"],
    })


@social_api_bp.get("/user/<mb_username:user_name>/events/followed-artists")
@crossdomain
@ratelimit()
def get_events_for_followed_artists(user_name: str):
    """
    Fetch events for all artists followed by the user ``user_name``, ordered chronologically. By default
    these are the upcoming events, and the ``days``, ``past`` and ``future`` parameters choose other
    dates. Returns a JSON like:

    .. code-block:: json

        {
            "payload": {
                "events": ["..."],
                "count": 10,
                "offset": 0,
                "user": "shivam-kapila"
            }
        }

    The events list is empty if the user follows no artists, or if none of the artists
    they follow have events in the chosen dates.

    Each event has the same fields as the values returned by ``GET /1/explore/events``, including ``performers``,
    ``genres`` and ``listen_count``.
    An event counts as upcoming until its end date, or its begin date if it has no end date, has passed.
    A missing month or day counts as the first of the year or month, and events with no date are left out.

    :param count: The number of events to return, at most 1000. Default 25.
    :param offset: The number of events to skip from the beginning. Default 0.
    :param days: The number of days the window reaches in each direction, at most 365, or at most 90 when
                 ``past`` is true. Default no limit.
    :param past: Whether to show events in the past. Needs ``days``. Default False.
    :param future: Whether to show events in the future. Default True.
    :param cancelled: Whether to show cancelled events. Default False.
    :statuscode 200: Yay, you have data!
    :statuscode 400: invalid count, offset, days, past, future or cancelled passed.
    :statuscode 404: User not found
    """
    user = db_user.get_by_mb_id(db_conn, user_name)

    if not user:
        raise APINotFound("User %s not found" % user_name)

    count = get_non_negative_param("count", DEFAULT_ITEMS_PER_GET)
    count = min(count, MAX_ITEMS_PER_GET)

    offset = get_non_negative_param("offset", 0)

    days, past, future, cancelled = _parse_event_window_args()

    try:
        artists = db_user_artist_relationship.get_all_followed_artist_mbids(db_conn, user["id"])
        artist_mbids = [artist["artist_mbid"] for artist in artists]
        events = db_event_feed.get_upcoming_events_for_artists(
            ts_conn, artist_mbids, count, offset, days=days, past=past, future=future, cancelled=cancelled
        )
        events = db_event_feed.add_performers_to_events(ts_conn, events)
    except Exception as e:
        current_app.logger.error("Error while trying to fetch events for followed artists: %s", str(e))
        raise APIInternalServerError("Something went wrong, please try again later")

    return jsonify({
        "payload": {
            "events": events,
            "count": len(events),
            "offset": offset,
            "user": user["musicbrainz_id"],
        }
    })


@social_api_bp.get("/user/<mb_username:user_name>/events/listened-artists")
@crossdomain
@ratelimit()
def get_events_for_listened_artists(user_name: str):
    """
    Fetch events for the artists the user ``user_name`` has listened to the most, going by their all time
    top artists statistics, ordered chronologically. By default these are the upcoming events, and the
    ``days``, ``past`` and ``future`` parameters choose other dates. Returns a JSON like:

    .. code-block:: json

        {
            "payload": {
                "events": ["..."],
                "count": 10,
                "offset": 0,
                "user": "shivam-kapila"
            }
        }

    The events list is empty if the user's statistics haven't been calculated yet, or if none of their top
    artists have events in the chosen dates.

    Each event has the same fields as the values returned by ``GET /1/explore/events``, and also
    ``user_listen_count``, the highest number of times the user has listened to any of its performers.
    An event counts as upcoming until its end date, or its begin date if it has no end date, has passed.
    A missing month or day counts as the first of the year or month, and events with no date are left out.

    :param count: The number of events to return, at most 1000. Default 25.
    :param offset: The number of events to skip from the beginning. Default 0.
    :param days: The number of days the window reaches in each direction, at most 365, or at most 90 when
                 ``past`` is true. Default no limit.
    :param past: Whether to show events in the past. Needs ``days``. Default False.
    :param future: Whether to show events in the future. Default True.
    :param cancelled: Whether to show cancelled events. Default False.
    :statuscode 200: Yay, you have data!
    :statuscode 400: invalid count, offset, days, past, future or cancelled passed.
    :statuscode 404: User not found
    """
    user = db_user.get_by_mb_id(db_conn, user_name)

    if not user:
        raise APINotFound("User %s not found" % user_name)

    count = get_non_negative_param("count", DEFAULT_ITEMS_PER_GET)
    count = min(count, MAX_ITEMS_PER_GET)

    offset = get_non_negative_param("offset", 0)

    days, past, future, cancelled = _parse_event_window_args()

    try:
        stats = db_stats.get(user["id"], "artists", "all_time", EntityRecord)
        listen_counts = {}
        if stats is not None:
            for artist in stats.data:
                if artist.artist_mbid:
                    listen_counts[artist.artist_mbid] = artist.listen_count

        events = db_event_feed.get_upcoming_events_for_artists(
            ts_conn, list(listen_counts), count, offset, days=days, past=past, future=future, cancelled=cancelled
        )
        events = db_event_feed.add_performers_to_events(ts_conn, events)
        for event in events:
            event["user_listen_count"] = max(
                (listen_counts.get(p["artist_mbid"], 0) for p in event["performers"]), default=0
            )
    except Exception as e:
        current_app.logger.error("Error while trying to fetch events for listened artists: %s", str(e))
        raise APIInternalServerError("Something went wrong, please try again later")

    return jsonify({
        "payload": {
            "events": events,
            "count": len(events),
            "offset": offset,
            "user": user["musicbrainz_id"],
        }
    })


@social_api_bp.post("/watched-events/add")
@crossdomain
@ratelimit()
def watch_event():
    """
    Watch the event with the given ``event_mbid``, sent in the request body as
    ``{"event_mbid": "<event_mbid>"}``. A user token (found on  https://listenbrainz.org/settings/ )
    must be provided in the Authorization header!

    :reqheader Authorization: Token <user token>
    :reqheader Content-Type: *application/json*
    :statuscode 200: Successfully watched the event.
    :statuscode 400:
                    - Missing or invalid event_mbid.
                    - Already watching the event.
    :statuscode 401: invalid authorization. See error message for details.
    :resheader Content-Type: *application/json*
    """
    current_user = validate_auth_header()

    data = request.json

    if "event_mbid" not in data:
        log_raise_400("JSON document must contain event_mbid", data)

    if not is_valid_uuid(data["event_mbid"]):
        log_raise_400("event_mbid %s is not valid" % data["event_mbid"], data)

    if db_event_interaction.is_watching_event(db_conn, current_user["id"], data["event_mbid"]):
        raise APIBadRequest("%s is already watching event %s" % (current_user["musicbrainz_id"], data["event_mbid"]))

    try:
        db_event_interaction.watch_event(db_conn, current_user["id"], data["event_mbid"])
    except Exception as e:
        current_app.logger.error("Error while trying to watch an event: %s", str(e))
        raise APIInternalServerError("Something went wrong, please try again later")

    return jsonify({"status": "ok"})


@social_api_bp.post("/watched-events/remove")
@crossdomain
@ratelimit()
def unwatch_event():
    """
    Stop watching the event with the given ``event_mbid``, sent in the request body as
    ``{"event_mbid": "<event_mbid>"}``. A user token (found on  https://listenbrainz.org/settings/ )
    must be provided in the Authorization header! Unwatching an event that is not watched does nothing.

    :reqheader Authorization: Token <user token>
    :reqheader Content-Type: *application/json*
    :statuscode 200: Successfully stopped watching the event.
    :statuscode 400: Missing or invalid event_mbid.
    :statuscode 401: invalid authorization. See error message for details.
    :resheader Content-Type: *application/json*
    """
    current_user = validate_auth_header()

    data = request.json

    if "event_mbid" not in data:
        log_raise_400("JSON document must contain event_mbid", data)

    if not is_valid_uuid(data["event_mbid"]):
        log_raise_400("event_mbid %s is not valid" % data["event_mbid"], data)

    try:
        db_event_interaction.unwatch_event(db_conn, current_user["id"], data["event_mbid"])
    except Exception as e:
        current_app.logger.error("Error while trying to unwatch an event: %s", str(e))
        raise APIInternalServerError("Something went wrong, please try again later")

    return jsonify({"status": "ok"})


@social_api_bp.get("/user/<mb_username:user_name>/watched-events")
@crossdomain
@ratelimit()
def get_watched_events(user_name: str):
    """
    Fetch the list of events watched by the user ``user_name``, most recently watched first. Only ``user_name`` and
    users who follow ``user_name`` and are followed back can see this. A user token (found on
    https://listenbrainz.org/settings/ ) must be provided in the Authorization header! Returns a JSON like:

    .. code-block:: json

        {
            "watched_events": ["<event_mbid>", "..."],
            "user": "user_name",
            "count": 5,
            "offset": 0
        }

    :param count: The number of events to return, at most 1000. Default 25.
    :param offset: The number of events to skip from the beginning. Default 0.
    :reqheader Authorization: Token <user token>
    :statuscode 200: Yay, you have data!
    :statuscode 400: invalid count or offset passed.
    :statuscode 401: Unauthorized, you do not have permission to view this user's watched events.
    :statuscode 403: Forbidden, you do not have permission to view this user's watched events.
    :statuscode 404: User not found
    """
    current_user = validate_auth_header()
    user = db_user.get_by_mb_id(db_conn, user_name)

    if not user:
        raise APINotFound("User %s not found" % user_name)

    if user["musicbrainz_id"] != current_user["musicbrainz_id"]:
        if not (db_user_relationship.is_following_user(db_conn, current_user["id"], user["id"])
                and db_user_relationship.is_following_user(db_conn, user["id"], current_user["id"])):
            raise APIForbidden("You don't have permissions to view this user's watched events.")

    count = get_non_negative_param("count", DEFAULT_ITEMS_PER_GET)
    count = min(count, MAX_ITEMS_PER_GET)

    offset = get_non_negative_param("offset", 0)

    try:
        events = db_event_interaction.get_watched_events(db_conn, user["id"], count, offset)
    except Exception as e:
        current_app.logger.error("Error while trying to fetch watched events: %s", str(e))
        raise APIInternalServerError("Something went wrong, please try again later")

    return jsonify({
        "watched_events": [event["event_mbid"] for event in events],
        "user": user["musicbrainz_id"],
        "count": len(events),
        "offset": offset,
    })


@social_api_bp.get("/user/<mb_username:user_name>/watched-events/<event_mbid>")
@crossdomain
@ratelimit()
def get_event_watch_status(user_name: str, event_mbid: str):
    """
    Check whether the user ``user_name`` is watching the event with the given ``event_mbid``. Only ``user_name`` and
    users who follow ``user_name`` and are followed back can see this. A user token (found on
    https://listenbrainz.org/settings/ ) must be provided in the Authorization header! Returns a JSON like:

    .. code-block:: json

        {
            "event_mbid": "<event_mbid>",
            "watching": true,
            "user": "user_name"
        }

    :reqheader Authorization: Token <user token>
    :statuscode 200: Yay, you have data!
    :statuscode 400: invalid event_mbid passed.
    :statuscode 401: Unauthorized, you do not have permission to view this user's watched events.
    :statuscode 403: Forbidden, you do not have permission to view this user's watched events.
    :statuscode 404: User not found
    """
    current_user = validate_auth_header()
    user = db_user.get_by_mb_id(db_conn, user_name)

    if not user:
        raise APINotFound("User %s not found" % user_name)

    if user["musicbrainz_id"] != current_user["musicbrainz_id"]:
        if not (db_user_relationship.is_following_user(db_conn, current_user["id"], user["id"])
                and db_user_relationship.is_following_user(db_conn, user["id"], current_user["id"])):
            raise APIForbidden("You don't have permissions to view this user's watched events.")

    if not is_valid_uuid(event_mbid):
        log_raise_400("event_mbid %s is not valid" % event_mbid)

    try:
        watching = db_event_interaction.is_watching_event(db_conn, user["id"], event_mbid)
    except Exception as e:
        current_app.logger.error("Error while trying to check an event watch: %s", str(e))
        raise APIInternalServerError("Something went wrong, please try again later")

    return jsonify({
        "event_mbid": event_mbid,
        "watching": watching,
        "user": user["musicbrainz_id"],
    })
