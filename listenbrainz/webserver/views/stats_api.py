from datetime import datetime
from flask import Blueprint, request, jsonify, current_app
from listenbrainz.webserver.errors import APIBadRequest, APIInternalServerError,\
    APIUnauthorized, APINotFound, APIServiceUnavailable
from listenbrainz.webserver.decorators import crossdomain
import listenbrainz.db.user as db_user
import listenbrainz.db.stats as db_stats
from listenbrainz.webserver.rate_limiter import ratelimit

stats_api_bp = Blueprint('stats_api_v1', __name__)


@stats_api_bp.route("/user/<user_name>/artists")
@crossdomain()
@ratelimit()
def get_artist(user_name):
    """
    Get top artists for user ``user_name``. The format for the JSON returned is defined in our :ref:`json-doc`.


    An sample response from the endpoint may look like::

        {
            "payload": {
                "artists": [
                    {
                       "artist_mbids": [93e6118e-7fa8-49f6-9e02-699a1ebce105],
                       "artist_msid": "d340853d-7408-4a0d-89c2-6ff13e568815",
                       "artist_name": "The Local train",
                       "listen_count": 385
                    },
                    {
                       "artist_mbids": [ae9ed5e2-4caf-4b3d-9cb3-2ad626b91714],
                       "artist_msid": "ba64b195-01dd-4613-9534-bb87dc44cffb",
                       "artist_name": "Lenka",
                       "listen_count": 333
                    },
                    {
                       "artist_mbids": [cc197bad-dc9c-440d-a5b5-d52ba2e14234],
                       "artist_msid": "6599e41e-390c-4855-a2ac-68ee798538b4",
                       "artist_name": "Coldplay",
                       "listen_count": 321
                    }
                ],
                "count": 3,
                "range": "all_time"
                "last_updated": 1588494361,
                "user_id": "John Doe"
            }
        }

    .. note::
        - This endpoint is currently in beta
        - ``artist_mbids`` and ``artist_msid`` are optional fields and may not be present in all the responses
        - As of now we are only calculating ``all_time`` statistics for artist.
          However, we plan to add other time intervals in the future.

    :param count: Optional, number of artists to return
    :type count: ``int``
    :param offset: Optional, number of artists to skip from the beginning, for pagination.
        Ex. An offset of 5 means the top 5 artists will be skipped, defaults to 0
    :type offset: ``int``
    :param range: Optional, time interval for which statistics should be collected, defaults to ``all_time``,
        we currently only support all time but more intervals will be added.
    :type range: ``str``
    :statuscode 200: Successful query, you have data!
    :statuscode 204: Statistics for the user haven't been calculated, empty response will be returned
    :statuscode 400: Bad request, check ``response['error']`` for more details
    :statuscode 404: User not found
    :resheader Content-Type: *application/json*
    """

    _range = request.args.get('range', default='all_time')
    if _range != 'all_time':
        raise APIBadRequest("We currently only support the `all_time` range.")

    offset = _get_non_negative_param('offset', default=0)
    count = _get_non_negative_param('count')

    user = db_user.get_by_mb_id(user_name)
    if user is None:
        raise APINotFound("Cannot find user: %s" % user_name)

    stats = db_stats.get_user_artists(user['id'])
    if stats is None:
        return '', 204

    if count is None:
        count = stats['artist']['count']
    count = count + offset
    artist_list = stats['artist']['all_time']['artists'][offset:count]

    return jsonify({'payload': {
        'user_id': user_name,
        "artists": artist_list,
        "count": len(artist_list),
        "offset": offset,
        "range": _range,
        'last_updated': int(stats['last_updated'].timestamp())
    }})


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