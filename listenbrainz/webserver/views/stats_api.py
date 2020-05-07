from datetime import datetime
from flask import Blueprint, request, jsonify, current_app
from listenbrainz.webserver.errors import APIBadRequest, APIInternalServerError,\
    APIUnauthorized, APINotFound, APIServiceUnavailable
from listenbrainz.webserver.decorators import crossdomain
import listenbrainz.db.user as db_user
import listenbrainz.db.stats as db_stats
from listenbrainz.webserver.rate_limiter import ratelimit

stats_api_bp = Blueprint('stats_api_v1', __name__)


@stats_api_bp.route("<user_name>/artist")
@crossdomain()
@ratelimit()
def get_artist(user_name):
    """
    Get top artists for user ``user_name``. The format for the JSON returned is defined in our :ref:`json-doc`.

    **Note**: This endpoint is currently in beta

    :param count: Optional, number of artists to return.
    :statuscode 200: Successful query, you have data!
    :statuscode 204: Statistics for user haven't been calculated, empty response will be returned
    :statuscode 400: Bad request, `count` should be of type integer
    :statuscode 404: User not found
    :resheader Content-Type: *application/json*
    """

    count = request.args.get('count', default=-1)
    try:
        count = int(count)
    except ValueError:
        raise APIBadRequest("Bad request, 'count' should be an integer")

    user = db_user.get_by_mb_id(user_name)
    if user is None:
        raise APINotFound("Cannot find user: %s" % user_name)

    stats = db_stats.get_user_artists(user['id'])
    if stats is None:
        return '', 204

    artist_list = stats['artist']['all_time']['artists']
    if count >= 0:
        artist_list = stats['artist']['all_time']['artists'][:count]

    return jsonify({'payload': {
        'user_id': user_name,
        'artist': {
            "all_time": {
                "artists": artist_list,
                "count": len(artist_list)
            },
        },
        'last_updated': int(stats['last_updated'].timestamp())
    }})
