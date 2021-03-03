import locale
import os
import requests
import subprocess

from brainzutils import cache
from datetime import datetime
from dateutil.relativedelta import relativedelta
from typing import List
from flask import Blueprint, render_template, current_app, redirect, url_for, request, jsonify
from flask_login import current_user, login_required
from requests.exceptions import HTTPError
import ujson
from werkzeug.exceptions import Unauthorized, NotFound

import listenbrainz.db.user as db_user
from listenbrainz.db.exceptions import DatabaseException
from listenbrainz.domain import spotify
from listenbrainz import webserver
from listenbrainz.webserver import flash
from listenbrainz.webserver.timescale_connection import _ts
from listenbrainz.webserver.redis_connection import _redis
from listenbrainz.webserver.views.user import delete_user


index_bp = Blueprint('index', __name__)
locale.setlocale(locale.LC_ALL, '')

STATS_PREFIX = 'listenbrainz.stats' # prefix used in key to cache stats
CACHE_TIME = 10 * 60 # time in seconds we cache the stats
NUMBER_OF_RECENT_LISTENS = 50

@index_bp.route("/")
def index():

    # get total listen count
    try:
        listen_count = _ts.get_total_listen_count()
    except Exception as e:
        current_app.logger.error('Error while trying to get total listen count: %s', str(e))
        listen_count = None


    return render_template(
        "index/index.html",
        listen_count=listen_count,
    )


@index_bp.route("/import")
def import_data():
    if current_user.is_authenticated:
        return redirect(url_for("profile.import_data"))
    else:
        return current_app.login_manager.unauthorized()


@index_bp.route("/download")
def downloads():
    return redirect(url_for('index.data'))


@index_bp.route("/data")
def data():
    return render_template("index/data.html")


@index_bp.route("/contribute")
def contribute():
    return render_template("index/contribute.html")


@index_bp.route("/add-data")
def add_data_info():
    return render_template("index/add-data.html")


@index_bp.route("/import-data")
def import_data_info():
    return render_template("index/import-data.html")


@index_bp.route("/goals")
def goals():
    return render_template("index/goals.html")


@index_bp.route("/faq")
def faq():
    return render_template("index/faq.html")


@index_bp.route("/lastfm-proxy")
def proxy():
    return render_template("index/lastfm-proxy.html")


@index_bp.route("/roadmap")
def roadmap():
    return render_template("index/roadmap.html")


@index_bp.route("/current-status")
def current_status():

    load = "%.2f %.2f %.2f" % os.getloadavg()

    listen_count = _ts.get_total_listen_count()
    try:
        user_count = format(int(_get_user_count()), ',d')
    except DatabaseException as e:
        user_count = 'Unknown'

    listen_counts_per_day: List[dict] = []
    for delta in range(2):
        try:
            day = datetime.utcnow() - relativedelta(days=delta)
            day_listen_count = _redis.get_listen_count_for_day(day)
        except:
            current_app.logger.error("Could not get %s listen count from redis", day.strftime('%Y-%m-%d'), exc_info=True)
            day_listen_count = None
        listen_counts_per_day.append({
            "date": day.strftime('%Y-%m-%d'),
            "listen_count": format(day_listen_count, ',d') if day_listen_count else "0",
            "label": "today" if delta == 0 else "yesterday",
        })

    return render_template(
        "index/current-status.html",
        load=load,
        listen_count=format(int(listen_count), ",d") if listen_count else "0",
        user_count=user_count,
        listen_counts_per_day=listen_counts_per_day,
    )


@index_bp.route("/recent")
def recent_listens():

    recent = []
    for listen in _redis.get_recent_listens(NUMBER_OF_RECENT_LISTENS):
        recent.append({
                "track_metadata": listen.data,
                "user_name" : listen.user_name,
                "listened_at": listen.ts_since_epoch,
                "listened_at_iso": listen.timestamp.isoformat() + "Z",
            })

    spotify_user = {}
    if current_user.is_authenticated:
        spotify_user = spotify.get_user_dict(current_user.id)

    props = {
        "listens": recent,
        "mode": "recent",
        "spotify": spotify_user,
        "api_url": current_app.config["API_URL"],
    }

    return render_template("index/recent.html",
        props=ujson.dumps(props),
        mode='recent',
        active_section='listens')

