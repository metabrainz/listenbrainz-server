import listenbrainz.db.stats as db_stats
import listenbrainz.db.user as db_user
import listenbrainz.db.user_relationship as db_user_relationship
import ujson

from flask import Blueprint, render_template, request, url_for, redirect, current_app
from flask_login import current_user
from listenbrainz import webserver
from listenbrainz.db.playlist import get_playlists_for_user, get_playlists_created_for_user, get_playlists_collaborated_on
from listenbrainz.webserver.login import User
from listenbrainz.webserver.decorators import web_listenstore_needed
from listenbrainz.webserver import timescale_connection
from listenbrainz.webserver.views.api import DEFAULT_NUMBER_OF_PLAYLISTS_PER_CALL
from werkzeug.exceptions import NotFound, BadRequest
from listenbrainz.webserver.views.playlist_api import serialize_jspf
from pydantic import ValidationError

from listenbrainz.webserver.views.views_utils import get_current_spotify_user, get_current_youtube_user

LISTENS_PER_PAGE = 25

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
            print(url_for(target, user_name=current_user.musicbrainz_id, **request.args))
            return redirect(url_for(target, user_name=current_user.musicbrainz_id, **request.args))
        else:
            return current_app.login_manager.unauthorized()
        pass
    return inner


redirect_bp.add_url_rule("/listens", "redirect_listens", redirect_user_page("user.profile"))
redirect_bp.add_url_rule("/charts", "redirect_charts", redirect_user_page("user.charts"))
redirect_bp.add_url_rule("/reports", "redirect_reports", redirect_user_page("user.reports"))
redirect_bp.add_url_rule("/playlists", "redirect_playlists", redirect_user_page("user.playlists"))
redirect_bp.add_url_rule("/collaborations", "redirect_collaborations", redirect_user_page("user.collaborations"))
redirect_bp.add_url_rule("/recommendations",
                         "redirect_recommendations",
                         redirect_user_page("user.recommendation_playlists"))

@user_bp.route("/<user_name>")
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
            raise BadRequest("Incorrect timestamp argument max_ts: %s" % request.args.get("max_ts"))

    min_ts = request.args.get("min_ts")
    if min_ts is not None:
        try:
            min_ts = int(min_ts)
        except ValueError:
            raise BadRequest("Incorrect timestamp argument min_ts: %s" % request.args.get("min_ts"))

    args = {}
    if max_ts:
        args['to_ts'] = max_ts
    else:
        args['from_ts'] = min_ts
    data, min_ts_per_user, max_ts_per_user = db_conn.fetch_listens(user_name, limit=LISTENS_PER_PAGE, **args)

    listens = []
    for listen in data:
        listens.append({
            "track_metadata": listen.data,
            "listened_at": listen.ts_since_epoch,
            "listened_at_iso": listen.timestamp.isoformat() + "Z",
        })

    # If there are no previous listens then display now_playing
    if not listens or listens[0]['listened_at'] >= max_ts_per_user:
        playing_now = playing_now_conn.get_playing_now(user.id)
        if playing_now:
            listen = {
                "track_metadata": playing_now.data,
                "playing_now": "true",
            }
            listens.insert(0, listen)

    user_stats = db_stats.get_user_artists(user.id, 'all_time')
    try:
        artist_count = user_stats.all_time.count
    except (AttributeError, ValidationError):
        artist_count = None

    spotify_data = get_current_spotify_user()
    youtube_data = get_current_youtube_user()
    current_user_data = {}
    logged_in_user_follows_user = None
    if current_user.is_authenticated:
        current_user_data = {
            "id": current_user.id,
            "name": current_user.musicbrainz_id,
            "auth_token": current_user.auth_token,
        }
        logged_in_user_follows_user = db_user_relationship.is_following_user(current_user.id, user.id)

    props = {
        "user": {
            "id": user.id,
            "name": user.musicbrainz_id,
        },
        "current_user": current_user_data,
        "listens": listens,
        "latest_listen_ts": max_ts_per_user,
        "oldest_listen_ts": min_ts_per_user,
        "latest_spotify_uri": _get_spotify_uri_for_listens(listens),
        "artist_count": format(artist_count, ",d") if artist_count else None,
        "profile_url": url_for('user.profile', user_name=user_name),
        "mode": "listens",
        "spotify": spotify_data,
        "youtube": youtube_data,
        "web_sockets_server_url": current_app.config['WEBSOCKETS_SERVER_URL'],
        "api_url": current_app.config['API_URL'],
        "logged_in_user_follows_user": logged_in_user_follows_user,
        "sentry_dsn": current_app.config.get("LOG_SENTRY", {}).get("dsn")
    }

    return render_template("user/profile.html",
                           props=ujson.dumps(props),
                           mode='listens',
                           user=user,
                           active_section='listens')


