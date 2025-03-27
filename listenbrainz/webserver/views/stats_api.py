import calendar
from collections import defaultdict
from datetime import datetime
from typing import Dict, List, Tuple, Iterable

from requests import HTTPError

import listenbrainz.db.stats as db_stats
import listenbrainz.db.user as db_user
import pycountry
import requests
import heapq

from data.model.common_stat import StatApi, StatisticsRange, StatRecordList
from data.model.user_artist_map import UserArtistMapRecord, UserArtistMapArtist
from flask import Blueprint, current_app, jsonify, request

from data.model.user_daily_activity import DailyActivityRecord
from data.model.user_entity import EntityRecord
from data.model.user_listening_activity import ListeningActivityRecord
from listenbrainz.db import year_in_music as db_year_in_music
from listenbrainz.webserver import db_conn
from listenbrainz.webserver.decorators import crossdomain
from listenbrainz.webserver.errors import (APIBadRequest,
                                           APIInternalServerError,
                                           APINoContent, APINotFound)
from brainzutils.ratelimit import ratelimit
from listenbrainz.webserver.views.api_tools import (DEFAULT_ITEMS_PER_GET,
                                                    MAX_ITEMS_PER_GET,
                                                    get_non_negative_param, is_valid_uuid)


stats_api_bp = Blueprint('stats_api_v1', __name__)


@stats_api_bp.get("/user/<user_name>/artists")
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
        ``artist_mbids`` is an optional field and may not be present in all the responses


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


@stats_api_bp.get("/user/<user_name>/releases")
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

        ``artist_mbids`` and ``release_mbid`` are optional fields and may not be present in all the responses

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


