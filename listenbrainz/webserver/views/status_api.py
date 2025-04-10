from datetime import datetime
from flask import Blueprint, request, jsonify, current_app
from time import time

from kombu import Connection, Queue, Exchange
from kombu.exceptions import KombuError

from listenbrainz.webserver.decorators import crossdomain
from listenbrainz.webserver.errors import APIBadRequest, APINotFound
from brainzutils.ratelimit import ratelimit
from brainzutils import cache
from listenbrainz.webserver import db_conn, ts_conn
from listenbrainz.db.playlist import get_recommendation_playlists_for_user
import listenbrainz.db.dump as db_dump
import listenbrainz.db.stats as db_stats
from listenbrainz.webserver.views.stats_api import get_entity_stats_last_updated

STATUS_PREFIX = 'listenbrainz.status'  # prefix used in key to cache status
CACHE_TIME = 60 * 60  # time in seconds we cache the fetched data
DUMP_CACHE_TIME = 24 * 60 * 60  # time in seconds we cache the dump check
LISTEN_COUNT_CACHE_TIME = 5 * 60  # time in seconds we cache the listen count
PLAYLIST_CACHE_TIME = 24 * 30 * 60  # time in seconds we cache latest playlist timestamp
# See RECOMMENDATION_PATCHES in listenbrainz.db.playlist for a full list of patches
MONITORED_PLAYLIST_PATCHES = ('daily-jams',
                              'weekly-jams',
                              'weekly-exploration')
status_api_bp = Blueprint("status_api_v1", __name__)


@status_api_bp.get("/get-dump-info")
@crossdomain
@ratelimit()
def get_dump_info():
    """
    Get information about ListenBrainz data dumps.
    You need to pass the `id` parameter in a GET request to get data about that particular
    dump.

    .. code-block:: json

        {
            "id": 1,
            "timestamp": "20190625-165900"
        }

    :query id: Integer specifying the ID of the dump, if not provided, the endpoint returns information about the latest data dump.
    :statuscode 200: You have data.
    :statuscode 400: You did not provide a valid dump ID. See error message for details.
    :statuscode 404: Dump with given ID does not exist.
    :resheader Content-Type: *application/json*
    """

    dump_id = request.args.get("id")
    if dump_id is None:
        try:
            dump = db_dump.get_dump_entries()[0]  # return the latest dump
        except IndexError:
            raise APINotFound("No dump entry exists.")
    else:
        try:
            dump_id = int(dump_id)
        except ValueError:
            raise APIBadRequest("The `id` parameter needs to be an integer.")
        dump = db_dump.get_dump_entry(dump_id)
        if dump is None:
            raise APINotFound("No dump exists with ID: %d" % dump_id)

    return jsonify({
        "id": dump["id"],
        "timestamp": _convert_timestamp_to_string_dump_format(dump["created"]),
        "dump_type": dump["dump_type"],
    })


def _convert_timestamp_to_string_dump_format(timestamp):
    """Convert datetime object to string.

    The string is the same format as the format in the file name.

    Args:
        timestamp (datetime): the datetime obj to be converted

    Returns:
        String of the format "20190625-170100"
    """
    return timestamp.strftime("%Y%m%d-%H%M%S")


def get_stats_timestamp():
    """ Check to see when statistics were last generated for a "random" user. Returns unix epoch timestamp"""

    cache_key = STATUS_PREFIX + ".stats-timestamp"
    last_updated = cache.get(cache_key)
    if last_updated is None:
        last_updated = get_entity_stats_last_updated("rob", "artists", "total_artist_count")
        if last_updated is None:
            return None

        cache.set(cache_key, last_updated, CACHE_TIME)

    return last_updated


def get_global_stats_timestamp(entity):
    """ Check to see when sitewide (global) statistics were last generated for the given entity. Returns unix epoch timestamp"""

    cache_key = STATUS_PREFIX + ".global-stats-timestamp-" + entity
    last_updated = cache.get(cache_key)

    if last_updated is None:
        oldest = None
        for range in ("this_week", "this_month", "this_year", "week", "month", "quarter", "year", "half_yearly", "all_time"):
            stats = db_stats.get_sitewide_stats(entity, range)
            if stats is None:
                current_app.logger.error("No stats found for %s-%s" % (entity, range))
                return None

            last_updated = stats["last_updated"]
            current_app.logger.warning("%s-%s: %d" % (entity, range, last_updated))

            if last_updated is None:
                return None

            if oldest is None:
                oldest = last_updated

            if oldest < last_updated:
                oldest = last_updated

        last_updated = oldest
        cache.set(cache_key, last_updated, CACHE_TIME)

    return last_updated


def get_playlists_timestamp():
    """ Check to see when recommendations playlists were last generated for a "random" user. Returns unix epoch timestamp"""

    cache_key = STATUS_PREFIX + ".playlist-timestamps"
    last_updated = cache.get(cache_key)
    if last_updated is None:
        last_updated = {}
        playlists = get_recommendation_playlists_for_user(db_conn, ts_conn, 1)
        if playlists is None or not playlists:
            return last_updated
        for playlist in playlists:
            source_patch = playlist.additional_metadata["algorithm_metadata"]["source_patch"]
            if source_patch in last_updated:
                # playlists are sorted by created date in descending order
                # don't overwrite the previously set timestamp for that playlist patch
                continue
            last_updated_ts = int(playlist.last_updated.timestamp())
            last_updated[source_patch] = last_updated_ts
        cache.set(cache_key, last_updated, PLAYLIST_CACHE_TIME)

    return last_updated


