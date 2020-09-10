import ujson
import requests
from datetime import datetime

from flask import Blueprint, render_template, current_app
from flask_login import current_user, login_required
from listenbrainz.domain import spotify

from listenbrainz.webserver.views.user import _get_user
import listenbrainz.db.recommendations_cf_recording as db_recommendations_cf_recording


recommendations_cf_recording_bp = Blueprint('recommendations_cf_recording', __name__)

SERVER_URL = "https://labs.api.listenbrainz.org/recording-mbid-lookup/json"


@recommendations_cf_recording_bp.route("/<user_name>")
def info(user_name):
    """ Show info about the recommended tracks
    """

    user = _get_user(user_name)

    return render_template(
        "recommendations_cf_recording/info.html",
        user=user,
        active_section='info'
    )


@recommendations_cf_recording_bp.route("/<user_name>/top_artist")
def top_artist(user_name: str):
    """ Show top artist user recommendations """
    user = _get_user(user_name)

    template = _get_template(active_section='top_artist', user=user)

    return template


@recommendations_cf_recording_bp.route("/<user_name>/similar_artist")
def similar_artist(user_name: str):
    """ Show similar artist user recommendations """
    user = _get_user(user_name)

    template = _get_template(active_section='similar_artist', user=user)

    return template


def _get_template(active_section, user):
    """ Get template to render based on active section.

        Args:
            active_section (str): Type of recommendation playlist to render i.e top_artist, similar_artist
            user: Database user object.

        Returns:
            Template to render.
    """

    data = db_recommendations_cf_recording.get_user_recommendation(user.id)

    if data is None:
        return render_template(
            "recommendations_cf_recording/{}.html".format(active_section),
            active_section=active_section,
            user=user,
            error_msg="Recommended tracks for the user have not been calculated. Check back later."
        )

    result = data['recording_mbid'][active_section]

    if not result:
        return render_template(
            "recommendations_cf_recording/{}.html".format(active_section),
            active_section=active_section,
            user=user,
            error_msg="Looks like you weren't active last week. Check back later."
        )

    listens = _get_listens_from_recording_mbid(result)

    spotify_data = spotify.get_user_dict(current_user.id)

    current_user_data = {
            "id": current_user.id,
            "name": current_user.musicbrainz_id,
            "auth_token": current_user.auth_token,
    }

    props = {
        "user": {
            "id": user.id,
            "name": user.musicbrainz_id,
        },
        "current_user": current_user_data,
        "spotify": spotify_data,
        "api_url": current_app.config["API_URL"],
        "web_sockets_server_url": current_app.config['WEBSOCKETS_SERVER_URL'],
        "listens": listens,
        "mode": "cf_recs"
    }

    return render_template(
        "recommendations_cf_recording/{}.html".format(active_section),
        active_section=active_section,
        props=ujson.dumps(props),
        user=user,
        last_updated=data['created'].strftime('%d %b %Y')
    )


def _get_listens_from_recording_mbid(mbids_and_ratings_list):
    """ Get listens from recording mbid using labs.listenbrainz.api.

        Args:
            mbids_and_ratings_list: Contains recording mbid and corresponding score.

        Returns:
            listens: list of listens of the format
                {
                    'listened_at' : 0,
                    'track_metadata' : {
                        'artist_name' : 'John Mayer',
                        'track_name' : 'Edge of desire',
                        'release_name' : "",
                        'additional_info' : {
                            'recording_mbid' : "181c4177-f33a-441d-b15d-910acaf18b07",
                            'artist_mbids' : "181c4177-f33a-441d-b15d-910acaf18b07"
                        }
                    },
                    'score': 0.123
                }

    """
    data = []
    mbids_and_ratings = {}

    for r in mbids_and_ratings_list:
        data.append({ 'recording_mbid': r[0] })
        # get score corresponding to recording mbid.
        mbids_and_ratings[r[0]] = r[1]

    r = requests.post(SERVER_URL, json=data)
    if r.status_code != 200:
        r.raise_for_status()

    try:
        rows = ujson.loads(r.text)
    except Exception as err:
        raise RuntimeError(str(err))

    listens = []

    for row in rows:
        listens.append({
            'listened_at' : 0,
            'track_metadata' : {
                'artist_name' : row['artist_credit_name'],
                'track_name' : row['recording_name'],
                'release_name' : row.get('release_name', ""),
                'additional_info' : {
                    'recording_mbid' : row['recording_mbid'],
                    'artist_mbids' : row['[artist_credit_mbids]']
                }
            },
            'score': mbids_and_ratings[row['recording_mbid']]
        })

    listens = sorted(listens, key=lambda x: x['score'], reverse=True)

    return listens
