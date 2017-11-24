
import urllib
from time import time

from flask import Blueprint, render_template, request, url_for, Response, redirect, current_app
from flask_login import current_user, login_required
from influxdb.exceptions import InfluxDBClientError, InfluxDBServerError
from werkzeug.exceptions import NotFound, BadRequest

import listenbrainz.config as config
import listenbrainz.db.user as db_user
from listenbrainz import webserver
from listenbrainz.webserver.decorators import crossdomain
from listenbrainz.webserver.login import User
from listenbrainz.webserver.redis_connection import _redis

LISTENS_PER_PAGE = 25

user_bp = Blueprint("user", __name__)


@user_bp.route("/<user_name>/scraper.js")
@crossdomain()
def lastfmscraper(user_name):
    """ Fetch the scraper.js with proper variable injecting
    """
    user_token = request.args.get("user_token")
    lastfm_username = request.args.get("lastfm_username")
    if user_token is None or lastfm_username is None:
        raise NotFound
    scraper = render_template(
        "user/scraper.js",
        base_url="{}/1/submit-listens".format(config.API_URL),
        import_url="{}/1/latest-import".format(config.API_URL),
        user_token=user_token,
        lastfm_username=lastfm_username,
        # need to escape user_name here because other wise jinja doesn't handle usernames with backslashes correctly
        user_name=urllib.parse.quote(user_name),
        profile_url=url_for('user.profile', user_name=user_name),
        lastfm_api_key=current_app.config['LASTFM_API_KEY'],
        lastfm_api_url=current_app.config['LASTFM_API_URL'],
    )
    return Response(scraper, content_type="text/javascript")


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
            raise BadRequest("Incorrect timestamp argument max_ts:" % request.args.get("max_ts"))

    min_ts = request.args.get("min_ts")
    if min_ts is not None:
        try:
            min_ts = int(min_ts)
        except ValueError:
            raise BadRequest("Incorrect timestamp argument min_ts:" % request.args.get("min_ts"))

    if max_ts == None and min_ts == None:
        max_ts = int(time())

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

    return render_template(
        "user/profile.html",
        user=user,
        listens=listens,
        previous_listen_ts=previous_listen_ts,
        next_listen_ts=next_listen_ts,
        spotify_uri=_get_spotify_uri_for_listens(listens),
        have_listen_count=have_listen_count,
        listen_count=format(int(listen_count), ",d"),
    )


def _get_user(user_name):
    """ Get current username """
    if current_user.is_authenticated() and \
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
        if "spotify_id" in additional_info:
            return additional_info["spotify_id"].rsplit('/', 1)[-1]
        else:
            return None

    track_ids = [get_track_id_from_listen(l) for l in listens]
    track_ids = [t_id for t_id in track_ids if t_id]

    if track_ids:
        return "spotify:trackset:Recent listens:" + ",".join(track_ids)
    else:
        return None


