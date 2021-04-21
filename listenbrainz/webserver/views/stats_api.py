import bisect
import calendar
import json
from collections import defaultdict
from datetime import datetime
from enum import Enum
from typing import Dict, List, Tuple, Union

import listenbrainz.db.stats as db_stats
import listenbrainz.db.user as db_user
import pycountry
import requests
from data.model.sitewide_artist_stat import (SitewideArtistRecord,
                                             SitewideArtistStatJson)
from data.model.user_artist_map import (UserArtistMapRecord, UserArtistMapStat,
                                        UserArtistMapStatJson,
                                        UserArtistMapStatRange)
from data.model.user_artist_stat import UserArtistRecord, UserArtistStat
from data.model.user_listening_activity import (UserListeningActivityRecord,
                                                UserListeningActivityStat)
from data.model.user_recording_stat import (UserRecordingRecord,
                                            UserRecordingStat)
from data.model.user_release_stat import UserReleaseRecord, UserReleaseStat
from flask import Blueprint, current_app, jsonify, request
from listenbrainz.webserver.decorators import crossdomain
from listenbrainz.webserver.errors import (APIBadRequest,
                                           APIInternalServerError,
                                           APINoContent, APINotFound,
                                           APIServiceUnavailable,
                                           APIUnauthorized)
from listenbrainz.webserver.rate_limiter import ratelimit
from listenbrainz.webserver.views.api_tools import (DEFAULT_ITEMS_PER_GET,
                                                    MAX_ITEMS_PER_GET,
                                                    get_non_negative_param)

STATS_CALCULATION_INTERVAL = 7  # Stats are recalculated every 7 days

stats_api_bp = Blueprint('stats_api_v1', __name__)


class StatisticsRange(Enum):
    week = 'week'
    month = 'month'
    year = 'year'
    all_time = 'all_time'


@stats_api_bp.route("/user/<user_name>/artists")
@crossdomain()
@ratelimit()
def get_user_artist(user_name):
    """
    Get top artists for user ``user_name``.


    A sample response from the endpoint may look like:

    .. code-block:: json

        {
            "payload": {
                "artists": [
                    {
                       "artist_mbids": ["93e6118e-7fa8-49f6-9e02-699a1ebce105"],
                       "artist_msid": "d340853d-7408-4a0d-89c2-6ff13e568815",
                       "artist_name": "The Local train",
                       "listen_count": 385
                    },
                    {
                       "artist_mbids": ["ae9ed5e2-4caf-4b3d-9cb3-2ad626b91714"],
                       "artist_msid": "ba64b195-01dd-4613-9534-bb87dc44cffb",
                       "artist_name": "Lenka",
                       "listen_count": 333
                    },
                    {
                       "artist_mbids": ["cc197bad-dc9c-440d-a5b5-d52ba2e14234"],
                       "artist_msid": "6599e41e-390c-4855-a2ac-68ee798538b4",
                       "artist_name": "Coldplay",
                       "listen_count": 321
                    }
                ],
                "count": 3,
                "total_artist_count": 175,
                "range": "all_time",
                "last_updated": 1588494361,
                "user_id": "John Doe",
                "from_ts": 1009823400,
                "to_ts": 1590029157
            }
        }

    .. note::
        - This endpoint is currently in beta
        - ``artist_mbids`` and ``artist_msid`` are optional fields and may not be present in all the responses

    :param count: Optional, number of artists to return, Default: :data:`~webserver.views.api.DEFAULT_ITEMS_PER_GET`
        Max: :data:`~webserver.views.api.MAX_ITEMS_PER_GET`
    :type count: ``int``
    :param offset: Optional, number of artists to skip from the beginning, for pagination.
        Ex. An offset of 5 means the top 5 artists will be skipped, defaults to 0
    :type offset: ``int``
    :param range: Optional, time interval for which statistics should be collected, possible values are ``week``,
        ``month``, ``year``, ``all_time``, defaults to ``all_time``
    :type range: ``str``
    :statuscode 200: Successful query, you have data!
    :statuscode 204: Statistics for the user haven't been calculated, empty response will be returned
    :statuscode 400: Bad request, check ``response['error']`` for more details
    :statuscode 404: User not found
    :resheader Content-Type: *application/json*
    """
    user = db_user.get_by_mb_id(user_name)
    if user is None:
        raise APINotFound("Cannot find user: %s" % user_name)

    stats_range = request.args.get('range', default='all_time')
    if not _is_valid_range(stats_range):
        raise APIBadRequest("Invalid range: {}".format(stats_range))

    offset = get_non_negative_param('offset', default=0)
    count = get_non_negative_param('count', default=DEFAULT_ITEMS_PER_GET)

    stats = db_stats.get_user_artists(user['id'], stats_range)
    if stats is None or getattr(stats, stats_range) is None:
        raise APINoContent('')

    entity_list, total_entity_count = _process_user_entity(stats, stats_range, offset, count, entity='artist')
    from_ts = int(getattr(stats, stats_range).from_ts)
    to_ts = int(getattr(stats, stats_range).to_ts)
    last_updated = int(stats.last_updated.timestamp())

    return jsonify({'payload': {
        "user_id": user_name,
        "artists": entity_list,
        "count": len(entity_list),
        "total_artist_count": total_entity_count,
        "offset": offset,
        "range": stats_range,
        "from_ts": from_ts,
        "to_ts": to_ts,
        "last_updated": last_updated,
    }})


