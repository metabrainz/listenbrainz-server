from datetime import datetime
from enum import Enum

from flask import Blueprint, current_app, jsonify, request

import listenbrainz.db.stats as db_stats
import listenbrainz.db.user as db_user
from listenbrainz.webserver.decorators import crossdomain
from listenbrainz.webserver.errors import (APIBadRequest,
                                           APIInternalServerError,
                                           APINoContent, APINotFound,
                                           APIServiceUnavailable,
                                           APIUnauthorized)
from listenbrainz.webserver.rate_limiter import ratelimit
from listenbrainz.webserver.views.api_tools import (DEFAULT_ITEMS_PER_GET,
                                                    MAX_ITEMS_PER_GET)

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


    An sample response from the endpoint may look like::

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

    stats = db_stats.get_user_artists(user['id'])
    if stats is None:
        raise APINoContent('')

    stats_range = request.args.get('range', default='all_time')
    if not _is_valid_range(stats_range):
        raise APIBadRequest("Invalid range: {}".format(stats_range))

    offset = _get_non_negative_param('offset', default=0)
    count = _get_non_negative_param('count', default=DEFAULT_ITEMS_PER_GET)

    entity_list, total_entity_count = _process_entity(user_name, stats, stats_range, offset, count, entity='artist')
    return jsonify({'payload': {
        "user_id": user_name,
        'artists': entity_list,
        "count": len(entity_list),
        "total_artist_count": total_entity_count,
        "offset": offset,
        "range": stats_range,
        "from_ts": int(stats['artist'][stats_range]['from_ts']),
        "to_ts": int(stats['artist'][stats_range]['to_ts']),
        "last_updated": int(stats['last_updated'].timestamp())
    }})


@stats_api_bp.route("/user/<user_name>/releases")
@crossdomain()
@ratelimit()
def get_release(user_name):
    """
    Get top releases for user ``user_name``.


    An sample response from the endpoint may look like::

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

    stats = db_stats.get_user_releases(user['id'])
    if stats is None:
        raise APINoContent('')

    stats_range = request.args.get('range', default='all_time')
    if not _is_valid_range(stats_range):
        raise APIBadRequest("Invalid range: {}".format(stats_range))

    offset = _get_non_negative_param('offset', default=0)
    count = _get_non_negative_param('count', default=DEFAULT_ITEMS_PER_GET)

    entity_list, total_entity_count = _process_entity(user_name, stats, stats_range, offset, count, entity='release')
    return jsonify({'payload': {
        "user_id": user_name,
        'releases': entity_list,
        "count": len(entity_list),
        "total_release_count": total_entity_count,
        "offset": offset,
        "range": stats_range,
        "from_ts": int(stats['release'][stats_range]['from_ts']),
        "to_ts": int(stats['release'][stats_range]['to_ts']),
        "last_updated": int(stats['last_updated'].timestamp())
    }})


def _process_entity(user_name, stats, stats_range, offset, count, entity):
    """ Process the statistics data according to query params

        Args:
            user_name (str): musicbrainz_id of the user
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

    plural_entity = entity + 's'

    count = min(count, MAX_ITEMS_PER_GET)
    try:
        total_entity_count = stats[entity][stats_range]['count']
    except (TypeError, KeyError):
        raise APINoContent('')

    count = count + offset
    entity_list = stats[entity][stats_range][plural_entity][offset:count]

    return entity_list, total_entity_count


def _get_non_negative_param(param, default=None):
    """ Gets the value of a request parameter, validating that it is non-negative

    Args:
        param (str): the parameter to get
        default: the value to return if the parameter doesn't exist in the request
    """
    value = request.args.get(param, default)
    if value is not None:
        try:
            value = int(value)
        except ValueError:
            raise APIBadRequest("'{}' should be a non-negative integer".format(param))

        if value < 0:
            raise APIBadRequest("'{}' should be a non-negative integer".format(param))
    return value


def _is_valid_range(stats_range):
    """ Check if the provided stats time range is valid

    Args:
        stats_range (str): the range to validate

    Returns:
        result (bool): True if given range is valid
    """
    return stats_range in StatisticsRange.__members__
