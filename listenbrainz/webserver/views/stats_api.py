from datetime import datetime
from flask import Blueprint, jsonify, current_app
from listenbrainz.webserver.errors import APIBadRequest, APIInternalServerError, APIUnauthorized, APINotFound, APIServiceUnavailable
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

    **Note**: This endpoint is currently in beta and the JSON format may change in future

    :statuscode 200: Successfull query
    :statuscode 204: Statistics for user haven't been calculated, empty response will be returned
    :statuscode 404: User not found
    :resheader Content-Type: *application/json*
    """

    user = db_user.get_by_mb_id(user_name)
    if user is None:
        raise APINotFound("Cannot find user: %s" % user_name)

    stats = db_stats.get_user_artists(user['id'])
    if stats is None:
        return '', 204

    return jsonify({'payload': {
        'user_id': user_name,
        'artist': stats['artist'],
        'last_updated': int(stats['last_updated'].timestamp())
    }})