@stats_api_bp.route("/user/<user_name>/releases")
@crossdomain()
@ratelimit()
def get_release(user_name):
    """
    Get top releases for user ``user_name``.

    A sample response from the endpoint may look like:

    .. code-block:: json

        {
            "payload": {
                "releases": [
                    {
                        "artist_mbids": [],
                        "artist_msid": "6599e41e-390c-4855-a2ac-68ee798538b4",
                        "artist_name": "Coldplay",
                        "listen_count": 26,
                        "release_mbid": "",
                        "release_msid": "d59730cf-f0e3-441e-a7a7-8e0f589632a5",
                        "release_name": "Live in Buenos Aires"
                    },
                    {
                        "artist_mbids": [],
                        "artist_msid": "7addbcac-ae39-4b4c-a956-53da336d68e8",
                        "artist_name": "Ellie Goulding",
                        "listen_count": 25,
                        "release_mbid": "",
                        "release_msid": "de97ca87-36c4-4995-a5c9-540e35944352",
                        "release_name": "Delirium (Deluxe)"
                    },
                    {
                        "artist_mbids": [],
                        "artist_msid": "3b155259-b29e-4515-aa62-cb0b917f4cfd",
                        "artist_name": "The Fray",
                        "listen_count": 25,
                        "release_mbid": "",
                        "release_msid": "2b2a93c3-a0bd-4f46-8507-baf5ad291966",
                        "release_name": "How to Save a Life"
                    },
                ],
                "count": 3,
                "total_release_count": 175,
                "range": "all_time",
                "last_updated": 1588494361,
                "user_id": "John Doe",
                "from_ts": 1009823400,
                "to_ts": 1590029157
            }
        }

    .. note::
        - This endpoint is currently in beta
        - ``artist_mbids``, ``artist_msid``, ``release_mbid`` and ``release_msid`` are optional fields and
          may not be present in all the responses

    :param count: Optional, number of releases to return, Default: :data:`~webserver.views.api.DEFAULT_ITEMS_PER_GET`
        Max: :data:`~webserver.views.api.MAX_ITEMS_PER_GET`
    :type count: ``int``
    :param offset: Optional, number of releases to skip from the beginning, for pagination.
        Ex. An offset of 5 means the top 5 releases will be skipped, defaults to 0
    :type offset: ``int``
    :param range: Optional, time interval for which statistics should be collected, possible values are ``week``,
        ``month``, ``year``, ``all_time``, defaults to ``all_time``
    :type range: ``str``
    :statuscode 200: Successful query, you have data!
    :statuscode 204: Statistics for the user haven't been calculated, empty response will be returned
    :statuscode 400: Bad request, check ``response['error']`` for more details
    :statuscode 404: User not found
    :resheader Content-Type: *application/json*
    """
    user = db_user.get_by_mb_id(user_name)
    if user is None:
        raise APINotFound("Cannot find user: %s" % user_name)

    stats_range = request.args.get('range', default='all_time')
    if not _is_valid_range(stats_range):
        raise APIBadRequest("Invalid range: {}".format(stats_range))

    offset = get_non_negative_param('offset', default=0)
    count = get_non_negative_param('count', default=DEFAULT_ITEMS_PER_GET)

    stats = db_stats.get_user_releases(user['id'], stats_range)
    if stats is None or getattr(stats, stats_range) is None:
        raise APINoContent('')

    entity_list, total_entity_count = _process_user_entity(stats, stats_range, offset, count, entity='release')
    from_ts = int(getattr(stats, stats_range).from_ts)
    to_ts = int(getattr(stats, stats_range).to_ts)
    last_updated = int(stats.last_updated.timestamp())

    return jsonify({'payload': {
        "user_id": user_name,
        'releases': entity_list,
        "count": len(entity_list),
        "total_release_count": total_entity_count,
        "offset": offset,
        "range": stats_range,
        "from_ts": from_ts,
        "to_ts": to_ts,
        "last_updated": last_updated,
    }})


