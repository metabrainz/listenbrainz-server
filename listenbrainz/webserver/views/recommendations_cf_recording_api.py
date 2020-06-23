import listenbrainz.db.user as db_user
import listenbrainz.db.recommendations_cf_recording as db_recommendations_cf_recording

from listenbrainz.webserver.errors import APIBadRequest, APINotFound

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

            "last_updated": "Sat, 06 Jun 2020 08:18:50 GMT",

            "<artist_type>": {

              "recording_mbids": [
                "526bd613-fddd-4bd6-9137-ab709ac74cab",
                "a6081bc1-2a76-4984-b21f-38bc3dcca3a5",
                "a6ad0205-6e96-416d-a4e8-edd1773dac09",
                "d8783d03-8a3b-4269-8261-00709d2cfee8"
              ]
            },

            "user_name": "unclejohn69"
          }
        }

        <artist_type>: 'top' or 'similar'

        :statuscode 200: Successful query, you have data!
        :statuscode 400: Bad request, check ``response['error']`` for more details
        :statuscode 404: User not found or recommendations not generated
    """
    user = db_user.get_by_mb_id(user_name)
    if user is None:
        raise APINotFound("Cannot find user: {}".format(user_name))

    artist_type = request.args.get('type')
    if not _is_valid_artist(artist_type):
        raise APIBadRequest("Invalid artist type: {}".format(artist_type))

    recommendations = db_recommendations_cf_recording.get_user_recommendation(user['id'])

    if recommendations is None:
        err_msg = 'Oops! Looks like {} doesn\'t have recent listening history.' \
                  ' Recommendations not generated :('.format(user_name)
        raise APINotFound(err_msg)

    if artist_type == 'top':
        try:
            payload = _get_top_artist_recommendations(recommendations, user_name)
        except TopArtistRecommendationsNotFound:
            err_msg = 'Oops! Looks like there was some Spark issue while generating top artist' \
                      ' recommendations for {}. We are working on it. Please check back later!!'.format(user_name)
            raise APINotFound(err_msg, payload={'last_updated': recommendations['created']})

    if artist_type == 'similar':
        try:
            payload = _get_similar_artist_recommendations(recommendations, user_name)
        except SimilarArtistRecommendationsNotFound:
            err_msg = 'Oops! Looks like there was some Spark issue while generating similar artist' \
                      ' recommendations for {}. We are working on it. Please check back later!!'.format(user_name)
            raise APINotFound(err_msg, payload={'last_updated': recommendations['created']})

    return jsonify(payload)


def _get_top_artist_recommendations(recommendations, user_name):
    """ Get top artist recommended recording mbids.

        if recommendations not found raises TopArtistRecommendationsNotFound exception.
    """
    top_artist_recommendations = recommendations['recording_mbid']['top_artist']

    if len(top_artist_recommendations) == 0:
        raise TopArtistRecommendationsNotFound()

    payload = {'payload': {
        'top-artist': {
            'recording_mbids': top_artist_recommendations
        },
        'user_name': user_name,
        'last_updated': recommendations['created'],
    }}

    return payload


def _get_similar_artist_recommendations(recommendations, user_name):
    """ Get similar artist recommended recording mbids.

        if recommendations not found raises SimilarArtistRecommendationsNotFound exception.
    """
    similar_artist_recommendations = recommendations['recording_mbid']['similar_artist']

    if len(similar_artist_recommendations) == 0:
        raise SimilarArtistRecommendationsNotFound()

    payload = {'payload': {
        'similar-artist': {
            'recording_mbids': similar_artist_recommendations
        },
        'user_name': user_name,
        'last_updated': recommendations['created'],
    }}

    return payload


def _is_valid_artist(artist_type):
    """ Check if artist type is valid.
    """
    if artist_type not in ['top', 'similar']:
        return False
    return True


class TopArtistRecommendationsNotFound(Exception):
    pass


class SimilarArtistRecommendationsNotFound(Exception):
    pass
