import calendar
from collections import defaultdict
from datetime import datetime
from typing import Dict, List, Tuple, Iterable

from requests import HTTPError

import listenbrainz.db.stats as db_stats
import listenbrainz.db.user as db_user
import pycountry
import requests

from data.model.common_stat import StatApi, StatisticsRange, StatRecordList
from data.model.user_artist_map import UserArtistMapRecord, UserArtistMapArtist
from flask import Blueprint, current_app, jsonify, request

from data.model.user_daily_activity import DailyActivityRecord
from data.model.user_entity import EntityRecord
from data.model.user_listening_activity import ListeningActivityRecord
from listenbrainz.db import year_in_music as db_year_in_music
from listenbrainz.webserver.decorators import crossdomain
from listenbrainz.webserver.errors import (APIBadRequest,
                                           APIInternalServerError,
                                           APINoContent, APINotFound)
from brainzutils.ratelimit import ratelimit
from listenbrainz.webserver.views.api_tools import (DEFAULT_ITEMS_PER_GET,
                                                    MAX_ITEMS_PER_GET,
                                                    get_non_negative_param)


stats_api_bp = Blueprint('stats_api_v1', __name__)


@stats_api_bp.route("/user/<user_name>/artists")
@crossdomain
@ratelimit()
def get_artist(user_name):
    """
    Get top artists for user ``user_name``.


    A sample response from the endpoint may look like:

    .. code-block:: json

        {
            "payload": {
                "artists": [
                    {
                       "artist_mbids": ["93e6118e-7fa8-49f6-9e02-699a1ebce105"],
                       "artist_name": "The Local train",
                       "listen_count": 385
                    },
                    {
                       "artist_mbids": ["ae9ed5e2-4caf-4b3d-9cb3-2ad626b91714"],
                       "artist_name": "Lenka",
                       "listen_count": 333
                    },
                    {
                       "artist_mbids": ["cc197bad-dc9c-440d-a5b5-d52ba2e14234"],
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
        - ``artist_mbids`` is an optional field and may not be present in all the responses

    :param count: Optional, number of artists to return, Default: :data:`~webserver.views.api.DEFAULT_ITEMS_PER_GET`
        Max: :data:`~webserver.views.api.MAX_ITEMS_PER_GET`
    :type count: ``int``
    :param offset: Optional, number of artists to skip from the beginning, for pagination.
        Ex. An offset of 5 means the top 5 artists will be skipped, defaults to 0
    :type offset: ``int``
    :param range: Optional, time interval for which statistics should be returned, possible values are
        :data:`~data.model.common_stat.ALLOWED_STATISTICS_RANGE`, defaults to ``all_time``
    :type range: ``str``
    :statuscode 200: Successful query, you have data!
    :statuscode 204: Statistics for the user haven't been calculated, empty response will be returned
    :statuscode 400: Bad request, check ``response['error']`` for more details
    :statuscode 404: User not found
    :resheader Content-Type: *application/json*
    """
    return _get_entity_stats(user_name, "artists", "total_artist_count")