@stats_api_bp.route("/user/<user_name>/recordings")
@crossdomain()
@ratelimit()
def get_recording(user_name):
    """
    Get top recordings for user ``user_name``.

    A sample response from the endpoint may look like:

    .. code-block:: json

        {
            "payload": {
                "recordings": [
                    {
                        "artist_mbids": [],
                        "artist_msid": "7addbcac-ae39-4b4c-a956-53da336d68e8",
                        "artist_name": "Ellie Goulding",
                        "listen_count": 25,
                        "recording_mbid": "0fe11cd3-0be4-467b-84fa-0bd524d45d74",
                        "recording_msid": "c6b65a7e-7284-433e-ac5d-e3ff0aa4738a",
                        "release_mbid": "",
                        "release_msid": "de97ca87-36c4-4995-a5c9-540e35944352",
                        "release_name": "Delirium (Deluxe)",
                        "track_name": "Love Me Like You Do - From \\"Fifty Shades of Grey\\""
                    },
                    {
                        "artist_mbids": [],
                        "artist_msid": "3b155259-b29e-4515-aa62-cb0b917f4cfd",
                        "artist_name": "The Fray",
                        "listen_count": 23,
                        "recording_mbid": "0008ab49-a6ad-40b5-aa90-9d2779265c22",
                        "recording_msid": "4b5bf07c-782f-4324-9242-bf56e4ba1e57",
                        "release_mbid": "",
                        "release_msid": "2b2a93c3-a0bd-4f46-8507-baf5ad291966",
                        "release_name": "How to Save a Life",
                        "track_name": "How to Save a Life"
                    }
                ],
                "count": 2,
                "total_recording_count": 175,
                "range": "all_time",
                "last_updated": 1588494361,
                "user_id": "John Doe",
                "from_ts": 1009823400,
                "to_ts": 1590029157
            }
        }

    .. note::
        - This endpoint is currently in beta
        - We only calculate the top 1000 all_time recordings
        - ``artist_mbids``, ``artist_msid``, ``release_name``, ``release_mbid``, ``release_msid``,
          ``recording_mbid`` and ``recording_msid`` are optional fields and may not be present in all the responses

    :param count: Optional, number of recordings to return, Default: :data:`~webserver.views.api.DEFAULT_ITEMS_PER_GET`
        Max: :data:`~webserver.views.api.MAX_ITEMS_PER_GET`
    :type count: ``int``
    :param offset: Optional, number of recordings to skip from the beginning, for pagination.
        Ex. An offset of 5 means the top 5 recordings will be skipped, defaults to 0
    :type offset: ``int``
    :param range: Optional, time interval for which statistics should be collected, possible values are ``week``,
        ``month``, ``year``, ``all_time``, defaults to ``all_time``
    :type range: ``str``
    :statuscode 200: Successful query, you have data!
    :statuscode 204: Statistics for the user haven't been calculated, empty response will be returned
    :statuscode 400: Bad request, check ``response['error']`` for more details
    :statuscode 404: User not found
    :resheader Content-Type: *application/json*
    """
    user = db_user.get_by_mb_id(user_name)
    if user is None:
        raise APINotFound("Cannot find user: %s" % user_name)

    stats_range = request.args.get('range', default='all_time')
    if not _is_valid_range(stats_range):
        raise APIBadRequest("Invalid range: {}".format(stats_range))

    offset = get_non_negative_param('offset', default=0)
    count = get_non_negative_param('count', default=DEFAULT_ITEMS_PER_GET)

    stats = db_stats.get_user_recordings(user['id'], stats_range)
    if stats is None or getattr(stats, stats_range) is None:
        raise APINoContent('')

    entity_list, total_entity_count = _process_user_entity(stats, stats_range, offset, count, entity='recording')
    from_ts = int(getattr(stats, stats_range).from_ts)
    to_ts = int(getattr(stats, stats_range).to_ts)
    last_updated = int(stats.last_updated.timestamp())

    return jsonify({'payload': {
        "user_id": user_name,
        'recordings': entity_list,
        "count": len(entity_list),
        "total_recording_count": total_entity_count,
        "offset": offset,
        "range": stats_range,
        "from_ts": from_ts,
        "to_ts": to_ts,
        "last_updated": last_updated,
    }})


