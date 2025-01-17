import listenbrainz.db.user as db_user
import listenbrainz.db.recommendations_cf_recording as db_recommendations_cf_recording
from listenbrainz.webserver import db_conn

from listenbrainz.webserver.errors import APINotFound, APINoContent
from listenbrainz.webserver.views.api_tools import DEFAULT_ITEMS_PER_GET, get_non_negative_param

from enum import Enum

from flask import Blueprint, jsonify
from listenbrainz.webserver.decorators import crossdomain
from brainzutils.ratelimit import ratelimit

recommendations_cf_recording_api_bp = Blueprint('recommendations_cf_recording_v1', __name__)


class RecommendationArtistType(Enum):
    raw = 'raw'


@recommendations_cf_recording_api_bp.get("/user/<user_name>/recording")
@crossdomain
@ratelimit()
def get_recommendations(user_name):
    """ Get recommendations sorted on rating and ratings for user ``user_name``.

        A sample response from the endpoint may look like:

        .. code-block:: json

            {
                "payload": {
                    "last_updated": 1588494361,
                    "type": "<artist_type>",
                    "entity": "recording",
                    "mbids": [
                        {
                            "recording_mbid": "526bd613-fddd-4bd6-9137-ab709ac74cab",
                            "score": 9.345
                        },
                        {
                            "recording_mbid": "a6081bc1-2a76-4984-b21f-38bc3dcca3a5",
                            "score": 6.998
                        }
                    ],
                    "user_name": "unclejohn69",
                    "count": 10,
                    "total_mbid_count": 30,
                    "offset": 10
                }
            }


        .. note::
            - This endpoint is experimental and probably will change in the future.

        :param count: Optional, number of recording mbids to return, Default: :data:`~webserver.views.api.DEFAULT_ITEMS_PER_GET`
            Max: :data:`~webserver.views.api.MAX_ITEMS_PER_GET`
        :type count: ``int``

        :param offset: Optional, number of mbids to skip from the beginning, for pagination.
            Ex. An offset of 5 means the 5 mbids will be skipped, defaults to 0
        :type offset: ``int``

        :statuscode 200: Successful query, you have data!
        :statuscode 400: Bad request, check ``response['error']`` for more details
        :statuscode 404: User not found.
        :statuscode 204: Recommendations for the user haven't been generated, empty response will be returned
    """
    user = db_user.get_by_mb_id(db_conn, user_name)
    if user is None:
        raise APINotFound("Cannot find user: {}".format(user_name))

    offset = get_non_negative_param('offset', default=0)
    count = get_non_negative_param('count', default=DEFAULT_ITEMS_PER_GET)

    recommendations = db_recommendations_cf_recording.get_user_recommendation(db_conn, user['id'])

    if recommendations is None:
        err_msg = 'No recommendations due to absence of recent listening history for user {}'.format(user_name)
        raise APINoContent(err_msg)

    mbid_list, total_mbid_count = _process_recommendations(recommendations, count, user_name, offset)

    payload = {
        'payload': {
            'model_id': recommendations.recording_mbid.model_id,
            'model_url': recommendations.recording_mbid.model_url,
            'mbids': mbid_list,
            'entity': "recording",
            'user_name': user_name,
            'last_updated': int(recommendations.created.timestamp()),
            'count': len(mbid_list),
            'total_mbid_count': total_mbid_count,
            'offset': offset
        }
    }

    return jsonify(payload)


def _process_recommendations(recommendations, count, user_name, offset):
    """ Process recommendations based on artist type.

        Args:
            recommendations: dict containing user recommendations.
            count (int): number of recommended recording mbids to return.
            user_name (str): musicbrainz id of the user.
            offset (int): number of entities to skip from the beginning

        Returns:
            - total_mbid_count (int): Total number of recommended mbids in the db for the user.
            - list of recommended mbids based on count and offset.

        Raises:
            APINoContent: if recommendations not found.
    """
    data = recommendations.recording_mbid.dict()
    mbid_list = data['raw']

    total_mbid_count = len(mbid_list)

    if total_mbid_count == 0:
        err_msg = f'No recommendations for user {user_name}, please try again later.'
        raise APINoContent(err_msg, payload={'last_updated': int(recommendations.created.timestamp())})

    # For the purpose of experimenting with recommendations, we're allowing to fetch at most
    # 1K recommendations.
    count = min(count, 1000)

    return mbid_list[offset:offset+count], total_mbid_count
