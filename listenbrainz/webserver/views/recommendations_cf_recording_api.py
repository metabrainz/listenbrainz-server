import listenbrainz.db.user as db_user
import listenbrainz.db.recommendations_cf_recording as db_recommendations_cf_recording

from listenbrainz.webserver.errors import APIBadRequest, APINotFound, APINoContent

from enum import Enum

from flask import Blueprint, jsonify, request
from listenbrainz.webserver.decorators import crossdomain
from listenbrainz.webserver.rate_limiter import ratelimit

recommendations_cf_recording_api_bp = Blueprint('recommendations_cf_recording_v1', __name__)


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

    recommendations = db_recommendations_cf_recording.get_user_recommendation(user['id'])

    if recommendations is None:
        err_msg = 'No recommendations due to absence of recent listening history for user {}'.format(user_name)
        raise APINoContent(err_msg)

    if artist_type == 'top':
        payload = _format_top_artist_recommendations(recommendations, user_name)

    if artist_type == 'similar':
        payload = _format_similar_artist_recommendations(recommendations, user_name)

    return jsonify(payload)


def _format_top_artist_recommendations(recommendations, user_name):
    """ Format top artist recommendations payload.

        Returns:
            payload = {
                'payload': {
                    'top_artist': {
                        'recording_mbid': ["526bd613-fddd-4bd6-9137-ab709ac74cab"]
                    },
                    'user_name': 'vansika,
                    'last_updated': 1588494361,
                }
            }
        Raises:
            APINoContent: if top artist recommendations not found.
    """
    top_artist_recommendations = recommendations['recording_mbid']['top_artist']
    last_updated = int(recommendations['created'].timestamp())

    if len(top_artist_recommendations) == 0:
        err_msg = 'No top artist recommendations for user {}, please try again later.'.format(user_name)
        raise APINoContent(err_msg, payload={'last_updated': last_updated})

    payload = {
        'payload': {
            'top_artist': {
                'recording_mbid': top_artist_recommendations
            },
            'user_name': user_name,
            'last_updated': last_updated,
        }
    }

    return payload


def _format_similar_artist_recommendations(recommendations, user_name):
    """ Format similar artist recommendations payload.

        Returns:
            payload = {
                'payload': {
                    'similar_artist': {
                        'recording_mbid': ["526bd613-fddd-4bd6-9137-ab709ac74cab"]
                    },
                    'user_name': 'vansika,
                    'last_updated': 1588494361,
                }
            }
        Raises:
            APINoContent: if similar artist recommendations not found.
    """
    similar_artist_recommendations = recommendations['recording_mbid']['similar_artist']
    last_updated = int(recommendations['created'].timestamp())

    if len(similar_artist_recommendations) == 0:
        err_msg = 'No similar artist recommendations for user {}, please try again later.'.format(user_name)
        raise APINoContent(err_msg, payload={'last_updated': last_updated})

    payload = {
        'payload': {
            'similar_artist': {
                'recording_mbid': similar_artist_recommendations
            },
            'user_name': user_name,
            'last_updated': last_updated,
        }
    }

    return payload


def _is_valid_artist_type(artist_type):
    """ Check if artist type is valid.
    """
    if artist_type is None:
        raise APIBadRequest('Please provide artist type')

    RecommendationArtistType = Enum('RecommendationArtistType', 'top similar')
    return artist_type in RecommendationArtistType.__members__
