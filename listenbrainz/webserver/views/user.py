from datetime import datetime

import listenbrainz.db.user as db_user
import listenbrainz.db.user_relationship as db_user_relationship

from flask import Blueprint, render_template, request, url_for, jsonify, current_app
from flask_login import current_user, login_required

from listenbrainz import webserver
from listenbrainz.db.msid_mbid_mapping import fetch_track_metadata_for_items
from listenbrainz.db.playlist import get_playlists_for_user, get_recommendation_playlists_for_user
from listenbrainz.db.pinned_recording import get_current_pin_for_user, get_pin_count_for_user, get_pin_history_for_user
from listenbrainz.db.feedback import get_feedback_count_for_user, get_feedback_for_user
from listenbrainz.db import year_in_music as db_year_in_music
from listenbrainz.webserver.decorators import web_listenstore_needed
from listenbrainz.webserver import timescale_connection, db_conn, ts_conn
from listenbrainz.webserver.errors import APIBadRequest
from listenbrainz.webserver.login import User, api_login_required
from listenbrainz.webserver.views.api import DEFAULT_NUMBER_OF_PLAYLISTS_PER_CALL
from werkzeug.exceptions import NotFound

LISTENS_PER_PAGE = 25
DEFAULT_NUMBER_OF_FEEDBACK_ITEMS_PER_CALL = 25

user_bp = Blueprint("user", __name__)
redirect_bp = Blueprint("redirect", __name__)


@redirect_bp.route('/', defaults={'path': ''})
@redirect_bp.route('/<path:path>/')
@login_required
def index(path):
    return render_template("index.html", user=current_user)


@user_bp.route("/<user_name>/", methods=['POST'])
@web_listenstore_needed
def profile(user_name):
    # Which database to use to showing user listens.
    ts_conn = webserver.timescale_connection._ts
    # Which database to use to show playing_now stream.
    playing_now_conn = webserver.redis_connection._redis

    user = _get_user(user_name)
    if not user:
        return jsonify({"error": "Cannot find user: %s" % user_name}), 404

    # User name used to get user may not have the same case as original user name.
    user_name = user.musicbrainz_id

    # Getting data for current page
    max_ts = request.args.get("max_ts")
    if max_ts is not None:
        try:
            max_ts = int(max_ts)
        except ValueError:
            return jsonify({"error": "Incorrect timestamp argument max_ts: %s" %
                            request.args.get("max_ts")}), 400

    min_ts = request.args.get("min_ts")
    if min_ts is not None:
        try:
            min_ts = int(min_ts)
        except ValueError:
            return jsonify({"error": "Incorrect timestamp argument min_ts: %s" %
                            request.args.get("min_ts")}), 400

    args = {}
    if max_ts:
        args['to_ts'] = datetime.utcfromtimestamp(max_ts)
    elif min_ts:
        args['from_ts'] = datetime.utcfromtimestamp(min_ts)
    data, min_ts_per_user, max_ts_per_user = ts_conn.fetch_listens(
        user.to_dict(), limit=LISTENS_PER_PAGE, **args)
    min_ts_per_user = int(min_ts_per_user.timestamp())
    max_ts_per_user = int(max_ts_per_user.timestamp())

    listens = []
    for listen in data:
        listens.append(listen.to_api())

    playing_now = playing_now_conn.get_playing_now(user.id)
    if playing_now:
        playing_now = playing_now.to_api()

    already_reported_user = False
    if current_user.is_authenticated:
        already_reported_user = db_user.is_user_reported(db_conn, current_user.id, user.id)

    pin = get_current_pin_for_user(db_conn, user_id=user.id)
    if pin:
        pin = fetch_track_metadata_for_items(webserver.ts_conn, [pin])[0].to_api()

    data = {
        "user": {
            "id": user.id,
            "name": user.musicbrainz_id,
        },
        "listens": listens,
        "latestListenTs": max_ts_per_user,
        "oldestListenTs": min_ts_per_user,
        "profile_url": url_for('user.index', path="", user_name=user_name),
        "userPinnedRecording": pin,
        "playingNow": playing_now,
        "logged_in_user_follows_user": logged_in_user_follows_user(user),
        "already_reported_user": already_reported_user,
    }

    return jsonify(data)


