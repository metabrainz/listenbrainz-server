import orjson
from flask import Blueprint, render_template, current_app
from psycopg2.extras import DictCursor

import listenbrainz.db.recommendations_cf_recording as db_recommendations_cf_recording
from listenbrainz.db import timescale
from listenbrainz.db.msid_mbid_mapping import load_recordings_from_mbids
from listenbrainz.webserver.views.user import _get_user

recommendations_cf_recording_bp = Blueprint('recommendations_cf_recording', __name__)

SERVER_URL = "https://labs.api.listenbrainz.org/recording-mbid-lookup/json"


@recommendations_cf_recording_bp.route("/<user_name>/")
def info(user_name):
    """ Show info about the recommended tracks
    """

    user = _get_user(user_name)

    return render_template(
        "recommendations_cf_recording/info.html",
        user=user,
        active_section='info'
    )


@recommendations_cf_recording_bp.route("/<user_name>/top_artist/")
def top_artist(user_name: str):
    """ Show top artist user recommendations """
    user = _get_user(user_name)

    template = _get_template(active_section='top_artist', user=user)

    return template


@recommendations_cf_recording_bp.route("/<user_name>/similar_artist/")
def similar_artist(user_name: str):
    """ Show similar artist user recommendations """
    user = _get_user(user_name)

    template = _get_template(active_section='similar_artist', user=user)

    return template


@recommendations_cf_recording_bp.route("/<user_name>/raw/")
def raw(user_name: str):
    """ Show raw track recommendations """
    user = _get_user(user_name)

    template = _get_template(active_section='raw', user=user)

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
        "recommendations": recommendations,
    }

    return render_template(
        "recommendations_cf_recording/base.html",
        active_section=active_section,
        tracks_type=tracks_type,
        props=orjson.dumps(props).decode("utf-8"),
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
                            'artist_mbids' : "181c4177-f33a-441d-b15d-910acaf18b07",
                            'caa_id' : 34021497287,
                            'caa_release_mbid' : "a2225115-891b-4f6b-a795-f2b7a68d0bcb"
                            'release_mbid' : "a2225115-891b-4f6b-a795-f2b7a68d0bcb"
                        }
                    }
                }
    """
    mbids = [r['recording_mbid'] for r in mbids_and_ratings_list]
    with timescale.engine.connect() as ts_conn, ts_conn.connection.cursor(cursor_factory=DictCursor) as ts_cursor:
        data = load_recordings_from_mbids(ts_cursor, mbids)

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
                    'artist_mbids': row['artist_mbids'],
                    'release_mbid' : row['release_mbid'],
                    'caa_id' : row['caa_id'],
                    'caa_release_mbid' : row['caa_release_mbid']
                }
            }
        })

    return recommendations