@stats_api_bp.route("/user/<user_name>/releases")
@crossdomain
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
                        "artist_name": "Coldplay",
                        "listen_count": 26,
                        "release_mbid": "",
                        "release_name": "Live in Buenos Aires"
                    },
                    {
                        "artist_mbids": [],
                        "artist_name": "Ellie Goulding",
                        "listen_count": 25,
                        "release_mbid": "",
                        "release_name": "Delirium (Deluxe)"
                    },
                    {
                        "artist_mbids": [],
                        "artist_name": "The Fray",
                        "listen_count": 25,
                        "release_mbid": "",
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
        - ``artist_mbids`` and ``release_mbid`` are optional fields and
          may not be present in all the responses

    :param count: Optional, number of releases to return, Default: :data:`~webserver.views.api.DEFAULT_ITEMS_PER_GET`
        Max: :data:`~webserver.views.api.MAX_ITEMS_PER_GET`
    :type count: ``int``
    :param offset: Optional, number of releases to skip from the beginning, for pagination.
        Ex. An offset of 5 means the top 5 releases will be skipped, defaults to 0
    :type offset: ``int``
    :param range: Optional, time interval for which statistics should be returned, possible values are
        :data:`~data.model.common_stat.ALLOWED_STATISTICS_RANGE`, defaults to ``all_time``
    :type range: ``str``
    :statuscode 200: Successful query, you have data!
    :statuscode 204: Statistics for the user haven't been calculated, empty response will be returned
    :statuscode 400: Bad request, check ``response['error']`` for more details
    :statuscode 404: User not found
    :resheader Content-Type: *application/json*
    """
    return _get_entity_stats(user_name, "releases", "total_release_count")


@stats_api_bp.route("/user/<user_name>/recordings")
@crossdomain
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
                        "artist_name": "Ellie Goulding",
                        "listen_count": 25,
                        "recording_mbid": "0fe11cd3-0be4-467b-84fa-0bd524d45d74",
                        "release_mbid": "",
                        "release_name": "Delirium (Deluxe)",
                        "track_name": "Love Me Like You Do - From \\"Fifty Shades of Grey\\""
                    },
                    {
                        "artist_mbids": [],
                        "artist_name": "The Fray",
                        "listen_count": 23,
                        "recording_mbid": "0008ab49-a6ad-40b5-aa90-9d2779265c22",
                        "release_mbid": "",
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
        - ``artist_mbids``, ``release_name``, ``release_mbid`` and ``recording_mbid`` are optional fields
         and may not be present in all the responses

    :param count: Optional, number of recordings to return, Default: :data:`~webserver.views.api.DEFAULT_ITEMS_PER_GET`
        Max: :data:`~webserver.views.api.MAX_ITEMS_PER_GET`
    :type count: ``int``
    :param offset: Optional, number of recordings to skip from the beginning, for pagination.
        Ex. An offset of 5 means the top 5 recordings will be skipped, defaults to 0
    :type offset: ``int``
    :param range: Optional, time interval for which statistics should be returned, possible values are
        :data:`~data.model.common_stat.ALLOWED_STATISTICS_RANGE`, defaults to ``all_time``
    :type range: ``str``
    :statuscode 200: Successful query, you have data!
    :statuscode 204: Statistics for the user haven't been calculated, empty response will be returned
    :statuscode 400: Bad request, check ``response['error']`` for more details
    :statuscode 404: User not found
    :resheader Content-Type: *application/json*
    """
    return _get_entity_stats(user_name, "recordings", "total_recording_count")


def _get_entity_stats(user_name: str, entity: str, count_key: str):
    user, stats_range = _validate_stats_user_params(user_name)

    offset = get_non_negative_param("offset", default=0)
    count = get_non_negative_param("count", default=DEFAULT_ITEMS_PER_GET)

    stats = db_stats.get(user["id"], entity, stats_range, EntityRecord)
    if stats is None:
        raise APINoContent('')

    entity_list, total_entity_count = _process_user_entity(stats, offset, count)

    entity = "artists" if entity == "test_artists" else entity

    return jsonify({"payload": {
        "user_id": user_name,
        entity: entity_list,
        "count": len(entity_list),
        count_key: total_entity_count,
        "offset": offset,
        "range": stats_range,
        "from_ts": stats.from_ts,
        "to_ts": stats.to_ts,
        "last_updated": stats.last_updated,
    }})


@stats_api_bp.route("/user/<user_name>/listening-activity")
@crossdomain
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

    :param range: Optional, time interval for which statistics should be returned, possible values are
        :data:`~data.model.common_stat.ALLOWED_STATISTICS_RANGE`, defaults to ``all_time``
    :type range: ``str``
    :statuscode 200: Successful query, you have data!
    :statuscode 204: Statistics for the user haven't been calculated, empty response will be returned
    :statuscode 400: Bad request, check ``response['error']`` for more details
    :statuscode 404: User not found
    :resheader Content-Type: *application/json*

    """
    user, stats_range = _validate_stats_user_params(user_name)

    stats = db_stats.get(user["id"], "listening_activity", stats_range, ListeningActivityRecord)
    if stats is None:
        raise APINoContent('')

    listening_activity = [x.dict() for x in stats.data.__root__]
    return jsonify({"payload": {
        "user_id": user_name,
        "listening_activity": listening_activity,
        "from_ts": stats.from_ts,
        "to_ts": stats.to_ts,
        "range": stats_range,
        "last_updated": stats.last_updated
    }})


@stats_api_bp.route("/user/<user_name>/daily-activity")
@crossdomain
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

    :param range: Optional, time interval for which statistics should be returned, possible values are
        :data:`~data.model.common_stat.ALLOWED_STATISTICS_RANGE`, defaults to ``all_time``
    :type range: ``str``
    :statuscode 200: Successful query, you have data!
    :statuscode 204: Statistics for the user haven't been calculated, empty response will be returned
    :statuscode 400: Bad request, check ``response['error']`` for more details
    :statuscode 404: User not found
    :resheader Content-Type: *application/json*

    """
    user, stats_range = _validate_stats_user_params(user_name)

    stats = db_stats.get(user['id'], "daily_activity", stats_range, DailyActivityRecord)
    if stats is None:
        raise APINoContent('')

    daily_activity_unprocessed = [x.dict() for x in stats.data.__root__]
    daily_activity = {calendar.day_name[day]: [{"hour": hour, "listen_count": 0} for hour in range(0, 24)] for day in
                      range(0, 7)}

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
        "from_ts": stats.from_ts,
        "to_ts": stats.to_ts,
        "range": stats_range,
        "last_updated": stats.last_updated
    }})


