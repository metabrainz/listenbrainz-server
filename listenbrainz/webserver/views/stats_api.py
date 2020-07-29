import json
import calendar
import requests
from datetime import datetime
from enum import Enum
from typing import List, Union
from collections import defaultdict

import pycountry
from flask import Blueprint, current_app, jsonify, request

import listenbrainz.db.stats as db_stats
import listenbrainz.db.user as db_user
from data.model.user_artist_stat import (UserArtistRecord,
                                         UserArtistStat)
from data.model.user_recording_stat import (UserRecordingRecord,
                                            UserRecordingStat)
from data.model.user_release_stat import (UserReleaseRecord,
                                          UserReleaseStat)
from data.model.user_listening_activity import (
    UserListeningActivityRecord, UserListeningActivityStat)
from data.model.user_artist_map import (UserArtistMapRecord,
                                        UserArtistMapStat,
                                        UserArtistMapStatJson,
                                        UserArtistMapStatRange)
from listenbrainz.webserver.decorators import crossdomain
from listenbrainz.webserver.errors import (APIBadRequest,
                                           APIInternalServerError,
                                           APINoContent, APINotFound,
                                           APIServiceUnavailable,
                                           APIUnauthorized)
from listenbrainz.webserver.rate_limiter import ratelimit
from listenbrainz.webserver.views.api_tools import (DEFAULT_ITEMS_PER_GET,
                                                    MAX_ITEMS_PER_GET,
                                                    _get_non_negative_param)

stats_api_bp = Blueprint('stats_api_v1', __name__)


class StatisticsRange(Enum):
    week = 'week'
    month = 'month'
    year = 'year'
    all_time = 'all_time'