@index_bp.route('/feed', methods=['GET', 'OPTIONS'])
@login_required
def feed():

    # TODO (param): remove this when feed feature is ready for release #feedfeatureflag
    if current_user.musicbrainz_id not in ['rob', 'iliekcomputers', 'mr_monkey', 'shivam-kapila', 'ishaanshah', 'alastairp', 'amCap1712']:
        raise NotFound

    spotify_user = {}
    if current_user.is_authenticated:
        spotify_user = spotify.get_user_dict(current_user.id)

    current_user_data = {
        "id": current_user.id,
        "name": current_user.musicbrainz_id,
        "auth_token": current_user.auth_token,
    }

    props = {
        "current_user": current_user_data,
        "spotify": spotify_user,
        "api_url": current_app.config["API_URL"],
    }
    return render_template('index/feed.html', props=ujson.dumps(props))



@index_bp.route('/agree-to-terms', methods=['GET', 'POST'])
@login_required
def gdpr_notice():
    if request.method == 'GET':
        return render_template('index/gdpr.html', next=request.args.get('next'))
    elif request.method == 'POST':
        if request.form.get('gdpr-options') == 'agree':
            try:
                db_user.agree_to_gdpr(current_user.musicbrainz_id)
            except DatabaseException as e:
                flash.error('Could not store agreement to GDPR terms')
            next = request.form.get('next')
            if next:
                return redirect(next)
            return redirect(url_for('index.index'))
        elif request.form.get('gdpr-options') == 'disagree':
            return redirect(url_for('profile.delete'))
        else:
            flash.error('You must agree to or decline our terms')
            return render_template('index/gdpr.html', next=request.args.get('next'))


@index_bp.route('/delete-user/<int:musicbrainz_row_id>')
def mb_user_deleter(musicbrainz_row_id):
    """ This endpoint is used by MusicBrainz to delete accounts once they
    are deleted on MusicBrainz too.

    See https://tickets.metabrainz.org/browse/MBS-9680 for details.

    Args: musicbrainz_row_id (int): the MusicBrainz row ID of the user to be deleted.

    Returns: 200 if the user has been successfully found and deleted from LB

    Raises:
        NotFound if the user is not found in the LB database
        Unauthorized if the MusicBrainz access token provided with the query is invalid
    """
    _authorize_mb_user_deleter(request.args.get('access_token', ''))
    user = db_user.get_by_mb_row_id(musicbrainz_row_id)
    if user is None:
        raise NotFound('Could not find user with MusicBrainz Row ID: %d' % musicbrainz_row_id)
    delete_user(user['musicbrainz_id'])
    return jsonify({'status': 'ok'}), 200


def _authorize_mb_user_deleter(auth_token):
    headers = {'Authorization': 'Bearer {}'.format(auth_token)}
    r = requests.get(current_app.config['MUSICBRAINZ_OAUTH_URL'], headers=headers)
    try:
        r.raise_for_status()
    except HTTPError:
        raise Unauthorized('Not authorized to use this view')

    data = {}
    try:
        data = r.json()
    except ValueError:
        raise Unauthorized('Not authorized to use this view')

    try:
        # 2007538 is the row ID of the `UserDeleter` account that is
        # authorized to access the `delete-user` endpoint
        if data['sub'] != 'UserDeleter' or data['metabrainz_user_id'] != 2007538:
            raise Unauthorized('Not authorized to use this view')
    except KeyError:
        raise Unauthorized('Not authorized to use this view')


def _get_user_count():
    """ Gets user count from either the brainzutils cache or from the database.
        If not present in the cache, it makes a query to the db and stores the
        result in the cache for 10 minutes.
    """
    user_count_key = "{}.{}".format(STATS_PREFIX, 'user_count')
    user_count = cache.get(user_count_key, decode=False)
    if user_count:
        return user_count
    else:
        try:
            user_count = db_user.get_user_count()
        except DatabaseException as e:
            raise
        cache.set(user_count_key, int(user_count), CACHE_TIME, encode=False)
        return user_count