@stats_api_bp.get("/user/<user_name>/release-groups")
@crossdomain
@ratelimit()
def get_release_group(user_name):
    """
    Get top release groups for user ``user_name``.

    A sample response from the endpoint may look like:

    .. code-block:: json

        {
            "payload": {
                "release_groups": [
                    {
                        "artist_mbids": [
                            "62162215-b023-4f0e-84bd-1e9412d5b32c",
                            "faf4cefb-036c-4c88-b93a-5b03dd0a0e6b",
                            "e07d9474-00ea-4460-ac27-88b46b3d976e"
                        ],
                        "artist_name": "All Time Low ft. Demi Lovato & blackbear",
                        "caa_id": 29179588350,
                        "caa_release_mbid": "ee65192d-31f3-437a-b170-9158d2172dbc",
                        "listen_count": 456,
                        "release_group_mbid": "326b4a29-dff5-4fab-87dc-efc1494001c6",
                        "release_group_name": "Monsters"
                    },
                    {
                        "artist_mbids": [
                            "c8b03190-306c-4120-bb0b-6f2ebfc06ea9"
                        ],
                        "artist_name": "The Weeknd",
                        "caa_id": 25720993837,
                        "caa_release_mbid": "19e4f6cc-ca0c-4897-8dfc-a36914b7f998",
                        "listen_count": 381,
                        "release_group_mbid": "78570bea-2a26-467c-a3db-c52723ceb394",
                        "release_group_name": "After Hours"
                    }
                ],
                "count": 2,
                "total_release_group_count": 175,
                "range": "all_time",
                "last_updated": 1588494361,
                "user_id": "John Doe",
                "from_ts": 1009823400,
                "to_ts": 1590029157
            }
        }

    .. note::

        ``artist_mbids`` and ``release_group_mbid`` are optional fields and may not be present in all the responses

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
    return _get_entity_stats(user_name, "release_groups", "total_release_group_count")


@stats_api_bp.get("/user/<user_name>/recordings")
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


def _get_entity_stats(user_name: str, entity: str, count_key: str, entire_range: bool = False):
    user, stats_range = _validate_stats_user_params(user_name)

    offset = get_non_negative_param("offset", default=0)
    count = get_non_negative_param("count", default=DEFAULT_ITEMS_PER_GET)

    stats = db_stats.get(user["id"], entity, stats_range, EntityRecord)
    if stats is None:
        raise APINoContent('')

    entity_list, total_entity_count = _process_user_entity(stats, offset, count, entire_range)
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


def get_entity_stats_last_updated(user_name: str, entity: str, count_key: str):
    user, stats_range = _validate_stats_user_params(user_name)
    stats = db_stats.get(user["id"], entity, stats_range, EntityRecord)
    if stats is None:
        return None
    return stats.last_updated


@stats_api_bp.get("/user/<user_name>/listening-activity")
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

def _get_artist_activity(release_groups_list):
    result = defaultdict(lambda: {"listen_count": 0, "albums": {}})
 
    for release_group in release_groups_list:
        artist_names = release_group["artist_name"].split(",")
        listen_count = release_group["listen_count"]
        release_group_name = release_group["release_group_name"]
        release_group_mbid = release_group.get("release_group_mbid")
 
        for artist_name in artist_names:
            artist_entry = result[artist_name]
            artist_entry["listen_count"] += listen_count
 
            if release_group_name in artist_entry["albums"]:
                artist_entry["albums"][release_group_name]["listen_count"] += listen_count
            else:
                artist_entry["albums"][release_group_name] = {
                    "name": release_group_name,
                    "listen_count": listen_count,
                    "release_group_mbid": release_group_mbid,
                }
 
    for artist_name, artist_data in result.items():
        artist_data["name"] = artist_name
        artist_data["albums"] = list(artist_data["albums"].values())

    return heapq.nlargest(15, result.values(), key=lambda x: x["listen_count"])

@stats_api_bp.get("/user/<user_name>/artist-activity")
@crossdomain
@ratelimit()
def get_artist_activity(user_name: str):
    """
    Get the artist activity for user ``user_name``. The artist activity shows the total number of listens
    for each artist along with their albums and corresponding listen counts.

    A sample response from the endpoint may look like:

    .. code-block:: json

        {
            "result": [
                {
                    "name": "Radiohead",
                    "listen_count": 120,
                    "albums": [
                        {"name": "OK Computer", "listen_count": 45},
                        {"name": "In Rainbows", "listen_count": 75}
                    ]
                },
                {
                    "name": "The Beatles",
                    "listen_count": 95,
                    "albums": [
                        {"name": "Abbey Road", "listen_count": 60},
                        {"name": "Revolver", "listen_count": 35}
                    ]
                }
            ]
        }

    .. note::

        - The example above shows artist activity data with two artists and their respective albums.
        - The statistics are aggregated based on the number of listens recorded for each artist and their albums.

    :statuscode 200: Successful query, you have data!
    :statuscode 204: Statistics for the user haven't been calculated, empty response will be returned
    :statuscode 400: Bad request, check ``response['error']`` for more details
    :statuscode 404: User not found
    :resheader Content-Type: *application/json*
    """
    user, stats_range = _validate_stats_user_params(user_name)
    offset = get_non_negative_param("offset", default=0)
    count = get_non_negative_param("count", default=DEFAULT_ITEMS_PER_GET)
    stats = db_stats.get(user["id"], "release_groups", stats_range, EntityRecord)
    if stats is None:
        raise APINoContent('')

    release_groups_list, _ = _process_user_entity(stats, offset, count, entire_range=True)
    result = _get_artist_activity(release_groups_list)
    return jsonify({"result": result})
    

@stats_api_bp.get("/user/<user_name>/daily-activity")
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


@stats_api_bp.get("/user/<user_name>/artist-map")
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
    stats = db_stats.get(user["id"], "artist_map", stats_range, UserArtistMapRecord)
    if stats is None:
        raise APINoContent('')
    return jsonify({
        "payload": {
            "user_id": user_name,
            "range": stats_range,
            "from_ts": stats.from_ts,
            "to_ts": stats.to_ts,
            "last_updated": stats.last_updated,
            "artist_map": [x.dict() for x in stats.data.__root__]
        }
    })


@stats_api_bp.get("/artist/<artist_mbid>/listeners")
@crossdomain
@ratelimit()
def get_artist_listeners(artist_mbid):
    """ Get top listeners for artist ``artist_mbid``. This includes the total listen count for the entity
    and top N listeners with their individual listen count for that artist in a given time range. A sample
    response from the endpoint may look like:

    .. code-block:: json

        {
          "payload": {
            "artist_mbid": "00034ede-a1f1-4219-be39-02f36853373e",
            "artist_name": "O Rappa",
            "from_ts": 1009843200,
            "last_updated": 1681839677,
            "listeners": [
              {
                "listen_count": 2469,
                "user_name": "RosyPsanda"
              },
              {
                "listen_count": 1858,
                "user_name": "alexyagui"
              },
              {
                "listen_count": 578,
                "user_name": "rafael_gn"
              },
              {
                "listen_count": 8,
                "user_name": "italooliveira"
              },
              {
                "listen_count": 7,
                "user_name": "paulodesouza"
              },
              {
                "listen_count": 1,
                "user_name": "oldpunisher"
              }
            ],
            "stats_range": "all_time",
            "to_ts": 1681777035,
            "total_listen_count": 16393
          }
        }

    :param range: Optional, time interval for which statistics should be returned, possible values are
        :data:`~data.model.common_stat.ALLOWED_STATISTICS_RANGE`, defaults to ``all_time``
    :type range: ``str``
    :statuscode 200: Successful query, you have data!
    :statuscode 204: Statistics for the user haven't been calculated or the entity does not exist,
        empty response will be returned
    :statuscode 400: Bad request, check ``response['error']`` for more details
    :statuscode 404: Entity not found
    :resheader Content-Type: *application/json*
    """
    return _get_entity_listeners("artists", artist_mbid)


@stats_api_bp.get("/release-group/<release_group_mbid>/listeners")
@crossdomain
@ratelimit()
def get_release_group_listeners(release_group_mbid):
    """ Get top listeners for release group ``release_group_mbid``. This includes the total listen count
    for the entity and top N listeners with their individual listen count for that release group in a
    given time range. A sample response from the endpoint may look like:

    .. code-block:: json

        {
          "payload": {
            "artist_mbids": [
              "c234fa42-e6a6-443e-937e-2f4b073538a3"
            ],
            "artist_name": "Chris Brown",
            "caa_id": 23564822587,
            "caa_release_mbid": "25f18616-5a9c-470e-964d-4eb8a511435b",
            "from_ts": 1009843200,
            "last_updated": 1681843150,
            "listeners": [
              {
                "listen_count": 2365,
                "user_name": "purpleyor"
              },
              {
                "listen_count": 570,
                "user_name": "dndty"
              },
              {
                "listen_count": 216,
                "user_name": "iammsyre"
              },
              {
                "listen_count": 141,
                "user_name": "dpmittal"
              },
              {
                "listen_count": 33,
                "user_name": "tazlad"
              },
              {
                "listen_count": 30,
                "user_name": "ratkutti"
              },
              {
                "listen_count": 22,
                "user_name": "Raymorjamiek"
              },
              {
                "listen_count": 21,
                "user_name": "MJJMC"
              },
              {
                "listen_count": 12,
                "user_name": "fookever"
              },
              {
                "listen_count": 8,
                "user_name": "Jamjamk12071983"
              },
              {
                "listen_count": 1,
                "user_name": "hassanymoses"
              },
              {
                "listen_count": 1,
                "user_name": "iJays"
              }
            ],
            "release_group_mbid": "087b3a7d-d532-44d9-b37a-84427677ddcd",
            "release_group_name": "Indigo",
            "stats_range": "all_time",
            "to_ts": 1681777035,
            "total_listen_count": 10291
          }
        }

    :param range: Optional, time interval for which statistics should be returned, possible values are
        :data:`~data.model.common_stat.ALLOWED_STATISTICS_RANGE`, defaults to ``all_time``
    :type range: ``str``
    :statuscode 200: Successful query, you have data!
    :statuscode 204: Statistics for the user haven't been calculated or the entity does not exist,
        empty response will be returned
    :statuscode 400: Bad request, check ``response['error']`` for more details
    :statuscode 404: Entity not found
    :resheader Content-Type: *application/json*
    """
    return _get_entity_listeners("release_groups", release_group_mbid)


def _get_entity_listeners(entity, mbid):
    if not is_valid_uuid(mbid):
        raise APIBadRequest(f"{mbid} mbid format invalid.")

    stats_range = request.args.get("range", default="all_time")
    if not _is_valid_range(stats_range):
        raise APIBadRequest(f"Invalid range: {stats_range}")

    stats = db_stats.get_entity_listener(db_conn, entity, mbid, stats_range)
    if stats is None:
        raise APINoContent("")

    return jsonify({"payload": stats})


@stats_api_bp.get("/sitewide/artists")
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
                "total_artist_count": 2,
                "range": "year",
                "last_updated": 1588494361,
                "from_ts": 1009823400,
                "to_ts": 1590029157
            }
        }

    .. note::
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
    return _get_sitewide_stats("artists", "total_artist_count")


@stats_api_bp.get("/sitewide/releases")
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
                "total_release_count": 2,
                "range": "year",
                "last_updated": 1588494361,
                "from_ts": 1009823400,
                "to_ts": 1590029157
            }
        }

    .. note::

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
    return _get_sitewide_stats("releases", "total_release_count")


@stats_api_bp.get("/sitewide/release-groups")
@crossdomain
@ratelimit()
def get_sitewide_release_group():
    """
    Get sitewide top release groups.

    A sample response from the endpoint may look like:

    .. code-block:: json

        {
            "payload": {
                "release_groups": [
                    {
                        "artist_mbids": [
                            "62162215-b023-4f0e-84bd-1e9412d5b32c",
                            "faf4cefb-036c-4c88-b93a-5b03dd0a0e6b",
                            "e07d9474-00ea-4460-ac27-88b46b3d976e"
                        ],
                        "artist_name": "All Time Low ft. Demi Lovato & blackbear",
                        "caa_id": 29179588350,
                        "caa_release_mbid": "ee65192d-31f3-437a-b170-9158d2172dbc",
                        "listen_count": 456,
                        "release_group_mbid": "326b4a29-dff5-4fab-87dc-efc1494001c6",
                        "release_group_name": "Monsters"
                    },
                    {
                        "artist_mbids": [
                            "c8b03190-306c-4120-bb0b-6f2ebfc06ea9"
                        ],
                        "artist_name": "The Weeknd",
                        "caa_id": 25720993837,
                        "caa_release_mbid": "19e4f6cc-ca0c-4897-8dfc-a36914b7f998",
                        "listen_count": 381,
                        "release_group_mbid": "78570bea-2a26-467c-a3db-c52723ceb394",
                        "release_group_name": "After Hours"
                    }
                ],
                "offset": 0,
                "count": 2,
                "total_release_group_count": 2,
                "range": "year",
                "last_updated": 1588494361,
                "from_ts": 1009823400,
                "to_ts": 1590029157
            }
        }

    .. note::
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
    return _get_sitewide_stats("release_groups", "total_release_group_count")


