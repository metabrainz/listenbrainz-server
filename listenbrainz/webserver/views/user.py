import listenbrainz.db.stats as db_stats
import listenbrainz.db.user as db_user
import urllib
import ujson

from flask import Blueprint, render_template, request, url_for, Response, redirect, flash, current_app, jsonify
from flask_login import current_user, login_required
from influxdb.exceptions import InfluxDBClientError, InfluxDBServerError
from listenbrainz import webserver
from listenbrainz.db.exceptions import DatabaseException
from listenbrainz.domain import spotify
from listenbrainz.webserver import flash
from listenbrainz.webserver.decorators import crossdomain
from listenbrainz.webserver.login import User
from listenbrainz.webserver.redis_connection import _redis
from listenbrainz.webserver.influx_connection import _influx
from listenbrainz.webserver.views.api_tools import publish_data_to_queue
import time
from datetime import datetime
from werkzeug.exceptions import NotFound, BadRequest, RequestEntityTooLarge, InternalServerError

LISTENS_PER_PAGE = 25

user_bp = Blueprint("user", __name__)


@user_bp.route("/<user_name>")
def profile(user_name):
    # Which database to use to showing user listens.
    db_conn = webserver.influx_connection._influx
    # Which database to use to show playing_now stream.
    playing_now_conn = webserver.redis_connection._redis

    user = _get_user(user_name)
    # User name used to get user may not have the same case as original user name.
    user_name = user.musicbrainz_id

    try:
        have_listen_count = True
        listen_count = db_conn.get_listen_count_for_user(user_name)
    except (InfluxDBServerError, InfluxDBClientError):
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

    if max_ts is None and min_ts is None:
        max_ts = int(time.time())

    args = {}
    if max_ts:
        args['to_ts'] = max_ts
    else:
        args['from_ts'] = min_ts

    listens = []
    for listen in db_conn.fetch_listens(user_name, limit=LISTENS_PER_PAGE, **args):
        # Let's fetch one more listen, so we know to show a next page link or not
        listens.append({
            "track_metadata": listen.data,
            "listened_at": listen.ts_since_epoch,
            "listened_at_iso": listen.timestamp.isoformat() + "Z",
        })

    latest_listen = db_conn.fetch_listens(user_name=user_name, limit=1, to_ts=int(time.time()))
    latest_listen_ts = latest_listen[0].ts_since_epoch if len(latest_listen) > 0 else 0

    # Calculate if we need to show next/prev buttons
    previous_listen_ts = None
    next_listen_ts = None
    if listens:
        (min_ts_per_user, max_ts_per_user) = db_conn.get_timestamps_for_user(user_name)
        if min_ts_per_user >= 0:
            if listens[-1]['listened_at'] > min_ts_per_user:
                next_listen_ts = listens[-1]['listened_at']
            else:
                next_listen_ts = None

            if listens[0]['listened_at'] < max_ts_per_user:
                previous_listen_ts = listens[0]['listened_at']
            else:
                previous_listen_ts = None

    # If there are no previous listens then display now_playing
    if not previous_listen_ts:
        playing_now = playing_now_conn.get_playing_now(user.id)
        if playing_now:
            listen = {
                "track_metadata": playing_now.data,
                "playing_now": "true",
            }
            listens.insert(0, listen)

    user_stats = db_stats.get_user_artists(user.id)
    try:
        artist_count = int(user_stats['artist']['all_time']['count'])
    except (KeyError, TypeError):
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
        "previous_listen_ts": previous_listen_ts,
        "next_listen_ts": next_listen_ts,
        "latest_listen_ts": latest_listen_ts,
        "latest_spotify_uri": _get_spotify_uri_for_listens(listens),
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
    """ Redirect to history page """
    return redirect(url_for('user.history', user_name=user_name, entity='artist'), code=301)


@user_bp.route("/<user_name>/history")
def history(user_name):
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
        "user/history.html",
        active_section="history",
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
    First, drops the user's influx measurement and then deletes the user from the
    database.

    Args:
        musicbrainz_id (str): the MusicBrainz ID of the user

    Raises:
        NotFound if user isn't present in the database
    """

    user = _get_user(musicbrainz_id)
    _influx.delete(user.musicbrainz_id)
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
    This, drops the user's influx measurement and resets their listen count.

    Args:
        musicbrainz_id (str): the MusicBrainz ID of the user

    Raises:
        NotFound if user isn't present in the database
    """

    user = _get_user(musicbrainz_id)
    _influx.delete(user.musicbrainz_id)
    _influx.reset_listen_count(user.musicbrainz_id)
    db_user.reset_latest_import(user.musicbrainz_id)
    db_stats.delete_user_stats(user.id)