@stats_api_bp.route("/user/<user_name>/artists")
@crossdomain()
@ratelimit()
def get_artist(user_name):
    """
    Get top artists for user ``user_name``.


    A sample response from the endpoint may look like::

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

    offset = _get_non_negative_param('offset', default=0)
    count = _get_non_negative_param('count', default=DEFAULT_ITEMS_PER_GET)

    stats = db_stats.get_user_artists(user['id'], stats_range)
    if stats is None or getattr(stats, stats_range) is None:
        raise APINoContent('')

    entity_list, total_entity_count = _process_entity(stats, stats_range, offset, count, entity='artist')
    from_ts = int(getattr(stats, stats_range).from_ts)
    to_ts = int(getattr(stats, stats_range).to_ts)
    last_updated = int(stats.last_updated.timestamp())

    return jsonify({'payload': {
        "user_id": user_name,
        'artists': entity_list,
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


    A sample response from the endpoint may look like::

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

    offset = _get_non_negative_param('offset', default=0)
    count = _get_non_negative_param('count', default=DEFAULT_ITEMS_PER_GET)

    stats = db_stats.get_user_releases(user['id'], stats_range)
    if stats is None or getattr(stats, stats_range) is None:
        raise APINoContent('')

    entity_list, total_entity_count = _process_entity(stats, stats_range, offset, count, entity='release')
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


    A sample response from the endpoint may look like::

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
                        "track_name": "Love Me Like You Do - From \"Fifty Shades of Grey\""
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
                    },
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

    offset = _get_non_negative_param('offset', default=0)
    count = _get_non_negative_param('count', default=DEFAULT_ITEMS_PER_GET)

    stats = db_stats.get_user_recordings(user['id'], stats_range)
    if stats is None or getattr(stats, stats_range) is None:
        raise APINoContent('')

    entity_list, total_entity_count = _process_entity(stats, stats_range, offset, count, entity='recording')
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

    A sample response from the endpoint may look like::

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

    A sample response from the endpoint may look like::

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
                        }...
                    ],
                    "Tuesday": [...],
                    ...
                }
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
    user = db_user.get_by_mb_id(user_name)
    if user is None:
        raise APINotFound("Cannot find user: {}".format(user_name))

    stats_range = request.args.get('range', default='all_time')
    if not _is_valid_range(stats_range):
        raise APIBadRequest("Invalid range: {}".format(stats_range))

    stats = db_stats.get_user_artists(user['id'], stats_range)
    if stats is None or getattr(stats, stats_range) is None:
        raise APINoContent('')

    artist_msids = []
    artist_mbids = []
    top_artists = getattr(stats, stats_range).artists
    for artist in top_artists:
        if artist.artist_msid is not None:
            artist_msids.append(artist.artist_msid)
        else:
            artist_mbids += artist.artist_mbids

    country_code_data = _get_country_codes(artist_msids, artist_mbids)
    return jsonify({"payload": {
        "country_code_data": country_code_data,
        "user_id": user_name,
        "from_ts": int(getattr(stats, stats_range).from_ts),
        "to_ts": int(getattr(stats, stats_range).to_ts),
        "range": stats_range,
        "last_updated": int(stats.last_updated.timestamp())
    }})


def _process_entity(stats, stats_range, offset, count, entity):
    """ Process the statistics data according to query params

        Args:
            stats (dict): the dictionary containing statistic data
            stats_range (str): time interval for which statistics should be collected
            offset (int): number of entities to skip from the beginning
            count (int): number of entities to return
            entity (str): name of the entity, i.e 'artist', 'release' or 'recording'

        Returns:
            entity_list, total_entity_count (list, int): a tupple of a list and integer
                containing the entities processed according to the query params and
                total number of entities respectively
    """

    count = min(count, MAX_ITEMS_PER_GET)
    count = count + offset
    total_entity_count = getattr(stats, stats_range).count
    entity_list = [x.dict() for x in _get_entity_list(stats, stats_range, entity, offset, count)]

    return entity_list, total_entity_count


def _is_valid_range(stats_range: str) -> bool:
    """ Check if the provided stats time range is valid

    Args:
        stats_range: the range to validate

    Returns:
        result: True if given range is valid
    """
    return stats_range in StatisticsRange.__members__


def _get_entity_list(
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


def _get_country_codes(artist_msids: list, artist_mbids: list) -> List[UserArtistMapRecord]:
    """ Get country codes from list of given artist_msids and artist_mbids
    """
    country_map = defaultdict(int)

    # Map artist_msids to artist_mbids
    all_artist_mbids = _get_mbids_from_msids(artist_msids) + artist_mbids

    # Get artist_origin_countries from artist_credit_ids
    countries = _get_country_code_from_mbids(set(all_artist_mbids))

    # Convert alpha_2 country code to alpha_3 and create a result dictionary
    for country in countries:
        country_alpaha_3 = pycountry.countries.get(alpha_2=country).alpha_3
        if country is None:
            continue
        country_map[country_alpaha_3] += 1

    return [
        {
            "country": country,
            "artist_count": value
        } for country, value in country_map.items()
    ]


def _get_mbids_from_msids(artist_msids: list) -> list:
    """ Get list of artist_mbids corresponding to the input artist_msids
    """
    request_data = [{"artist_msid": artist_msid} for artist_msid in artist_msids]
    artist_mbids = []
    try:
        result = requests.post("http://bono.metabrainz.org:8000/artist-msid-lookup/json", json=request_data)
        # Raise error if non 200 response is received
        result.raise_for_status()
        data = result.json()
        for entry in data:
            artist_mbids += entry['[artist_credit_mbids]']
    except requests.RequestException as err:
        current_app.logger.error("Error while getting artist_mbids, {}".format(err), exc_info=True)

    return artist_mbids


def _get_country_code_from_mbids(artist_mbids: set) -> list:
    """ Get a list of artist_country_code corresponding to the input artist_mbids
    """
    request_data = [{"artist_mbid": artist_mbid} for artist_mbid in artist_mbids]
    country_codes = []
    for entry in request_data:
        try:
            result = requests.post("http://bono.metabrainz.org:8000/artist-mbid-country-code/json", json=[entry])
            # Raise error if non 200 response is received
            result.raise_for_status()
            data = result.json()
            for entry in data:
                country_codes.append(entry['country_code'])
        except requests.RequestException as err:
            current_app.logger.error("Error while getting artist_country_codes, {}, {}".format(err, entry), exc_info=True)
            continue

    return country_codes
