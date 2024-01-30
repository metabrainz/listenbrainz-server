from datetime import datetime

import listenbrainz.db.user as db_user
import listenbrainz.db.user_relationship as db_user_relationship

from flask import Blueprint, render_template, request, url_for, redirect, jsonify
from flask_login import current_user, login_required

from data.model.external_service import ExternalServiceType
from listenbrainz import webserver
from listenbrainz.db import listens_importer
from listenbrainz.db.msid_mbid_mapping import fetch_track_metadata_for_items
from listenbrainz.db.playlist import get_playlists_for_user, get_recommendation_playlists_for_user
from listenbrainz.db.pinned_recording import get_current_pin_for_user, get_pin_count_for_user, get_pin_history_for_user
from listenbrainz.db.feedback import get_feedback_count_for_user, get_feedback_for_user
from listenbrainz.db import year_in_music as db_year_in_music
from listenbrainz.webserver.decorators import web_listenstore_needed
from listenbrainz.webserver import timescale_connection
from listenbrainz.webserver.errors import APIBadRequest
from listenbrainz.webserver.login import User, api_login_required
from listenbrainz.webserver import timescale_connection
from listenbrainz.webserver.views.api import DEFAULT_NUMBER_OF_PLAYLISTS_PER_CALL
from werkzeug.exceptions import NotFound, BadRequest

LISTENS_PER_PAGE = 25
DEFAULT_NUMBER_OF_FEEDBACK_ITEMS_PER_CALL = 25

user_bp = Blueprint("user", __name__)
redirect_bp = Blueprint("redirect", __name__)


@redirect_bp.route('/', defaults={'path': ''})
@redirect_bp.route('/<path:path>/')
@login_required
def index(path):
    return render_template("user/index.html", user=current_user)