@user_bp.route("/<user_name>/artists")
def artists(user_name):
    """ Redirect to charts page """
    page = request.args.get('page', default=1)
    stats_range = request.args.get('range', default="all_time")
    return redirect(url_for('user.charts', user_name=user_name, entity='artist', page=page, range=stats_range), code=301)


@user_bp.route("/<user_name>/history")
def history(user_name):
    """ Redirect to charts page """
    entity = request.args.get('entity', default="artist")
    page = request.args.get('page', default=1)
    stats_range = request.args.get('range', default="all_time")
    return redirect(url_for('user.charts', user_name=user_name, entity=entity, page=page, range=stats_range), code=301)


@user_bp.route("/<user_name>/charts")
def charts(user_name):
    """ Show the top entitys for the user. """
    user = _get_user(user_name)

    user_data = {
        "name": user.musicbrainz_id,
        "id": user.id,
    }

    props = {
        "user": user_data,
        "api_url": current_app.config["API_URL"],
        "sentry_dsn": current_app.config.get("LOG_SENTRY", {}).get("dsn")
    }

    return render_template(
        "user/charts.html",
        active_section="charts",
        props=ujson.dumps(props),
        user=user
    )


@user_bp.route("/<user_name>/reports")
def reports(user_name: str):
    """ Show user reports """
    user = _get_user(user_name)

    user_data = {
        "name": user.musicbrainz_id,
        "id": user.id,
    }

    props = {
        "user": user_data,
        "api_url": current_app.config["API_URL"],
        "sentry_dsn": current_app.config.get("LOG_SENTRY", {}).get("dsn")
    }

    return render_template(
        "user/reports.html",
        active_section="reports",
        props=ujson.dumps(props),
        user=user
    )

@user_bp.route("/<user_name>/playlists")
@web_listenstore_needed
def playlists(user_name: str):
    """ Show user playlists """

    offset = request.args.get('offset', 0)
    try:
        offset = int(offset)
    except ValueError:
        raise BadRequest("Incorrect int argument offset: %s" % request.args.get("offset"))

    count = request.args.get("count", DEFAULT_NUMBER_OF_PLAYLISTS_PER_CALL)
    try:
        count = int(count)
    except ValueError:
        raise BadRequest("Incorrect int argument count: %s" % request.args.get("count"))

    user = _get_user(user_name)
    user_data = {
        "name": user.musicbrainz_id,
        "id": user.id,
    }

    current_user_data = {}
    if current_user.is_authenticated:
        current_user_data = {
            "id": current_user.id,
            "name": current_user.musicbrainz_id,
            "auth_token": current_user.auth_token,
        }

    include_private = current_user.is_authenticated and current_user.id == user.id

    playlists = []
    user_playlists, playlist_count = get_playlists_for_user(user.id,
                                                            include_private=include_private,
                                                            load_recordings=False,
                                                            count=count,
                                                            offset=offset)
    for playlist in user_playlists:
        playlists.append(serialize_jspf(playlist))

    props = {
        "current_user": current_user_data,
        "api_url": current_app.config["API_URL"],
        "playlists": playlists,
        "user": user_data,
        "active_section": "playlists",
        "playlist_count": playlist_count,
        "pagination_offset": offset,
        "playlists_per_page": count,
        "sentry_dsn": current_app.config.get("LOG_SENTRY", {}).get("dsn")
    }

    return render_template(
        "playlists/playlists.html",
        active_section="playlists",
        props=ujson.dumps(props),
        user=user
    )


