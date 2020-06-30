import listenbrainz.db.stats as db_stats
import listenbrainz.db.user as db_user
import urllib
import ujson
import psycopg2
import datetime

from flask import Blueprint, render_template, request, url_for, Response, redirect, flash, current_app, jsonify
from flask_login import current_user, login_required
from listenbrainz import webserver
from listenbrainz.db.exceptions import DatabaseException
from listenbrainz.domain import spotify
from listenbrainz.webserver import flash
from listenbrainz.webserver.decorators import crossdomain
from listenbrainz.webserver.login import User
from listenbrainz.webserver.redis_connection import _redis
from listenbrainz.webserver.timescale_connection import _ts
from listenbrainz.webserver.views.api_tools import publish_data_to_queue
import time
from datetime import datetime
from werkzeug.exceptions import NotFound, BadRequest, RequestEntityTooLarge, InternalServerError
from pydantic import ValidationError

LISTENS_PER_PAGE = 25

user_bp = Blueprint("user", __name__)


@user_bp.route("/<user_name>")
def profile(user_name):
    # Which database to use to showing user listens.
    db_conn = webserver.timescale_connection._ts
    # Which database to use to show playing_now stream.
    playing_now_conn = webserver.redis_connection._redis

    user = _get_user(user_name)
    # User name used to get user may not have the same case as original user name.
    user_name = user.musicbrainz_id

    try:
        have_listen_count = True
        listen_count = db_conn.get_listen_count_for_user(user_name)
    except psycopg2.OperationalError:
        have_listen_count = False
        listen_count = 0

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

    search_larger_time_range = request.args.get("search_larger_time_range", 0)
    try:
        search_larger_time_range = int(search_larger_time_range)
    except ValueError:
        raise BadRequest("search_larger_time_range must be an integer value 0 or greater: %s" % search_larger_time_range)

    # Send min and max listen times to allow React component to hide prev/next buttons accordingly
    (min_ts_per_user, max_ts_per_user) = db_conn.get_timestamps_for_user(user_name)

    if max_ts is None and min_ts is None:
        if max_ts_per_user:
            max_ts = max_ts_per_user + 1
        else:
            max_ts = int(time.time())

    listens_missing = 0
    listens = []
    if min_ts_per_user != max_ts_per_user:
        args = {}
        # if we're supposed to search larger time range then search 50 days. (each increment in time_range == 5 days)
        args['time_range'] = 10 if search_larger_time_range else None
        if max_ts:
            args['to_ts'] = max_ts
        else:
            args['from_ts'] = min_ts
        for listen in db_conn.fetch_listens(user_name, limit=LISTENS_PER_PAGE, **args):
            listens.append({
                "track_metadata": listen.data,
                "listened_at": listen.ts_since_epoch,
                "listened_at_iso": listen.timestamp.isoformat() + "Z",
            })
        if len(listens) < LISTENS_PER_PAGE and search_larger_time_range == 0:
            listens_missing = 1

    # If there are no previous listens then display now_playing
    if  not listens or listens[0]['listened_at'] >= max_ts_per_user:
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

    spotify_data = {}
    if current_user.is_authenticated:
        spotify_data = spotify.get_user_dict(current_user.id)

    props = {
        "user": {
            "id": user.id,
            "name": user.musicbrainz_id,
        },
        "listens": listens,
        "latest_listen_ts": max_ts_per_user,
        "oldest_listen_ts": min_ts_per_user,
        "latest_spotify_uri": _get_spotify_uri_for_listens(listens),
        "search_larger_time_range": listens_missing,
        "have_listen_count": have_listen_count,
        "listen_count": format(int(listen_count), ",d"),
        "artist_count": format(artist_count, ",d") if artist_count else None,
        "profile_url": url_for('user.profile', user_name=user_name),
        "mode": "listens",
        "spotify": spotify_data,
        "web_sockets_server_url": current_app.config['WEBSOCKETS_SERVER_URL'],
        "api_url": current_app.config['API_URL'],
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
        "api_url": current_app.config["API_URL"]
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
        "api_url": current_app.config["API_URL"]
    }

    return render_template(
        "user/reports.html",
        active_section="reports",
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
    _ts.delete(user.musicbrainz_id)
    publish_data_to_queue(
        data={
            'type': 'delete.user',
            'musicbrainz_id': musicbrainz_id,
        },
        exchange=current_app.config['BIGQUERY_EXCHANGE'],
        queue=current_app.config['BIGQUERY_QUEUE'],
        error_msg='Could not put user %s into queue for deletion, please try again later' % musicbrainz_id,
    )
    db_user.delete(user.id)


def delete_listens_history(musicbrainz_id):
    """ Delete a user's listens from ListenBrainz completely.

    Args:
        musicbrainz_id (str): the MusicBrainz ID of the user

    Raises:
        NotFound if user isn't present in the database
    """

    user = _get_user(musicbrainz_id)
    _ts.delete(user.musicbrainz_id)
    _ts.reset_listen_count(user.musicbrainz_id)
    db_user.reset_latest_import(user.musicbrainz_id)
    db_stats.delete_user_stats(user.id)