@stats_api_bp.get("/sitewide/recordings")
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
                "total_recording_count": 2,
                "range": "year",
                "last_updated": 1588494361,
                "from_ts": 1009823400,
                "to_ts": 1590029157
            }
        }

    .. note::
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
    return _get_sitewide_stats("recordings", "total_recording_count")


def _get_sitewide_stats(entity: str, count_key: str, entire_range: bool = False):
    stats_range = request.args.get("range", default="all_time")
    if not _is_valid_range(stats_range):
        raise APIBadRequest(f"Invalid range: {stats_range}")

    offset = get_non_negative_param("offset", default=0)
    count = get_non_negative_param("count", default=DEFAULT_ITEMS_PER_GET)

    stats = db_stats.get_sitewide_stats(entity, stats_range)
    if stats is None:
        raise APINoContent("")

    count = min(count, MAX_ITEMS_PER_GET)
    total_entity_count = stats["count"]

    if entire_range:
        entity_list = stats["data"]
    else:
        entity_list = stats["data"][offset:count + offset]

    return jsonify({
        "payload": {
            entity: entity_list,
            "range": stats_range,
            "offset": offset,
            "count": count,
            count_key: total_entity_count,
            "from_ts": stats["from_ts"],
            "to_ts": stats["to_ts"],
            "last_updated": stats["last_updated"]
        }
    })