@stats_api_bp.route("/user/<user_name>/artist-map")
@crossdomain
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
        - We cache the results for this query for a week to improve page load times, if you want to request fresh data
          you can use the ``force_recalculate`` flag.

    :param range: Optional, time interval for which statistics should be returned, possible values are
        :data:`~data.model.common_stat.ALLOWED_STATISTICS_RANGE`, defaults to ``all_time``
    :type range: ``str``
    :param force_recalculate: Optional, recalculate the data instead of returning the cached result.
    :type force_recalculate: ``bool``
    :statuscode 200: Successful query, you have data!
    :statuscode 204: Statistics for the user haven't been calculated, empty response will be returned
    :statuscode 400: Bad request, check ``response['error']`` for more details
    :statuscode 404: User not found
    :resheader Content-Type: *application/json*

    """
    user, stats_range = _validate_stats_user_params(user_name)
    result = _get_artist_map_stats(user["id"], stats_range)
    return jsonify({
        "payload": {
            "user_id": user_name,
            "range": stats_range,
            "from_ts": result.from_ts,
            "to_ts": result.to_ts,
            "last_updated": result.last_updated,
            "artist_map": [x.dict() for x in result.data.__root__]
        }
    })


@stats_api_bp.route("/sitewide/artists")
@crossdomain
@ratelimit()
def get_sitewide_artist():
    """
    Get sitewide top artists.


    A sample response from the endpoint may look like:

    .. code-block:: json

        {
            "payload": {
                "artists": [
                    {
                        "artist_mbids": [],
                        "artist_name": "Kanye West",
                        "listen_count": 1305
                    },
                    {
                        "artist_mbids": ["0b30341b-b59d-4979-8130-b66c0e475321"],
                        "artist_name": "Lil Nas X",
                        "listen_count": 1267
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
        - ``artist_mbids`` is optional field and may not be present in all the entries
        - We only calculate the top 1000 artists for each time period.

    :param count: Optional, number of artists to return for each time range,
        Default: :data:`~webserver.views.api.DEFAULT_ITEMS_PER_GET`
        Max: :data:`~webserver.views.api.MAX_ITEMS_PER_GET`
    :type count: ``int``
    :param offset: Optional, number of artists to skip from the beginning, for pagination.
        Ex. An offset of 5 means the top 5 artists will be skipped, defaults to 0
    :type offset: ``int``
    :param range: Optional, time interval for which statistics should be returned, possible values are
        :data:`~data.model.common_stat.ALLOWED_STATISTICS_RANGE`, defaults to ``all_time``
    :type range: ``str``
    :statuscode 200: Successful query, you have data!
    :statuscode 204: Statistics haven't been calculated, empty response will be returned
    :statuscode 400: Bad request, check ``response['error']`` for more details
    :resheader Content-Type: *application/json*
    """
    return _get_sitewide_stats("artists")


@stats_api_bp.route("/sitewide/releases")
@crossdomain
@ratelimit()
def get_sitewide_release():
    """
    Get sitewide top releases.

    A sample response from the endpoint may look like:

    .. code-block:: json

        {
            "payload": {
                "releases": [
                    {
                        "artist_mbids": [],
                        "artist_name": "Coldplay",
                        "listen_count": 26,
                        "release_mbid": "",
                        "release_name": "Live in Buenos Aires"
                    },
                    {
                        "artist_mbids": [],
                        "artist_name": "Ellie Goulding",
                        "listen_count": 25,
                        "release_mbid": "",
                        "release_name": "Delirium (Deluxe)"
                    },
                    {
                        "artist_mbids": [],
                        "artist_name": "The Fray",
                        "listen_count": 25,
                        "release_mbid": "",
                        "release_name": "How to Save a Life"
                    },
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
        - ``artist_mbids`` and ``release_mbid`` are optional fields and may not be present in all the responses

    :param count: Optional, number of artists to return for each time range,
        Default: :data:`~webserver.views.api.DEFAULT_ITEMS_PER_GET`
        Max: :data:`~webserver.views.api.MAX_ITEMS_PER_GET`
    :type count: ``int``
    :param offset: Optional, number of artists to skip from the beginning, for pagination.
        Ex. An offset of 5 means the top 5 artists will be skipped, defaults to 0
    :type offset: ``int``
    :param range: Optional, time interval for which statistics should be returned, possible values are
        :data:`~data.model.common_stat.ALLOWED_STATISTICS_RANGE`, defaults to ``all_time``
    :type range: ``str``
    :statuscode 200: Successful query, you have data!
    :statuscode 204: Statistics haven't been calculated, empty response will be returned
    :statuscode 400: Bad request, check ``response['error']`` for more details
    :resheader Content-Type: *application/json*
    """
    return _get_sitewide_stats("releases")


@stats_api_bp.route("/sitewide/recordings")
@crossdomain
@ratelimit()
def get_sitewide_recording():
    """
    Get sitewide top recordings.

    A sample response from the endpoint may look like:

    .. code-block:: json

        {
            "payload": {
                "recordings": [
                    {
                        "artist_mbids": [],
                        "artist_name": "Ellie Goulding",
                        "listen_count": 25,
                        "recording_mbid": "0fe11cd3-0be4-467b-84fa-0bd524d45d74",
                        "release_mbid": "",
                        "release_name": "Delirium (Deluxe)",
                        "track_name": "Love Me Like You Do - From \\"Fifty Shades of Grey\\""
                    },
                    {
                        "artist_mbids": [],
                        "artist_name": "The Fray",
                        "listen_count": 23,
                        "recording_mbid": "0008ab49-a6ad-40b5-aa90-9d2779265c22",
                        "release_mbid": "",
                        "release_name": "How to Save a Life",
                        "track_name": "How to Save a Life"
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
        - We only calculate the top 1000 all_time recordings
        - ``artist_mbids``, ``release_name``, ``release_mbid`` and ``recording_mbid`` are optional fields and
         may not be present in all the responses

    :param count: Optional, number of artists to return for each time range,
        Default: :data:`~webserver.views.api.DEFAULT_ITEMS_PER_GET`
        Max: :data:`~webserver.views.api.MAX_ITEMS_PER_GET`
    :type count: ``int``
    :param offset: Optional, number of artists to skip from the beginning, for pagination.
        Ex. An offset of 5 means the top 5 artists will be skipped, defaults to 0
    :type offset: ``int``
    :param range: Optional, time interval for which statistics should be returned, possible values are
        :data:`~data.model.common_stat.ALLOWED_STATISTICS_RANGE`, defaults to ``all_time``
    :type range: ``str``
    :statuscode 200: Successful query, you have data!
    :statuscode 204: Statistics haven't been calculated, empty response will be returned
    :statuscode 400: Bad request, check ``response['error']`` for more details
    :resheader Content-Type: *application/json*
    """
    return _get_sitewide_stats("recordings")


def _get_sitewide_stats(entity: str):
    stats_range = request.args.get("range", default="all_time")
    if not _is_valid_range(stats_range):
        raise APIBadRequest(f"Invalid range: {stats_range}")

    offset = get_non_negative_param("offset", default=0)
    count = get_non_negative_param("count", default=DEFAULT_ITEMS_PER_GET)

    stats = db_stats.get(db_stats.SITEWIDE_STATS_USER_ID, entity, stats_range, EntityRecord)
    if stats is None:
        raise APINoContent("")

    entity_list, total_entity_count = _process_user_entity(stats, offset, count)
    return jsonify({
        "payload": {
            entity: entity_list,
            "range": stats_range,
            "offset": offset,
            "count": total_entity_count,
            "from_ts": stats.from_ts,
            "to_ts": stats.to_ts,
            "last_updated": stats.last_updated
        }
    })


@stats_api_bp.route("/sitewide/listening-activity")
@crossdomain
@ratelimit()
def get_sitewide_listening_activity():
    """
    Get the listening activity for entire site. The listening activity shows the number of listens
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
                    }
                ],
                "to_ts": 1589155200,
                "range": "week"
            }
        }

    .. note::
        - This endpoint is currently in beta
        - The example above shows the data for three days only, however we calculate the statistics for
          the current time range and the previous time range. For example for weekly statistics the data
          is calculated for the current as well as the past week.

    :param range: Optional, time interval for which statistics should be returned, possible values are
        :data:`~data.model.common_stat.ALLOWED_STATISTICS_RANGE`, defaults to ``all_time``
    :type range: ``str``
    :statuscode 200: Successful query, you have data!
    :statuscode 204: Statistics for the user haven't been calculated, empty response will be returned
    :statuscode 400: Bad request, check ``response['error']`` for more details
    :resheader Content-Type: *application/json*
    """
    stats_range = request.args.get("range", default="all_time")
    if not _is_valid_range(stats_range):
        raise APIBadRequest(f"Invalid range: {stats_range}")

    stats = db_stats.get(
        db_stats.SITEWIDE_STATS_USER_ID,
        "listening_activity",
        stats_range,
        ListeningActivityRecord
    )
    if stats is None:
        raise APINoContent('')

    listening_activity = [x.dict() for x in stats.data.__root__]
    return jsonify({"payload": {
        "listening_activity": listening_activity,
        "from_ts": stats.from_ts,
        "to_ts": stats.to_ts,
        "range": stats_range,
        "last_updated": stats.last_updated
    }})


@stats_api_bp.route("/sitewide/artist-map")
@crossdomain
@ratelimit()
def get_sitewide_artist_map():
    """
    Get the sitewide artist map. The artist map shows the number of artists listened to by users
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
            }
        }

    .. note::
        - This endpoint is currently in beta
        - We cache the results for this query for a week to improve page load times, if you want to request fresh data
          you can use the ``force_recalculate`` flag.

    :param range: Optional, time interval for which statistics should be returned, possible values are
        :data:`~data.model.common_stat.ALLOWED_STATISTICS_RANGE`, defaults to ``all_time``
    :type range: ``str``
    :param force_recalculate: Optional, recalculate the data instead of returning the cached result.
    :type force_recalculate: ``bool``
    :statuscode 200: Successful query, you have data!
    :statuscode 204: Statistics for the user haven't been calculated, empty response will be returned
    :statuscode 400: Bad request, check ``response['error']`` for more details
    :statuscode 404: User not found
    :resheader Content-Type: *application/json*

    """
    stats_range = request.args.get("range", default="all_time")
    if not _is_valid_range(stats_range):
        raise APIBadRequest(f"Invalid range: {stats_range}")

    result = _get_artist_map_stats(db_stats.SITEWIDE_STATS_USER_ID, stats_range)

    return jsonify({
        "payload": {
            "range": stats_range,
            "from_ts": result.from_ts,
            "to_ts": result.to_ts,
            "last_updated": result.last_updated,
            "artist_map": [x.dict() for x in result.data.__root__]
        }
    })


def _get_artist_map_stats(user_id, stats_range):
    recalculate_param = request.args.get('force_recalculate', default='false')
    if recalculate_param.lower() not in ['true', 'false']:
        raise APIBadRequest("Invalid value of force_recalculate: {}".format(recalculate_param))
    force_recalculate = recalculate_param.lower() == 'true'

    stats = None
    if not force_recalculate:
        stats = db_stats.get(user_id, "artistmap", stats_range, UserArtistMapRecord)

    if stats is None:
        artist_stats = db_stats.get(user_id, "artists", stats_range, EntityRecord)
        if artist_stats is None:
            raise APINoContent('')

        # Calculate the data
        artist_mbid_counts = defaultdict(int)
        for artist in artist_stats.data.__root__:
            if artist.artist_mbid:
                artist_mbid_counts[artist.artist_mbid] += artist.listen_count

        country_code_data = _get_country_wise_counts(artist_mbid_counts)

        try:
            db_stats.insert_artist_map(user_id, stats_range, artist_stats.from_ts, artist_stats.to_ts, country_code_data)
        except HTTPError as e:
            current_app.logger.error(f"{e}. Response: %s", e.response.json(), exc_info=True)

        stats = StatApi[UserArtistMapRecord](
            user_id=user_id,
            from_ts=artist_stats.from_ts,
            to_ts=artist_stats.to_ts,
            stats_range=stats_range,
            data=StatRecordList[UserArtistMapRecord](__root__=country_code_data),
            last_updated=int(datetime.now().timestamp())
        )

    return stats


@stats_api_bp.route("/user/<user_name>/year-in-music")
@stats_api_bp.route("/user/<user_name>/year-in-music/<int:year>")
def year_in_music(user_name: str, year: int = 2022):
    """ Get data for year in music stuff """
    if year != 2021 and year != 2022:
        raise APINotFound(f"Cannot find Year in Music report for year: {year}")

    user = db_user.get_by_mb_id(user_name)
    if user is None:
        raise APINotFound(f"Cannot find user: {user_name}")

    return jsonify({
        "payload": {
            "user_name": user_name,
            "data": db_year_in_music.get(user["id"], year) or {}
        }
    })


def _process_user_entity(stats: StatApi[EntityRecord], offset: int, count: int) -> Tuple[list[dict], int]:
    """ Process the statistics data according to query params

        Args:
            stats: the dictionary containing statistic data
            offset: number of entities to skip from the beginning
            count: number of entities to return

        Returns:
            entity_list, total_entity_count: a tuple of a list and integer
                containing the entities processed according to the query params and
                total number of entities respectively
    """

    count = min(count, MAX_ITEMS_PER_GET)
    count = count + offset
    total_entity_count = stats.count
    entity_list = [x.dict() for x in stats.data.__root__[offset:count]]

    return entity_list, total_entity_count


def _validate_stats_user_params(user_name) -> Tuple[Dict, str]:
    """ Validate and return the user and common stats params """
    user = db_user.get_by_mb_id(user_name)
    if user is None:
        raise APINotFound(f"Cannot find user: {user_name}")

    stats_range = request.args.get("range", default="all_time")
    if not _is_valid_range(stats_range):
        raise APIBadRequest(f"Invalid range: {stats_range}")
    return user, stats_range


def _is_valid_range(stats_range: str) -> bool:
    """ Check if the provided stats time range is valid

    Args:
        stats_range: the range to validate

    Returns:
        result: True if given range is valid
    """
    return stats_range in StatisticsRange.__members__


def _get_country_wise_counts(artist_mbids: Dict[str, int]) -> List[UserArtistMapRecord]:
    """ Get country wise listen counts and artist lists from dict of given artist_mbids and listen counts
    """
    # Get artist_origin_countries from artist_credit_ids
    artist_country_codes = _get_country_code_from_mbids(artist_mbids.keys())

    # Map country codes to appropriate MBIDs and listen counts
    result = defaultdict(lambda: {
        "artist_count": 0,
        "listen_count": 0,
        "artists": []
    })
    for artist_mbid, listen_count in artist_mbids.items():
        if artist_mbid in artist_country_codes:
            # TODO: add a test to handle the case where pycountry doesn't recognize the country
            country_alpha_3 = pycountry.countries.get(alpha_2=artist_country_codes[artist_mbid]["country_code"])
            if country_alpha_3 is None:
                continue
            result[country_alpha_3.alpha_3]["artist_count"] += 1
            result[country_alpha_3.alpha_3]["listen_count"] += listen_count
            result[country_alpha_3.alpha_3]["artists"].append(
                UserArtistMapArtist(
                    artist_mbid=artist_mbid,
                    # we use the artist name from the country code endpoint because the
                    # other artist name we have in stats is actually artist credit name where
                    # this artist name is the actual artist name associated with the mbid
                    artist_name=artist_country_codes[artist_mbid]["artist_name"],
                    listen_count=listen_count
                )
            )

    artist_map_data = []
    for country, data in result.items():
        # sort artists within each country based on descending order of listen counts
        data["artists"].sort(key=lambda x: x.listen_count, reverse=True)
        artist_map_data.append(UserArtistMapRecord(country=country, **data))
    return artist_map_data


def _get_country_code_from_mbids(artist_mbids: Iterable[str]) -> Dict[str, Dict]:
    """ Get a list of artist_country_code corresponding to the input artist_mbids
    """
    request_data = [{"artist_mbid": artist_mbid} for artist_mbid in artist_mbids]
    artist_country_code = {}
    if len(request_data) > 0:
        try:
            result = requests.post(
                f"{current_app.config['LISTENBRAINZ_LABS_API_URL']}/artist-country-code-from-artist-mbid/json",
                json=request_data,
                params={"count": len(request_data)}
            )
            # Raise error if non 200 response is received
            result.raise_for_status()
            data = result.json()
            artist_country_code = {entry["artist_mbid"]: entry for entry in data}
        except requests.RequestException as err:
            current_app.logger.error("Error while getting artist_artist_country_code, {}".format(err), exc_info=True)
            error_msg = ("An error occurred while calculating artist_map data, "
                         "try setting 'force_recalculate' to 'false' to get a cached copy if available"
                         "Payload: {}. Response: {}".format(request_data, result.text))
            raise APIInternalServerError(error_msg)
    return artist_country_code
