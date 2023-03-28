import listenbrainz.db.user as db_user
import listenbrainz.db.user_relationship as db_user_relationship
import orjson

from flask import Blueprint, render_template, request, url_for, redirect, current_app, jsonify
from flask_login import current_user

from data.model.external_service import ExternalServiceType
from listenbrainz import webserver
from listenbrainz.db import listens_importer
from listenbrainz.db.missing_musicbrainz_data import get_user_missing_musicbrainz_data
from listenbrainz.db.msid_mbid_mapping import fetch_track_metadata_for_items
from listenbrainz.db.playlist import get_playlists_for_user, get_playlists_created_for_user, \
    get_playlists_collaborated_on
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
from listenbrainz.webserver.views.playlist_api import serialize_jspf

LISTENS_PER_PAGE = 25
DEFAULT_NUMBER_OF_FEEDBACK_ITEMS_PER_CALL = 25

user_bp = Blueprint("user", __name__)
redirect_bp = Blueprint("redirect", __name__)


def redirect_user_page(target):
    """Redirect a well-known url to a user's profile.

    The user-facing informational pages contain a username in the url. This means
    that we don't have a standard url that we can send any user to (for example a link
    on twitter). We configure some standardised URLS /my/[page] that will redirect
    the user to this specific page in their namespace if they are logged in."""

    def inner():
        if current_user.is_authenticated:
            return redirect(url_for(target, user_name=current_user.musicbrainz_id, **request.args))
        else:
            return current_app.login_manager.unauthorized()

    return inner


redirect_bp.add_url_rule("/listens/", "redirect_listens",
                         redirect_user_page("user.profile"))
redirect_bp.add_url_rule("/stats/", "redirect_stats",
                         redirect_user_page("user.stats"))
redirect_bp.add_url_rule("/playlists/", "redirect_playlists",
                         redirect_user_page("user.playlists"))
redirect_bp.add_url_rule("/recommendations/",
                         "redirect_recommendations",
                         redirect_user_page("user.recommendation_playlists"))
redirect_bp.add_url_rule("/taste/", "redirect_taste",
                         redirect_user_page("user.taste"))
redirect_bp.add_url_rule("/year-in-music/", "redirect_year_in_music",
                         redirect_user_page("user.year_in_music"))


@user_bp.route("/<user_name>/")
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
        args['to_ts'] = max_ts
    else:
        args['from_ts'] = min_ts
    data, min_ts_per_user, max_ts_per_user = db_conn.fetch_listens(
        user.to_dict(), limit=LISTENS_PER_PAGE, **args)

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
        already_reported_user = db_user.is_user_reported(
            current_user.id, user.id)

    pin = get_current_pin_for_user(user_id=user.id)
    if pin:
        pin = fetch_track_metadata_for_items([pin])[0].to_api()

    props = {
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

    return render_template("user/profile.html",
                           props=orjson.dumps(props).decode("utf-8"),
                           user=user,
                           active_section='listens')


@user_bp.route("/<user_name>/artists/")
def artists(user_name):
    """ Redirect to charts page """
    page = request.args.get('page', default=1)
    stats_range = request.args.get('range', default="all_time")
    return redirect(url_for('user.charts', user_name=user_name, entity='artist', page=page, range=stats_range),
                    code=301)


@user_bp.route("/<user_name>/history/")
def history(user_name):
    """ Redirect to charts page """
    entity = request.args.get('entity', default="artist")
    page = request.args.get('page', default=1)
    stats_range = request.args.get('range', default="all_time")
    return redirect(url_for('user.charts', user_name=user_name, entity=entity, page=page, range=stats_range), code=301)


@user_bp.route("/<user_name>/charts/")
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

    return render_template(
        "user/charts.html",
        active_section="stats",
        props=orjson.dumps(props).decode("utf-8"),
        user=user
    )

@user_bp.route("/<user_name>/reports/")
def reports(user_name):
    """ Redirect to stats page """
    return redirect(url_for('user.stats', user_name=user_name), code=301)


@user_bp.route("/<user_name>/stats/")
def stats(user_name: str):
    """ Show user stats """
    user = _get_user(user_name)

    user_data = {
        "name": user.musicbrainz_id,
        "id": user.id,
    }

    props = {
        "user": user_data,
        "logged_in_user_follows_user": logged_in_user_follows_user(user),
    }

    return render_template(
        "user/stats.html",
        active_section="stats",
        props=orjson.dumps(props).decode("utf-8"),
        user=user
    )


@user_bp.route("/<user_name>/collaborations/")
def collaborations(user_name: str):
    return redirect(url_for("user.playlists", user_name=user_name))


@user_bp.route("/<user_name>/playlists/")
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
        playlists.append(serialize_jspf(playlist))

    props = {
        "playlists": playlists,
        "user": user_data,
        "active_section": "playlists",
        "playlist_count": playlist_count,
        "logged_in_user_follows_user": logged_in_user_follows_user(user),
    }

    return render_template(
        "playlists/playlists.html",
        active_section="playlists",
        props=orjson.dumps(props).decode("utf-8"),
        user=user
    )


@user_bp.route("/<user_name>/recommendations/")
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
    user_playlists, playlist_count = get_playlists_created_for_user(
        user.id, False, count, offset)
    for playlist in user_playlists:
        playlists.append(serialize_jspf(playlist))

    props = {
        "playlists": playlists,
        "user": user_data,
        "playlist_count": playlist_count,
        "logged_in_user_follows_user": logged_in_user_follows_user(user),
    }

    return render_template(
        "playlists/recommendations.html",
        active_section="recommendations",
        props=orjson.dumps(props).decode("utf-8"),
        user=user
    )



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


@user_bp.route("/<user_name>/taste/")
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

    props = {
        "feedback": [f.to_api() for f in feedback],
        "feedback_count": feedback_count,
        "user": user_data,
        "active_section": "taste",
        "logged_in_user_follows_user": logged_in_user_follows_user(user),
        "pins": pins,
        "pin_count": pin_count,
        "profile_url": url_for('user.profile', user_name=user_name),
    }

    return render_template(
        "user/taste.html",
        active_section="taste",
        props=orjson.dumps(props).decode("utf-8"),
        user=user
    )


@user_bp.route("/<user_name>/year-in-music/")
@user_bp.route("/<user_name>/year-in-music/<int:year>/")
def year_in_music(user_name, year: int = 2022):
    """ Year in Music """
    if year != 2021 and year != 2022:
        raise NotFound(f"Cannot find Year in Music report for year: {year}")

    user = _get_user(user_name)
    return render_template(
        "user/year-in-music.html",
        user_name=user_name,
        year=year,
        props=orjson.dumps({
            "data": db_year_in_music.get(user.id, year),
            "user": {
                "id": user.id,
                "name": user.musicbrainz_id,
            }
        }).decode("utf-8"),
        year_in_music_js_file=f"yearInMusic{year}.js"
    )


@user_bp.route("/<user_name>/missing-data/")
def missing_mb_data(user_name: str):
    """ Shows missing musicbrainz data """
    user = _get_user(user_name)
    missing_data, created = get_user_missing_musicbrainz_data(user.id, "cf")

    props = {
        "missingData": missing_data or [],
        "user": {
            "id": user.id,
            "name": user.musicbrainz_id,
        }
    }

    return render_template("user/missing_data.html", user=user, props=orjson.dumps(props).decode("utf-8"))