@stats_api_bp.route("/user/<user_name>/listening-activity")
@crossdomain()
@ratelimit()
def get_listening_activity(user_name: str):
    """
    Get the listening activity for user ``user_name``. The listening activity shows the number of listens
    the user has submitted over a period of time.

    A sample response from the endpoint may look like:

    .. code-block:: json

        {
            "payload": {
                "from_ts": 1587945600,
                "last_updated": 1592807084,
                "listening_activity": [
                    {
                        "from_ts": 1587945600,
                        "listen_count": 26,
                        "time_range": "Monday 27 April 2020",
                        "to_ts": 1588031999
                    },
                    {
                        "from_ts": 1588032000,
                        "listen_count": 57,
                        "time_range": "Tuesday 28 April 2020",
                        "to_ts": 1588118399
                    },
                    {
                        "from_ts": 1588118400,
                        "listen_count": 33,
                        "time_range": "Wednesday 29 April 2020",
                        "to_ts": 1588204799
                    },
                "to_ts": 1589155200,
                "user_id": "ishaanshah"
            }
        }

    .. note::
        - This endpoint is currently in beta
        - The example above shows the data for three days only, however we calculate the statistics for
          the current time range and the previous time range. For example for weekly statistics the data
          is calculated for the current as well as the past week.
        - For ``all_time`` listening activity statistics we only return the years which have more than
          zero listens.

    :param range: Optional, time interval for which statistics should be returned, possible values are ``week``,
        ``month``, ``year``, ``all_time``, defaults to ``all_time``
    :type range: ``str``
    :statuscode 200: Successful query, you have data!
    :statuscode 204: Statistics for the user haven't been calculated, empty response will be returned
    :statuscode 400: Bad request, check ``response['error']`` for more details
    :statuscode 404: User not found
    :resheader Content-Type: *application/json*

    """
    user = db_user.get_by_mb_id(user_name)
    if user is None:
        raise APINotFound("Cannot find user: {}".format(user_name))

    stats_range = request.args.get('range', default='all_time')
    if not _is_valid_range(stats_range):
        raise APIBadRequest("Invalid range: {}".format(stats_range))

    stats = db_stats.get_user_listening_activity(user['id'], stats_range)
    if stats is None or getattr(stats, stats_range) is None:
        raise APINoContent('')

    listening_activity = [x.dict() for x in getattr(stats, stats_range).listening_activity]
    return jsonify({"payload": {
        "user_id": user_name,
        "listening_activity": listening_activity,
        "from_ts": int(getattr(stats, stats_range).from_ts),
        "to_ts": int(getattr(stats, stats_range).to_ts),
        "range": stats_range,
        "last_updated": int(stats.last_updated.timestamp())
    }})


