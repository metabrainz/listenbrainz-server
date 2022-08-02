import ujson
from flask import Blueprint, render_template, current_app

import listenbrainz.db.recommendations_cf_recording as db_recommendations_cf_recording
from listenbrainz import db
from listenbrainz.db import timescale
from listenbrainz.db.msid_mbid_mapping import load_recordings_from_mapping
from listenbrainz.webserver.views.user import _get_user

recommendations_cf_recording_bp = Blueprint('recommendations_cf_recording', __name__)

SERVER_URL = "https://labs.api.listenbrainz.org/recording-mbid-lookup/json"


@recommendations_cf_recording_bp.route("/<user_name>/")
def info(user_name):
    """ Show info about the recommended tracks
    """
    with db.engine.connect() as conn:
        user = _get_user(conn, user_name)

    return render_template(
        "recommendations_cf_recording/info.html",
        user=user,
        active_section='info'
    )


@recommendations_cf_recording_bp.route("/<user_name>/top_artist/")
def top_artist(user_name: str):
    """ Show top artist user recommendations """
    return _get_template('top_artist', user_name)


@recommendations_cf_recording_bp.route("/<user_name>/similar_artist/")
def similar_artist(user_name: str):
    """ Show similar artist user recommendations """
    return _get_template('similar_artist', user_name)


@recommendations_cf_recording_bp.route("/<user_name>/raw/")
def raw(user_name: str):
    """ Show raw track recommendations """
    return _get_template('raw', user_name)


def _get_template(active_section, user_name):
    """ Get template to render based on active section.

        Args:
            active_section (str): Type of recommendation playlist to render i.e top_artist, similar_artist
            user_name: musicbrainz id of the user.

        Returns:
            Template to render.
    """
    with db.engine.connect() as conn:
        user = _get_user(conn, user_name)
        data = db_recommendations_cf_recording.get_user_recommendation(conn, user.id)

    if active_section == 'top_artist':
        tracks_type = "Top Artist"
    elif active_section == 'similar_artist':
        tracks_type = "Similar Artist"
    else:
        tracks_type = "Raw Tracks"

    if data is None:
        return render_template(
            "recommendations_cf_recording/base.html",
            active_section=active_section,
            tracks_type=tracks_type,
            user=user,
            error_msg="Looks like the user wasn't active in the last week. Submit your listens and check back after a week!"
        )

    result = data.recording_mbid.dict()[active_section]

    if not result:
        current_app.logger.error('Top/Similar artists/raw not found in Mapping/artist relation for "{}"'.format(user.musicbrainz_id))
        return render_template(
            "recommendations_cf_recording/base.html",
            active_section=active_section,
            tracks_type=tracks_type,
            user=user,
            error_msg="Looks like the recommendations weren't generated because of anomalies in our data." \
                      "We are working on it. Check back later."
        )

    recommendations = _get_playable_recommendations_list(result)
    if not recommendations:
        current_app.logger.error('The API returned an empty response for {} recommendations.\nData: {}'
                                 .format(active_section, result))
        return render_template(
            "recommendations_cf_recording/base.html",
            active_section=active_section,
            tracks_type=tracks_type,
            user=user,
            error_msg="An error occurred while processing your request. Check back later!"
        )

    props = {
        "user": {
            "id": user.id,
            "name": user.musicbrainz_id,
        },
        "web_sockets_server_url": current_app.config['WEBSOCKETS_SERVER_URL'],
        "recommendations": recommendations,
    }

    return render_template(
        "recommendations_cf_recording/base.html",
        active_section=active_section,
        tracks_type=tracks_type,
        props=ujson.dumps(props),
        user=user,
        last_updated=data.created.strftime('%d %b %Y')
    )


def _get_playable_recommendations_list(mbids_and_ratings_list):
    """ Get artist, track etc info from recording mbid using labs.listenbrainz.api
        so that they can be played using BrainzPlayer. Refer to webserver/static/js/src/BrainzPlayer.tsx

        Args:
            mbids_and_ratings_list: Contains recording mbid and corresponding score.

        Returns:
            recommendations: list of recommendations of the format
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
                    }
                }
    """
    mbids = [r['recording_mbid'] for r in mbids_and_ratings_list]
    with timescale.engine.connect() as ts_conn:
        data, _ = load_recordings_from_mapping(ts_conn, mbids=mbids, msids=[])

    recommendations = []

    for recommendation in mbids_and_ratings_list:
        mbid = recommendation['recording_mbid']
        if mbid not in data:
            continue
        row = data[mbid]
        recommendations.append({
            'listened_at_iso': recommendation['latest_listened_at'],
            'track_metadata': {
                'artist_name': row['artist'],
                'track_name': row['title'],
                'release_name': row['release'],
                'additional_info': {
                    'recording_mbid': row['recording_mbid'],
                    'artist_mbids': row['artist_mbids']
                }
            }
        })

    return recommendations