@stats_api_bp.get("/sitewide/listening-activity")
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

    stats = db_stats.get_sitewide_stats("listening_activity", stats_range)
    if stats is None:
        raise APINoContent('')

    return jsonify({
        "payload": {
            "listening_activity": stats["data"],
            "from_ts": stats["from_ts"],
            "to_ts": stats["to_ts"],
            "range": stats_range,
            "last_updated": stats["last_updated"]
        }
    })


@stats_api_bp.get("/sitewide/artist-activity")
@crossdomain
@ratelimit()
def get_sitewide_artist_activity():
    """
    Get the sitewide artist activity. The daily activity shows the number of listens
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

    :param range: Optional, time interval for which statistics should be returned, possible values are
        :data:`~data.model.common_stat.ALLOWED_STATISTICS_RANGE`, defaults to ``all_time``
    :type range: ``str``
    :statuscode 200: Successful query, you have data!
    :statuscode 204: Statistics for the user haven't been calculated, empty response will be returned
    :statuscode 400: Bad request, check ``response['error']`` for more details
    :statuscode 404: User not found
    :resheader Content-Type: *application/json*

    """
    stats_range = request.args.get("range", default="all_time")
    if not _is_valid_range(stats_range):
        raise APIBadRequest(f"Invalid range: {stats_range}")
    
    stats = db_stats.get_sitewide_stats("artists", stats_range)
    if stats is None:
        raise APINoContent('')
    
    release_groups_list = stats["data"]
    result = _get_artist_activity(release_groups_list)
    return jsonify({"result": result})