@stats_api_bp.route("/user/<user_name>/daily-activity")
@crossdomain()
@ratelimit()
def get_daily_activity(user_name: str):
    """
    Get the daily activity for user ``user_name``. The daily activity shows the number of listens
    submitted by the user for each hour of the day over a period of time. We assume that all listens are in UTC.

    A sample response from the endpoint may look like:

    .. code-block:: json

        {
            "payload": {
                "from_ts": 1587945600,
                "last_updated": 1592807084,
                "daily_activity": {
                    "Monday": [
                        {
                            "hour": 0
                            "listen_count": 26,
                        },
                        {
                            "hour": 1
                            "listen_count": 30,
                        },
                        {
                            "hour": 2
                            "listen_count": 4,
                        },
                        "..."
                    ],
                    "Tuesday": ["..."],
                    "..."
                },
                "stats_range": "all_time",
                "to_ts": 1589155200,
                "user_id": "ishaanshah"
            }
        }

    .. note::
        - This endpoint is currently in beta

    :param range: Optional, time interval for which statistics should be returned, possible values are ``week``,
        ``month``, ``year``, ``all_time``, defaults to ``all_time``
    :type range: ``str``
    :statuscode 200: Successful query, you have data!
    :statuscode 204: Statistics for the user haven't been calculated, empty response will be returned
    :statuscode 400: Bad request, check ``response['error']`` for more details
    :statuscode 404: User not found
    :resheader Content-Type: *application/json*

    """
    user = db_user.get_by_mb_id(user_name)
    if user is None:
        raise APINotFound("Cannot find user: {}".format(user_name))

    stats_range = request.args.get('range', default='all_time')
    if not _is_valid_range(stats_range):
        raise APIBadRequest("Invalid range: {}".format(stats_range))

    stats = db_stats.get_user_daily_activity(user['id'], stats_range)
    if stats is None or getattr(stats, stats_range) is None:
        raise APINoContent('')

    daily_activity_unprocessed = [x.dict() for x in getattr(stats, stats_range).daily_activity]
    daily_activity = {calendar.day_name[day]: [{"hour": hour, "listen_count": 0} for hour in range(0, 24)] for day in range(0, 7)}

    for day, day_data in daily_activity.items():
        for hour_data in day_data:
            hour = hour_data["hour"]

            for entry in daily_activity_unprocessed:
                if entry["hour"] == hour and entry["day"] == day:
                    hour_data["listen_count"] = entry["listen_count"]
                    break
            else:
                hour_data["listen_count"] = 0

    return jsonify({"payload": {
        "user_id": user_name,
        "daily_activity": daily_activity,
        "from_ts": int(getattr(stats, stats_range).from_ts),
        "to_ts": int(getattr(stats, stats_range).to_ts),
        "range": stats_range,
        "last_updated": int(stats.last_updated.timestamp())
    }})


