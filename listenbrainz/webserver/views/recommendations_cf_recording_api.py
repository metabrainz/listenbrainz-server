import listenbrainz.db.user as db_user
import listenbrainz.db.recommendations_cf_recording as db_recommendations_cf_recording

from listenbrainz.webserver.errors import APIBadRequest, APINotFound, APINoContent
from listenbrainz.webserver.views.api_tools import (DEFAULT_ITEMS_PER_GET,
                                                    _get_non_negative_param,
                                                    MAX_ITEMS_PER_GET)

from enum import Enum

from flask import Blueprint, jsonify, request
from listenbrainz.webserver.decorators import crossdomain
from listenbrainz.webserver.rate_limiter import ratelimit

recommendations_cf_recording_api_bp = Blueprint('recommendations_cf_recording_v1', __name__)


class RecommendationArtistType(Enum):
    top = 'top'
    similar = 'similar'


@recommendations_cf_recording_api_bp.route("/user/<user_name>/artist")
@crossdomain()
@ratelimit()
def get_recommendations(user_name):
    """ Get recommendations for user ``user_name``.

        A sample response from the endpoint may look like::

        {
          "payload": {

            "last_updated": 1588494361,

            "<artist_type>": {

              "recording_mbid": [
                "526bd613-fddd-4bd6-9137-ab709ac74cab",
                "a6081bc1-2a76-4984-b21f-38bc3dcca3a5",
                "a6ad0205-6e96-416d-a4e8-edd1773dac09",
                "d8783d03-8a3b-4269-8261-00709d2cfee8"
              ]
            },

            "user_name": "unclejohn69"
            'count': 10,
            'total_recording_mbids_count': 30
          }
        }

        <artist_type>: 'top_artist' or 'similar_artist'

        .. note::
            - This endpoint is experimental and probably will change in the future.

        :param type: Mandatory, artist type in ['top', 'similar']
            Ex. type = top will fetch recommended recording mbids that belong to top artists
                       listened to by the user.
                type = similar will fetch recommended recording mbids that belong to artists
                       similar to top artists listened to by the user.
        :type type: ``str``

        :param count: Optional, number of recording mbids to return, Default: :data:`~webserver.views.api.DEFAULT_ITEMS_PER_GET`
            Max: :data:`~webserver.views.api.MAX_ITEMS_PER_GET`
        :type count: ``int``

        :statuscode 200: Successful query, you have data!
        :statuscode 400: Bad request, check ``response['error']`` for more details
        :statuscode 404: User not found.
        :statuscode 204: Recommendations for the user haven't been generated, empty response will be returned
    """
    user = db_user.get_by_mb_id(user_name)
    if user is None:
        raise APINotFound("Cannot find user: {}".format(user_name))

    artist_type = request.args.get('type')
    if not _is_valid_artist_type(artist_type):
        raise APIBadRequest("Invalid artist type: {}".format(artist_type))

    count = _get_non_negative_param('count', default=DEFAULT_ITEMS_PER_GET)

    recommendations = db_recommendations_cf_recording.get_user_recommendation(user['id'])

    if recommendations is None:
        err_msg = 'No recommendations due to absence of recent listening history for user {}'.format(user_name)
        raise APINoContent(err_msg)

    recording_list, total_recording_count = _process_recommendations(recommendations, count, artist_type, user_name)

    if artist_type == 'top':
        artist_type = 'top_artist'

    elif artist_type == 'similar':
        artist_type = 'similar_artist'

    payload = {
        'payload': {
            artist_type : {
                'recording_mbid': recording_list
            },
            'user_name': user_name,
            'last_updated': int(recommendations['created'].timestamp()),
            'count': len(recording_list),
            'total_recording_mbids_count': total_recording_count
        }
    }

    return jsonify(payload)


def _process_recommendations(recommendations, count, artist_type, user_name):
    """ Process recommendations based on artist type.

        Args:
            recommendations: dict containing user recommendations.
            count (int): number of recommended recording mbids to return.
            artist_type (str): artist type i.e 'top', 'similar'
            user_name (str): musicbrainz id of the user.

        Returns:
            - total_recording_count (int): Total number of recommended mbids in the db for the user.
            - list of recommended mbids based on count.

        Raises:
            APINoContent: if recommendations not found.
    """
    if artist_type == 'similar':
        recording_list = recommendations['recording_mbid']['similar_artist']

    elif artist_type == 'top':
        recording_list = recommendations['recording_mbid']['top_artist']

    total_recording_count = len(recording_list)

    if total_recording_count == 0:
        err_msg = 'No recommendations for user {}, please try again later.'.format(user_name)
        raise APINoContent(err_msg, payload={'last_updated': int(recommendations['created'].timestamp())})

    count = min(count, MAX_ITEMS_PER_GET)

    return recording_list[:count], total_recording_count


def _is_valid_artist_type(artist_type):
    """ Check if artist type is valid.
    """
    if artist_type is None:
        raise APIBadRequest('Please provide artist type')

    return artist_type in RecommendationArtistType.__members__