def get_incoming_listens_count():
    """ Check to see how many listens are currently in the incoming queue. Returns an unix epoch timestamp. """

    cache_key = STATUS_PREFIX + ".incoming_listens"
    listen_count = cache.get(cache_key)
    if listen_count is None:
        try:
            incoming_exchange = Exchange(current_app.config["INCOMING_EXCHANGE"], "fanout", durable=False)
            incoming_queue = Queue(current_app.config["INCOMING_QUEUE"], exchange=incoming_exchange, durable=True)

            with Connection(hostname=current_app.config["RABBITMQ_HOST"],
                            userid=current_app.config["RABBITMQ_USERNAME"],
                            port=current_app.config["RABBITMQ_PORT"],
                            password=current_app.config["RABBITMQ_PASSWORD"],
                            virtual_host=current_app.config["RABBITMQ_VHOST"]) as conn:

                _, listen_count, _ = incoming_queue.queue_declare(channel=conn.channel(), passive=True)
        except KombuError as err:
            current_app.logger.error("RabbitMQ is currently not available. Error: %s" % (str(err)))
            return None

        cache.set(cache_key, listen_count, LISTEN_COUNT_CACHE_TIME)

    return listen_count


def get_dump_timestamp():
    """ Check when the latst dump was generated. """

    cache_key = STATUS_PREFIX + ".dump_timestamp"
    dump_timestamp = cache.get(cache_key)
    if dump_timestamp is None:
        try:
            dump = db_dump.get_dump_entries()[0]  # return the latest dump
            dump_timestamp = int(dump["created"].timestamp())
            cache.set(cache_key, dump_timestamp, DUMP_CACHE_TIME)
        except IndexError:
            return None

    return dump_timestamp


def get_service_status():
    """ Fetch the age of the last output of various services and return a dict:

    .. code-block:: json

        {
          "dump_age": null,
          "incoming_listen_count": 2,
          "stats_age": 418605,
          "time": 1731429303
        }
    """

    current_ts = int(time())

    dump = get_dump_timestamp()
    if dump is None:
        dump_age = None
    else:
        dump_age = current_ts - dump

    listen_count = get_incoming_listens_count()

    stats = get_stats_timestamp()
    if stats is None:
        stats_age = None
    else:
        stats_age = current_ts - stats

    global_stats_age = None
    for entity in ("artists", "recordings", "release_groups"):
        global_stats = get_global_stats_timestamp(entity)
        if global_stats is None:
            global_stats_age = None
            break

        age = current_ts - global_stats
        if global_stats_age is None or age > global_stats_age:
            global_stats_age = age

    return {
        "time": current_ts,
        "dump_age": dump_age,
        "stats_age": stats_age,
        "sitewide_stats_age": global_stats_age,
        "incoming_listen_count": listen_count
    }


def get_playlist_status():
    """ Fetch the age of the last output of recommendation playlists and return a dict:

    .. code-block:: json

        {
          "playlists": [
               {
                name: "daily-jams",
                "age": 1234,
                },
                {
                name: "weekly-jams",
                "age": 1234,
                },
          ]
          "time": 1731429303
        }
    """

    current_ts = int(time())

    playlists_ts = get_playlists_timestamp()
    playlists = []
    for patch_name in MONITORED_PLAYLIST_PATCHES:
        playlist_age = current_ts - playlists_ts[patch_name] \
            if patch_name in playlists_ts else None
        playlists.append({"name": patch_name, "age": playlist_age})

    return {
        "time": current_ts,
        "playlists": playlists,
    }


@status_api_bp.get("/service-status")
@crossdomain
@ratelimit()
def service_status():
    """ Fetch the recently updated metrics for age of stats, dumps and the number of items in the incoming
    queue. This function returns JSON:

    .. code-block:: json

        {
            "dump_age": 60309,
            "incoming_listen_count": 0,
            "stats_age": 38715,
            "time": 1734021912
        }

    :statuscode 200: You have data.
    :resheader Content-Type: *application/json*
    """

    return jsonify(get_service_status())


@status_api_bp.get("/playlist-status")
@crossdomain
@ratelimit()
def playlist_status():
    """ Fetch the recently updated metrics for age of recommendation playlists. This function returns JSON:

    .. code-block:: json

        {
            "playlists": [
                {
                    "age": 55671,
                    "name": "daily-jams"
                },
                {
                    "age": 919392,
                    "name": "weekly-jams"
                },
                {
                    "age": 919184,
                    "name": "weekly-exploration"
                }
            ],
            "time": 1734013745
        }

    :statuscode 200: You have data.
    :resheader Content-Type: *application/json*
    """

    return jsonify(get_playlist_status())