@stats_api_bp.route("/user/<user_name>/artist-map")
@crossdomain()
@ratelimit()
def get_artist_map(user_name: str):
    """
    Get the artist map for user ``user_name``. The artist map shows the number of artists the user has listened to
    from different countries of the world.

    A sample response from the endpoint may look like:

    .. code-block:: json

        {
            "payload": {
                "from_ts": 1587945600,
                "last_updated": 1592807084,
                "artist_map": [
                    {
                        "country": "USA",
                        "artist_count": 34
                    },
                    {
                        "country": "GBR",
                        "artist_count": 69
                    },
                    {
                        "country": "IND",
                        "artist_count": 32
                    }
                ],
                "stats_range": "all_time"
                "to_ts": 1589155200,
                "user_id": "ishaanshah"
            }
        }

    .. note::
        - This endpoint is currently in beta
        - We cache the results for this query for a week to improve page load times, if you want to request fresh data you
          can use the ``force_recalculate`` flag.

    :param range: Optional, time interval for which statistics should be returned, possible values are ``week``,
        ``month``, ``year``, ``all_time``, defaults to ``all_time``
    :type range: ``str``
    :param force_recalculate: Optional, recalculate the data instead of returning the cached result.
    :type range: ``bool``
    :statuscode 200: Successful query, you have data!
    :statuscode 204: Statistics for the user haven't been calculated, empty response will be returned
    :statuscode 400: Bad request, check ``response['error']`` for more details
    :statuscode 404: User not found
    :resheader Content-Type: *application/json*

    """
    user = db_user.get_by_mb_id(user_name)
    if user is None:
        raise APINotFound("Cannot find user: {}".format(user_name))

    stats_range = request.args.get('range', default='all_time')
    if not _is_valid_range(stats_range):
        raise APIBadRequest("Invalid range: {}".format(stats_range))

    recalculate_param = request.args.get('force_recalculate', default='false')
    if recalculate_param.lower() not in ['true', 'false']:
        raise APIBadRequest("Invalid value of force_recalculate: {}".format(recalculate_param))
    force_recalculate = recalculate_param.lower() == 'true'

    # Check if stats are present in DB, if not calculate them
    calculated = not force_recalculate
    stats = db_stats.get_user_artist_map(user['id'], stats_range)
    if stats is None or getattr(stats, stats_range) is None:
        calculated = False

    # Check if the stats present in DB have been calculated in the past week, if not recalculate them
    stale = False
    if calculated:
        last_updated = getattr(stats, stats_range).last_updated
        if (datetime.now() - datetime.fromtimestamp(last_updated)).days >= STATS_CALCULATION_INTERVAL:
            stale = True

    if stale or not calculated:
        artist_stats = db_stats.get_user_artists(user['id'], stats_range)

        # If top artists are missing, return the stale stats if present, otherwise return 204
        if artist_stats is None or getattr(artist_stats, stats_range) is None:
            if stale:
                result = stats
            else:
                raise APINoContent('')
        else:
            # Calculate the data
            artist_msids = defaultdict(lambda: 0)
            artist_mbids = defaultdict(lambda: 0)
            top_artists = getattr(artist_stats, stats_range).artists
            for artist in top_artists:
                if artist.artist_msid is not None:
                    artist_msids[artist.artist_msid] += artist.listen_count
                else:
                    for artist_mbid in artist.artist_mbids:
                        artist_mbids[artist_mbid] += artist.listen_count

            country_code_data = _get_country_codes(artist_msids, artist_mbids)
            result = UserArtistMapStatJson(**{
                stats_range: {
                    "artist_map": country_code_data,
                    "from_ts": int(getattr(artist_stats, stats_range).from_ts),
                    "to_ts": int(getattr(artist_stats, stats_range).to_ts),
                    "last_updated": int(datetime.now().timestamp())
                }
            })

            # Store in DB for future use
            try:
                db_stats.insert_user_artist_map(user['id'], result)
            except Exception as err:
                current_app.logger.error("Error while inserting artist map stats for {user}. Error: {err}. Data: {data}".format(
                    user=user_name, err=err, data=result), exc_info=True)
    else:
        result = stats

    return jsonify({
        "payload": {
            "user_id": user_name,
            "range": stats_range,
            **(getattr(result, stats_range).dict())
        }
    })


@stats_api_bp.route("/sitewide/artists")
@crossdomain()
@ratelimit()
def get_sitewide_artist():
    """
    Get sitewide top artists.


    A sample response from the endpoint may look like:

    .. code-block:: json

        {
            "payload": {
                "time_ranges": [
                    {
                        "time_range": "April 2020",
                        "artists": [
                            {
                                "artist_mbids": ["f4fdbb4c-e4b7-47a0-b83b-d91bbfcfa387"],
                                "artist_msid": "b4ae3356-b8a7-471a-a23a-e471a69ad454",
                                "artist_name": "Ariana Grande",
                                "listen_count": 519
                            },
                            {
                                "artist_mbids": ["f4abc0b5-3f7a-4eff-8f78-ac078dbce533"],
                                "artist_msid": "f9ee09fb-5ab4-46a2-9088-3eac0eed4920",
                                "artist_name": "Billie Eilish",
                                "listen_count": 447
                            }
                        ],
                        "from_ts": 1585699200,
                        "to_ts": 1588291199,
                    },
                    {
                        "time_range": "May 2020",
                        "artists": [
                            {
                                "artist_mbids": [],
                                "artist_msid": "2b0646af-f3f0-4a5b-b629-6c31301c1c29",
                                "artist_name": "The Weeknd",
                                "listen_count": 621
                            },
                            {
                                "artist_mbids": [],
                                "artist_msid": "9720fd77-fe48-41ba-a7a2-b4795718dd97",
                                "artist_name": "Drake",
                                "listen_count": 554
                            }
                        ],
                        "from_ts": 1588291200,
                        "to_ts": 1590969599
                    }
                ],
                "offset": 0,
                "count": 2,
                "range": "year",
                "last_updated": 1588494361,
                "from_ts": 1009823400,
                "to_ts": 1590029157
            }
        }

    .. note::
        - This endpoint is currently in beta
        - ``artist_mbids`` and ``artist_msid`` are optional fields and may not be present in all the entries
        - The example above shows the data for two days only, however we calculate the statistics for
          the current time range and the previous time range. For example for yearly statistics the data
          is calculated for the months in current as well as the past year.
        - We only calculate the top 1000 artists for each time period.

    :param count: Optional, number of artists to return for each time range,
        Default: :data:`~webserver.views.api.DEFAULT_ITEMS_PER_GET`
        Max: :data:`~webserver.views.api.MAX_ITEMS_PER_GET`
    :type count: ``int``
    :param offset: Optional, number of artists to skip from the beginning, for pagination.
        Ex. An offset of 5 means the top 5 artists will be skipped, defaults to 0
    :type offset: ``int``
    :param range: Optional, time interval for which statistics should be collected, possible values are ``week``,
        ``month``, ``year``, ``all_time``, defaults to ``all_time``
    :type range: ``str``
    :statuscode 200: Successful query, you have data!
    :statuscode 204: Statistics haven't been calculated, empty response will be returned
    :statuscode 400: Bad request, check ``response['error']`` for more details
    :resheader Content-Type: *application/json*
    """
    stats_range = request.args.get('range', default='all_time')
    if not _is_valid_range(stats_range):
        raise APIBadRequest("Invalid range: {}".format(stats_range))

    offset = get_non_negative_param('offset', default=0)
    count = get_non_negative_param('count', default=DEFAULT_ITEMS_PER_GET)

    stats = db_stats.get_sitewide_artists(stats_range)
    if stats is None or stats.data is None:
        raise APINoContent('')

    entity_data = _get_sitewide_entity_list(stats.data, entity="artists", offset=offset, count=count)
    return jsonify({
        'payload': {
            "time_ranges": entity_data,
            "range": stats_range,
            "offset": offset,
            "count": min(count, MAX_ITEMS_PER_GET),
            "from_ts": stats.data.from_ts,
            "to_ts": stats.data.to_ts,
            "last_updated": int(stats.last_updated.timestamp())
        }
    })