@user_bp.route("/<user_name>/stats/top-artists/", methods=['POST'])
@user_bp.route("/<user_name>/stats/top-albums/", methods=['POST'])
@user_bp.route("/<user_name>/stats/top-tracks/", methods=['POST'])
def charts(user_name):
    """ Show the top entitys for the user. """
    user = _get_user(user_name)
    if not user:
        return jsonify({"error": "Cannot find user: %s" % user_name}), 404

    user_data = {
        "name": user.musicbrainz_id,
        "id": user.id,
    }

    props = {
        "user": user_data,
        "logged_in_user_follows_user": logged_in_user_follows_user(user),
    }

    return jsonify(props)


@user_bp.route("/<user_name>/stats/", methods=['POST'])
def stats(user_name: str):
    """ Show user stats """
    user = _get_user(user_name)
    if not user:
        return jsonify({"error": "Cannot find user: %s" % user_name}), 404

    user_data = {
        "name": user.musicbrainz_id,
        "id": user.id,
    }

    data = {
        "user": user_data,
        "logged_in_user_follows_user": logged_in_user_follows_user(user),
    }

    return jsonify(data)


@user_bp.route("/<user_name>/playlists/", methods=['POST'])
@web_listenstore_needed
def playlists(user_name: str):
    """ Show user playlists """

    user = _get_user(user_name)
    if not user:
        return jsonify({"error": "Cannot find user: %s" % user_name}), 404

    user_data = {
        "name": user.musicbrainz_id,
        "id": user.id,
    }

    include_private = current_user.is_authenticated and current_user.id == user.id

    playlists = []
    user_playlists, playlist_count = get_playlists_for_user(
        db_conn, ts_conn, user.id, include_private=include_private,
        load_recordings=False, count=DEFAULT_NUMBER_OF_PLAYLISTS_PER_CALL, offset=0
    )
    for playlist in user_playlists:
        playlists.append(playlist.serialize_jspf())

    data = {
        "playlists": playlists,
        "user": user_data,
        "playlistCount": playlist_count,
        "logged_in_user_follows_user": logged_in_user_follows_user(user),
    }

    return jsonify(data)


@user_bp.route("/<user_name>/recommendations/", methods=['POST'])
@web_listenstore_needed
def recommendation_playlists(user_name: str):
    """ Show playlists created for user """

    offset = request.args.get('offset', 0)
    try:
        offset = int(offset)
    except ValueError:
        return jsonify({"error": "Incorrect int argument offset: %s" %
                        request.args.get("offset")}), 400

    count = request.args.get("count", DEFAULT_NUMBER_OF_PLAYLISTS_PER_CALL)
    try:
        count = int(count)
    except ValueError:
        return jsonify({"error": "Incorrect int argument count: %s" %
                        request.args.get("count")}), 400
    user = _get_user(user_name)
    if not user:
        return jsonify({"error": "Cannot find user: %s" % user_name}), 404

    user_data = {
        "name": user.musicbrainz_id,
        "id": user.id,
    }

    playlists = []
    user_playlists = get_recommendation_playlists_for_user(db_conn, ts_conn, user.id)
    for playlist in user_playlists:
        playlists.append(playlist.serialize_jspf())

    data = {
        "playlists": playlists,
        "user": user_data,
        "logged_in_user_follows_user": logged_in_user_follows_user(user),
    }

    return jsonify(data)


@user_bp.route("/<user_name>/report-user/", methods=['POST'])
@api_login_required
def report_abuse(user_name):
    data = request.json
    reason = None
    if data:
        reason = data.get("reason")
        if not isinstance(reason, str):
            raise APIBadRequest("Reason must be a string.")
    user_to_report = db_user.get_by_mb_id(db_conn, user_name)
    if current_user.id != user_to_report["id"]:
        db_user.report_user(db_conn, current_user.id, user_to_report["id"], reason)
        return jsonify({"status": "%s has been reported successfully." % user_name})
    else:
        raise APIBadRequest("You cannot report yourself.")


def _get_user(user_name):
    """ Get current username """
    if current_user.is_authenticated and \
            current_user.musicbrainz_id == user_name:
        return current_user
    else:
        user = db_user.get_by_mb_id(db_conn, user_name)
        if user is None:
            return None
        return User.from_dbrow(user)


def logged_in_user_follows_user(user):
    """ Check if user is being followed by the current user.
    Args:
        user : User object
    Raises:
        NotFound if user isn't present in the database
    """

    if current_user.is_authenticated:
        return db_user_relationship.is_following_user(
            db_conn, current_user.id, user.id
        )
    return None