@user_bp.route("/<user_name>/recommendations")
@web_listenstore_needed
def recommendation_playlists(user_name: str):
    """ Show playlists created for user """

    offset = request.args.get('offset', 0)
    try:
        offset = int(offset)
    except ValueError:
        raise BadRequest("Incorrect int argument offset: %s" % request.args.get("offset"))

    count = request.args.get("count", DEFAULT_NUMBER_OF_PLAYLISTS_PER_CALL)
    try:
        count = int(count)
    except ValueError:
        raise BadRequest("Incorrect int argument count: %s" % request.args.get("count"))
    user = _get_user(user_name)
    user_data = {
        "name": user.musicbrainz_id,
        "id": user.id,
    }
    current_user_data = {}
    if current_user.is_authenticated:
        current_user_data = {
            "id": current_user.id,
            "name": current_user.musicbrainz_id,
            "auth_token": current_user.auth_token,
        }

    playlists = []
    user_playlists, playlist_count = get_playlists_created_for_user(user.id, False, count, offset)
    for playlist in user_playlists:
        playlists.append(serialize_jspf(playlist))


    props = {
        "current_user": current_user_data,
        "api_url": current_app.config["API_URL"],
        "playlists": playlists,
        "user": user_data,
        "active_section": "recommendations",
        "playlist_count": playlist_count,
        "sentry_dsn": current_app.config.get("LOG_SENTRY", {}).get("dsn")
    }

    return render_template(
        "playlists/playlists.html",
        active_section="recommendations",
        props=ujson.dumps(props),
        user=user
    )

@user_bp.route("/<user_name>/collaborations")
@web_listenstore_needed
def collaborations(user_name: str):
    """ Show playlists a user collaborates on """

    offset = request.args.get('offset', 0)
    try:
        offset = int(offset)
    except ValueError:
        raise BadRequest("Incorrect int argument offset: %s" % request.args.get("offset"))

    count = request.args.get("count", DEFAULT_NUMBER_OF_PLAYLISTS_PER_CALL)
    try:
        count = int(count)
    except ValueError:
        raise BadRequest("Incorrect int argument count: %s" % request.args.get("count"))

    user = _get_user(user_name)
    user_data = {
        "name": user.musicbrainz_id,
        "id": user.id,
    }

    current_user_data = {}
    if current_user.is_authenticated:
        current_user_data = {
            "id": current_user.id,
            "name": current_user.musicbrainz_id,
            "auth_token": current_user.auth_token,
        }

    include_private = current_user.is_authenticated and current_user.id == user.id

    playlists = []
    colalborative_playlists, playlist_count = get_playlists_collaborated_on(user.id,
                                                                            include_private=include_private,
                                                                            load_recordings=False,
                                                                            count=count,
                                                                            offset=offset)
    for playlist in colalborative_playlists:
        playlists.append(serialize_jspf(playlist))

    props = {
        "current_user": current_user_data,
        "api_url": current_app.config["API_URL"],
        "playlists": playlists,
        "user": user_data,
        "active_section": "collaborations",
        "playlist_count": playlist_count,
        "sentry_dsn": current_app.config.get("LOG_SENTRY", {}).get("dsn")
    }

    return render_template(
        "playlists/playlists.html",
        active_section="collaborations",
        props=ujson.dumps(props),
        user=user
    )


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


def _get_spotify_uri_for_listens(listens):

    def get_track_id_from_listen(listen):
        additional_info = listen["track_metadata"]["additional_info"]
        if "spotify_id" in additional_info and additional_info["spotify_id"] is not None:
            return additional_info["spotify_id"].rsplit('/', 1)[-1]
        else:
            return None

    track_id = None
    if len(listens):
        track_id = get_track_id_from_listen(listens[0])

    if track_id:
        return "spotify:track:" + track_id
    else:
        return None


def delete_user(musicbrainz_id):
    """ Delete a user from ListenBrainz completely.
    First, drops the user's listens and then deletes the user from the
    database.
    Args:
        musicbrainz_id (str): the MusicBrainz ID of the user
    Raises:
        NotFound if user isn't present in the database
    """

    user = _get_user(musicbrainz_id)
    timescale_connection._ts.delete(user.musicbrainz_id)
    db_user.delete(user.id)


def delete_listens_history(musicbrainz_id):
    """ Delete a user's listens from ListenBrainz completely.
    Args:
        musicbrainz_id (str): the MusicBrainz ID of the user
    Raises:
        NotFound if user isn't present in the database
    """

    user = _get_user(musicbrainz_id)
    timescale_connection._ts.delete(user.musicbrainz_id)
    timescale_connection._ts.reset_listen_count(user.musicbrainz_id)
    db_user.reset_latest_import(user.musicbrainz_id)
    db_stats.delete_user_stats(user.id)