def _process_user_entity(stats, stats_range, offset, count, entity) -> Tuple[list, int]:
    """ Process the statistics data according to query params

        Args:
            stats (dict): the dictionary containing statistic data
            stats_range (str): time interval for which statistics should be collected
            offset (int): number of entities to skip from the beginning
            count (int): number of entities to return
            entity (str): name of the entity, i.e 'artist', 'release' or 'recording'

        Returns:
            entity_list, total_entity_count: a tupple of a list and integer
                containing the entities processed according to the query params and
                total number of entities respectively
    """

    count = min(count, MAX_ITEMS_PER_GET)
    count = count + offset
    total_entity_count = getattr(stats, stats_range).count
    entity_list = [x.dict() for x in _get_user_entity_list(stats, stats_range, entity, offset, count)]

    return entity_list, total_entity_count


def _is_valid_range(stats_range: str) -> bool:
    """ Check if the provided stats time range is valid

    Args:
        stats_range: the range to validate

    Returns:
        result: True if given range is valid
    """
    return stats_range in StatisticsRange.__members__


def _get_user_entity_list(
    stats: Union[UserArtistStat, UserReleaseStat, UserRecordingStat],
    stats_range: StatisticsRange,
    entity: str,
    offset: int,
    count: int,
) -> List[Union[UserArtistRecord, UserReleaseRecord, UserRecordingRecord]]:
    """ Gets a list of entity records from the stat passed based on the offset and count
    """
    if entity == 'artist':
        return getattr(stats, stats_range).artists[offset:count]
    elif entity == 'release':
        return getattr(stats, stats_range).releases[offset:count]
    elif entity == 'recording':
        return getattr(stats, stats_range).recordings[offset:count]
    raise APIBadRequest("Unknown entity: %s" % entity)


def _get_sitewide_entity_list(
    stats: Union[SitewideArtistStatJson],
    entity: str,
    offset: int,
    count: int,
) -> List[dict]:
    """ Gets a list of entity records from the stat passed based on the offset and count
    """
    count = min(count, MAX_ITEMS_PER_GET)
    count = count + offset

    result = []
    for time_range in stats.time_ranges:
        result.append({
            "time_range": time_range.time_range,
            "from_ts": time_range.from_ts,
            "to_ts": time_range.to_ts,
            entity: [x.dict() for x in getattr(time_range, entity)[offset:count]]
        })

    return sorted(result, key=lambda x: x['from_ts'])