@user_bp.route("/<user_name>/taste/", methods=['POST'])
@web_listenstore_needed
def taste(user_name: str):
    """ Show user feedback(love/hate) and pins.
    Feedback has filter on score (1 or -1).

    Args:
        user_name (str): the MusicBrainz ID of the user
    Raises:
        NotFound if user isn't present in the database
    """

    score = request.args.get('score', 1)
    try:
        score = int(score)
    except ValueError:
        return jsonify({"error": "Incorrect int argument score: %s" %
                        request.args.get("score")}), 400

    user = _get_user(user_name)
    if not user:
        return jsonify({"error": "Cannot find user: %s" % user_name}), 404

    user_data = {
        "name": user.musicbrainz_id,
        "id": user.id,
    }

    feedback_count = get_feedback_count_for_user(db_conn, user.id, score)
    feedback = get_feedback_for_user(
        db_conn, ts_conn, user_id=user.id, limit=DEFAULT_NUMBER_OF_FEEDBACK_ITEMS_PER_CALL,
        offset=0, score=score, metadata=True
    )
    
    pins = get_pin_history_for_user(db_conn, user_id=user.id, count=25, offset=0)
    pins = [pin.to_api() for pin in fetch_track_metadata_for_items(ts_conn, pins)]
    pin_count = get_pin_count_for_user(db_conn, user_id=user.id)

    data = {
        "feedback": [f.to_api() for f in feedback],
        "feedback_count": feedback_count,
        "user": user_data,
        "active_section": "taste",
        "logged_in_user_follows_user": logged_in_user_follows_user(user),
        "pins": pins,
        "pin_count": pin_count,
        "profile_url": url_for('user.index', path="", user_name=user_name),
    }

    return jsonify(data)


@user_bp.route("/<user_name>/year-in-music/", methods=['POST'])
@user_bp.route("/<user_name>/year-in-music/<int:year>/", methods=['POST'])
def year_in_music(user_name, year: int = 2023):
    """ Year in Music """
    if year != 2021 and year != 2022 and year != 2023:
        return jsonify({"error": f"Cannot find Year in Music report for year: {year}"}), 404

    user = _get_user(user_name)
    if not user:
        return jsonify({"error": "Cannot find user: %s" % user_name}), 404

    try:
        yearInMusicData = db_year_in_music.get(user.id, year) or {}
    except Exception as e:
        yearInMusicData = {}
        current_app.logger.error(f"Error getting Year in Music data for user {user_name}: {e}")

    return jsonify({
        "data": yearInMusicData,
        "user": {
            "id": user.id,
            "name": user.musicbrainz_id,
        },
    })

# Embedable widgets, return HTML page to embed in an iframe


@user_bp.route("/<user_name>/embed/playing-now", methods=['GET'])
def embed_playing_now(user_name):
    # Which database to use to show playing_now stream.
    playing_now_conn = webserver.redis_connection._redis

    user = _get_user(user_name)
    if not user:
        return jsonify({"error": "Cannot find user: %s" % user_name}), 404

    # User name used to get user may not have the same case as original user name.
    user_name = user.musicbrainz_id

    playing_now = playing_now_conn.get_playing_now(user.id)
    if playing_now:
        playing_now = playing_now.to_api()

    return render_template("widgets/playing_now.html", user_name=user_name, playing_now=playing_now)

# Embedable widgets, return HTML page to embed in an iframe


@user_bp.route("/<user_name>/embed/pin", methods=['GET'])
def embed_pin(user_name):
    # Which database to use to show playing_now stream.

    user = _get_user(user_name)
    if not user:
        return jsonify({"error": "Cannot find user: %s" % user_name}), 404

    # User name used to get user may not have the same case as original user name.
    user_name = user.musicbrainz_id

    pin = get_current_pin_for_user(db_conn, user_id=user.id)
    if pin:
        pin = fetch_track_metadata_for_items(
            webserver.ts_conn, [pin])[0].to_api()

    return render_template("widgets/pin.html", user_name=user_name, pinned_recording=pin)


@user_bp.route("/<user_name>/",  defaults={'path': ''})
@user_bp.route('/<user_name>/<path:path>/')
@web_listenstore_needed
def index(user_name, path):
    user = _get_user(user_name)
    return render_template("index.html", user=user)