@user_bp.route("/<user_name>/", methods=['POST'])
@web_listenstore_needed
def profile(user_name):
    # Which database to use to showing user listens.
    db_conn = webserver.timescale_connection._ts
    # Which database to use to show playing_now stream.
    playing_now_conn = webserver.redis_connection._redis

    user = _get_user(user_name)
    # User name used to get user may not have the same case as original user name.
    user_name = user.musicbrainz_id

    # Getting data for current page
    max_ts = request.args.get("max_ts")
    if max_ts is not None:
        try:
            max_ts = int(max_ts)
        except ValueError:
            raise BadRequest("Incorrect timestamp argument max_ts: %s" %
                             request.args.get("max_ts"))

    min_ts = request.args.get("min_ts")
    if min_ts is not None:
        try:
            min_ts = int(min_ts)
        except ValueError:
            raise BadRequest("Incorrect timestamp argument min_ts: %s" %
                             request.args.get("min_ts"))

    args = {}
    if max_ts:
        args['to_ts'] = datetime.utcfromtimestamp(max_ts)
    elif min_ts:
        args['from_ts'] =  datetime.utcfromtimestamp(min_ts)
    data, min_ts_per_user, max_ts_per_user = db_conn.fetch_listens(
        user.to_dict(), limit=LISTENS_PER_PAGE, **args)
    min_ts_per_user = int(min_ts_per_user.timestamp())
    max_ts_per_user = int(max_ts_per_user.timestamp())

    listens = []
    for listen in data:
        listens.append(listen.to_api())

    # If there are no previous listens then display now_playing
    if not listens or listens[0]['listened_at'] >= max_ts_per_user:
        playing_now = playing_now_conn.get_playing_now(user.id)
        if playing_now:
            listens.insert(0, playing_now.to_api())

    already_reported_user = False
    if current_user.is_authenticated:
        already_reported_user = db_user.is_user_reported(current_user.id, user.id)

    pin = get_current_pin_for_user(user_id=user.id)
    if pin:
        pin = fetch_track_metadata_for_items([pin])[0].to_api()

    data = {
        "user": {
            "id": user.id,
            "name": user.musicbrainz_id,
        },
        "listens": listens,
        "latest_listen_ts": max_ts_per_user,
        "oldest_listen_ts": min_ts_per_user,
        "profile_url": url_for('user.profile', user_name=user_name),
        "userPinnedRecording": pin,
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

    user_data = {
        "name": user.musicbrainz_id,
        "id": user.id,
    }

    props = {
        "user": user_data,
        "logged_in_user_follows_user": logged_in_user_follows_user(user),
    }

    return jsonify(props)


@user_bp.route("/<user_name>/reports/", methods=['POST'])
def reports(user_name):
    """ Redirect to stats page """
    return redirect(url_for('user.stats', user_name=user_name), code=301)


@user_bp.route("/<user_name>/stats/", methods=['POST'])
def stats(user_name: str):
    """ Show user stats """
    user = _get_user(user_name)

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
    user_data = {
        "name": user.musicbrainz_id,
        "id": user.id,
    }

    include_private = current_user.is_authenticated and current_user.id == user.id

    playlists = []
    user_playlists, playlist_count = get_playlists_for_user(user.id,
                                                            include_private=include_private,
                                                            load_recordings=False,
                                                            count=DEFAULT_NUMBER_OF_PLAYLISTS_PER_CALL,
                                                            offset=0)
    for playlist in user_playlists:
        playlists.append(playlist.serialize_jspf())

    data = {
        "playlists": playlists,
        "user": user_data,
        "active_section": "playlists",
        "playlist_count": playlist_count,
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
        raise BadRequest("Incorrect int argument offset: %s" %
                         request.args.get("offset"))

    count = request.args.get("count", DEFAULT_NUMBER_OF_PLAYLISTS_PER_CALL)
    try:
        count = int(count)
    except ValueError:
        raise BadRequest("Incorrect int argument count: %s" %
                         request.args.get("count"))
    user = _get_user(user_name)
    user_data = {
        "name": user.musicbrainz_id,
        "id": user.id,
    }

    playlists = []
    user_playlists = get_recommendation_playlists_for_user(
        user.id)
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
    user_to_report = db_user.get_by_mb_id(user_name)
    if current_user.id != user_to_report["id"]:
        db_user.report_user(current_user.id, user_to_report["id"], reason)
        return jsonify({"status": "%s has been reported successfully." % user_name})
    else:
        raise APIBadRequest("You cannot report yourself.")


def _get_user(user_name):
    """ Get current username """
    if current_user.is_authenticated and \
            current_user.musicbrainz_id == user_name:
        return current_user
    else:
        user = db_user.get_by_mb_id(user_name)
        if user is None:
            raise NotFound("Cannot find user: %s" % user_name)
        return User.from_dbrow(user)


def delete_user(user_id: int):
    """ Delete a user from ListenBrainz completely. First, drops
     the user's listens and then deletes the user from the database.

    Args:
        user_id: the LB row ID of the user
    """
    timescale_connection._ts.delete(user_id)
    db_user.delete(user_id)


def delete_listens_history(user_id: int):
    """ Delete a user's listens from ListenBrainz completely.

    Args:
        user_id: the LB row ID of the user
    """
    timescale_connection._ts.delete(user_id)
    listens_importer.update_latest_listened_at(user_id, ExternalServiceType.LASTFM, 0)


def logged_in_user_follows_user(user):
    """ Check if user is being followed by the current user.
    Args:
        user : User object
    Raises:
        NotFound if user isn't present in the database
    """

    if current_user.is_authenticated:
        return db_user_relationship.is_following_user(
            current_user.id, user.id
        )
    return None


@user_bp.route("/<user_name>/taste/", methods=['POST'])
@web_listenstore_needed
def taste(user_name: str):
    """ Show user feedback(love/hate) and pins.
    Feedback has filter on score (1 or -1).

    Args:
        musicbrainz_id (str): the MusicBrainz ID of the user
    Raises:
        NotFound if user isn't present in the database
    """

    score = request.args.get('score', 1)
    try:
        score = int(score)
    except ValueError:
        raise BadRequest("Incorrect int argument score: %s" %
                         request.args.get("score"))

    user = _get_user(user_name)
    user_data = {
        "name": user.musicbrainz_id,
        "id": user.id,
    }

    feedback_count = get_feedback_count_for_user(user.id, score)
    feedback = get_feedback_for_user(user_id=user.id, limit=DEFAULT_NUMBER_OF_FEEDBACK_ITEMS_PER_CALL, offset=0, score=score, metadata=True)
    
    pins = get_pin_history_for_user(user_id=user.id, count=25, offset=0)
    pins = [pin.to_api() for pin in fetch_track_metadata_for_items(pins)]
    pin_count = get_pin_count_for_user(user_id=user.id)

    data = {
        "feedback": [f.to_api() for f in feedback],
        "feedback_count": feedback_count,
        "user": user_data,
        "active_section": "taste",
        "logged_in_user_follows_user": logged_in_user_follows_user(user),
        "pins": pins,
        "pin_count": pin_count,
        "profile_url": url_for('user.profile', user_name=user_name),
    }

    return jsonify(data)


@user_bp.route("/<user_name>/year-in-music/", methods=['POST'])
@user_bp.route("/<user_name>/year-in-music/<int:year>/", methods=['POST'])
def year_in_music(user_name, year: int = 2023):
    """ Year in Music """
    if year != 2021 and year != 2022 and year != 2023:
        raise NotFound(f"Cannot find Year in Music report for year: {year}")

    user = _get_user(user_name)
    return jsonify({
        "data": db_year_in_music.get(user.id, year) or {},
        "user": {
            "id": user.id,
            "name": user.musicbrainz_id,
        },
    })


@user_bp.route("/<user_name>/",  defaults={'path': ''})
@user_bp.route('/<user_name>/<path:path>/')
@web_listenstore_needed
def index(user_name, path):
    user = _get_user(user_name)
    return render_template("user/index.html", user=user)