@stats_api_bp.get("/sitewide/artist-map")
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

    :param range: Optional, time interval for which statistics should be returned, possible values are
        :data:`~data.model.common_stat.ALLOWED_STATISTICS_RANGE`, defaults to ``all_time``
    :type range: ``str``
    :statuscode 200: Successful query, you have data!
    :statuscode 204: Statistics for the user haven't been calculated, empty response will be returned
    :statuscode 400: Bad request, check ``response['error']`` for more details
    :statuscode 404: User not found
    :resheader Content-Type: *application/json*

    """
    stats_range = request.args.get("range", default="all_time")
    if not _is_valid_range(stats_range):
        raise APIBadRequest(f"Invalid range: {stats_range}")

    stats = db_stats.get_sitewide_stats("artist_map", stats_range)
    if stats is None:
        raise APINoContent("")

    return jsonify({
        "payload": {
            "artist_map": stats["data"],
            "from_ts": stats["from_ts"],
            "to_ts": stats["to_ts"],
            "last_updated": stats["last_updated"],
            "stats_range": stats_range
        }
    })


@stats_api_bp.get("/user/<user_name>/year-in-music")
@stats_api_bp.get("/user/<user_name>/year-in-music/<int:year>")
@crossdomain
def year_in_music(user_name: str, year: int = 2024):
    """ Get data for year in music stuff """
    if year != 2021 and year != 2022 and year != 2023 and year != 2024:
        raise APINotFound(f"Cannot find Year in Music report for year: {year}")

    user = db_user.get_by_mb_id(db_conn, user_name)
    if user is None:
        raise APINotFound(f"Cannot find user: {user_name}")

    return jsonify({
        "payload": {
            "user_name": user_name,
            "data": db_year_in_music.get(user["id"], year) or {}
        }
    })


def _process_user_entity(stats: StatApi[EntityRecord], offset: int, count: int, entire_range: bool) -> Tuple[list[dict], int]:
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
    if entire_range:
        entity_list = [x.dict() for x in stats.data.__root__]
    else:
        entity_list = [x.dict() for x in stats.data.__root__[offset:count]]

    return entity_list, total_entity_count


def _validate_stats_user_params(user_name) -> Tuple[Dict, str]:
    """ Validate and return the user and common stats params """
    user = db_user.get_by_mb_id(db_conn, user_name)
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