def _get_country_codes(artist_msids: Dict[str, int], artist_mbids: Dict[str, int]) -> List[UserArtistMapRecord]:
    """ Get country codes from list of given artist_msids and artist_mbids
    """
    country_map = defaultdict(int)

    # Map artist_msids to artist_mbids and create a common dict
    all_artist_mbids = defaultdict(lambda: 0)
    for artist_mbid, listen_count in _get_mbids_from_msids(artist_msids).items():
        all_artist_mbids[artist_mbid] += listen_count
    for artist_mbid, listen_count in artist_mbids.items():
        all_artist_mbids[artist_mbid] += listen_count

    # Get artist_origin_countries from artist_credit_ids
    artist_country_code = _get_country_code_from_mbids(all_artist_mbids)

    # Map country codes to appropriate MBIDs and listen counts
    result = defaultdict(lambda: {
        "artist_count": 0,
        "listen_count": 0
    })
    for artist_mbid, listen_count in all_artist_mbids.items():
        if artist_mbid in artist_country_code:
            # TODO: add a test to handle the case where pycountry doesn't recognize the country
            country_alpha_3 = pycountry.countries.get(alpha_2=artist_country_code[artist_mbid])
            if country_alpha_3 is None:
                continue
            result[country_alpha_3.alpha_3]["artist_count"] += 1
            result[country_alpha_3.alpha_3]["listen_count"] += listen_count

    return [
        UserArtistMapRecord(**{
            "country": country,
            **data
        }) for country, data in result.items()
    ]


def _get_mbids_from_msids(artist_msids: Dict[str, int]) -> Dict[str, int]:
    """ Get list of artist_mbids corresponding to the input artist_msids
    """
    request_data = [{"artist_msid": artist_msid} for artist_msid in artist_msids.keys()]
    msid_mbid_mapping = defaultdict(list)
    if len(request_data) > 0:
        try:
            result = requests.post("{}/artist-credit-from-artist-msid/json"
                                   .format(current_app.config['LISTENBRAINZ_LABS_API_URL']),
                                   json=request_data, params={'count': len(request_data)})
            # Raise error if non 200 response is received
            result.raise_for_status()
            data = result.json()
            for entry in data:
                msid_mbid_mapping[entry['artist_msid']] = entry['[artist_credit_mbid]']
        except requests.RequestException as err:
            current_app.logger.error("Error while getting artist_mbids, {}".format(err), exc_info=True)
            error_msg = ("An error occurred while calculating artist_map data, "
                         "try setting 'force_recalculate' to 'false' to get a cached copy if available."
                         "Payload: {}. Response: {}".format(request_data, result.text))
            raise APIInternalServerError(error_msg)

    artist_mbids = defaultdict(lambda: 0)
    for artist_msid, listen_count in artist_msids.items():
        if artist_msid in msid_mbid_mapping:
            for artist_mbid in msid_mbid_mapping[artist_msid]:
                artist_mbids[artist_mbid] += listen_count

    return artist_mbids


def _get_country_code_from_mbids(artist_mbids: Dict[str, int]) -> Dict[str, str]:
    """ Get a list of artist_country_code corresponding to the input artist_mbids
    """
    request_data = [{"artist_mbid": artist_mbid} for artist_mbid in artist_mbids.keys()]
    artist_country_code = {}
    if len(request_data) > 0:
        try:
            result = requests.post("{}/artist-country-code-from-artist-mbid/json"
                                   .format(current_app.config['LISTENBRAINZ_LABS_API_URL']),
                                   json=request_data, params={'count': len(request_data)})
            # Raise error if non 200 response is received
            result.raise_for_status()
            data = result.json()
            for entry in data:
                artist_country_code[entry["artist_mbid"]] = entry["country_code"]
        except requests.RequestException as err:
            current_app.logger.error("Error while getting artist_artist_country_code, {}".format(err), exc_info=True)
            error_msg = ("An error occurred while calculating artist_map data, "
                         "try setting 'force_recalculate' to 'false' to get a cached copy if available"
                         "Payload: {}. Response: {}".format(request_data, result.text))
            raise APIInternalServerError(error_msg)

    return artist_country_code
