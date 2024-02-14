import locale
import os
import requests

from brainzutils import cache
from datetime import datetime
from dateutil.relativedelta import relativedelta
from typing import List
from flask import Blueprint, render_template, current_app, redirect, url_for, request, jsonify
from flask_login import current_user, login_required
from requests.exceptions import HTTPError
import orjson
from werkzeug.exceptions import Unauthorized, NotFound

import listenbrainz.db.user as db_user
from data.model.user_entity import EntityRecord
from listenbrainz.db.exceptions import DatabaseException
from listenbrainz.webserver.decorators import web_listenstore_needed
from listenbrainz.webserver import flash, db_conn
from listenbrainz.webserver.timescale_connection import _ts
from listenbrainz.webserver.redis_connection import _redis
from listenbrainz.webserver.views.user import delete_user
import listenbrainz.db.stats as db_stats

index_bp = Blueprint('index', __name__)
locale.setlocale(locale.LC_ALL, '')

STATS_PREFIX = 'listenbrainz.stats'  # prefix used in key to cache stats
CACHE_TIME = 10 * 60  # time in seconds we cache the stats
NUMBER_OF_RECENT_LISTENS = 50

SEARCH_USER_LIMIT = 100  # max number of users to return in search username results


@index_bp.route("/")
def index():
    if current_user.is_authenticated and request.args.get("redirect", "true") == "true":
        return redirect(url_for("user.profile", user_name=current_user.musicbrainz_id))

    if _ts:
        try:
            listen_count = _ts.get_total_listen_count()
        except Exception as e:
            current_app.logger.error('Error while trying to get total listen count: %s', str(e))
            listen_count = 0
    else:
        listen_count = 0

    artist_count = 0
    try:
        artist_stats = db_stats.get(db_stats.SITEWIDE_STATS_USER_ID, "artists", "all_time", EntityRecord)
        if artist_stats is not None:
            artist_count = artist_stats.count
    except Exception as e:
        current_app.logger.error('Error while trying to get total artist count: %s', str(e))

    props = {
        "listen_count": listen_count,
        "artist_count": artist_count,
    }

    return render_template(
        "index/index.html",
        props=orjson.dumps(props).decode("utf-8")
    )


@index_bp.route("/import/")
def import_data():
    if current_user.is_authenticated:
        return redirect(url_for("settings.index", path='import/'))
    else:
        return current_app.login_manager.unauthorized()


@index_bp.route("/download/")
def downloads():
    return redirect(url_for('index.data'))


@index_bp.route("/data/")
def data():
    return render_template("index/data.html",active_about_section="using-data")


@index_bp.route("/add-data/")
def add_data_info():
    return render_template("index/add-data.html", active_about_section="add-listens")


@index_bp.route("/import-data/")
def import_data_info():
    return render_template("index/import-data.html")


@index_bp.route("/lastfm-proxy/")
def proxy():
    return render_template("index/lastfm-proxy.html")


@index_bp.route("/about/")
def about():
    return render_template("index/about.html", active_about_section="about")


@index_bp.route("/terms-of-service/")
def terms_of_service():
    return render_template("index/terms-of-service.html", active_about_section="terms-of-service")


@index_bp.route("/blog-data/")
def blog_data():
    """Proxy to the MetaBrainz blog to get recent posts so that user IP addresses are not leaked to wordpress"""

    cache_key = "blog-feed"
    cache_blog_expires = 60*60
    cached_blog = cache.get(cache_key)
    if cached_blog:
        return jsonify(cached_blog)

    url = "https://public-api.wordpress.com/rest/v1.1/sites/blog.metabrainz.org/posts/"
    try:
        r = requests.get(url, timeout=5)
        r.raise_for_status()
        blog_data = r.json()
        cache.set(cache_key, blog_data, cache_blog_expires)
        return jsonify(blog_data)
    except (requests.exceptions.HTTPError, requests.exceptions.ConnectionError):
        return jsonify({}), 503


@index_bp.route("/current-status/")
@web_listenstore_needed
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
        active_about_section="site-status"
    )


@index_bp.route("/recent/")
def recent_listens():

    recent = []
    for listen in _redis.get_recent_listens(NUMBER_OF_RECENT_LISTENS):
        recent.append({
                "track_metadata": listen.data,
                "user_name" : listen.user_name,
                "listened_at": listen.ts_since_epoch,
                "listened_at_iso": listen.timestamp.isoformat() + "Z",
            })
            
    listen_count = _ts.get_total_listen_count()
    try:
        user_count = format(int(_get_user_count()), ',d')
    except DatabaseException as e:
        user_count = 'Unknown'

    props = {
        "listens": recent,
        "globalListenCount": listen_count,
        "globalUserCount": user_count
    }

    return render_template("index/recent.html", props=orjson.dumps(props).decode("utf-8"))


@index_bp.route('/feed/', methods=['GET', 'OPTIONS'])
@login_required
@web_listenstore_needed
def feed():
    return render_template('index/feed.html')


@index_bp.route('/agree-to-terms/', methods=['GET', 'POST'])
@login_required
def gdpr_notice():
    if request.method == 'GET':
        return render_template('index/gdpr.html', next=request.args.get('next'))
    elif request.method == 'POST':
        if request.form.get('gdpr-options') == 'agree':
            try:
                db_user.agree_to_gdpr(db_conn, current_user.musicbrainz_id)
            except DatabaseException as e:
                flash.error('Could not store agreement to GDPR terms')
            next = request.form.get('next')
            if next:
                return redirect(next)
            return redirect(url_for('index.index'))
        elif request.form.get('gdpr-options') == 'disagree':
            return redirect(url_for('settings.index',  path='delete'))
        else:
            flash.error('You must agree to or decline our terms')
            return render_template('index/gdpr.html', next=request.args.get('next'))


@index_bp.route('/search/', methods=['GET', 'OPTIONS'])
def search():
    search_term = request.args.get("search_term")
    user_id = current_user.id if current_user.is_authenticated else None
    if search_term:
        users = db_user.search(db_conn, search_term, SEARCH_USER_LIMIT, user_id)
    else:
        users = []
    return render_template("index/search-users.html", search_term=search_term, users=users)


@index_bp.route('/messybrainz/', methods=['GET', 'OPTIONS'])
def messybrainz():
    return render_template("index/messybrainz.html")


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
    user = db_user.get_by_mb_row_id(db_conn, musicbrainz_row_id)
    if user is None:
        raise NotFound('Could not find user with MusicBrainz Row ID: %d' % musicbrainz_row_id)
    delete_user(user['id'])
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
        user_count = db_user.get_user_count(db_conn)
        cache.set(user_count_key, int(user_count), CACHE_TIME, encode=False)
        return user_count


@index_bp.route("/similar-users/")
def similar_users():
    return redirect(url_for("explore.similar_users"))


@index_bp.route("/listens-offline/")
def listens_offline():
    """
        Show the "listenstore offline" message.
    """

    return render_template("index/listens_offline.html")


@index_bp.route("/musicbrainz-offline/")
def musicbrainz_offline():
    """ Show the "musicbrainz offline" message. """
    return render_template("index/musicbrainz-offline.html")


@index_bp.route("/huesound/")
def huesound():
    """ Redirect to /explore/huesound """

    return redirect(url_for("explore.huesound"))


@index_bp.route("/statistics/charts/")
def charts():
    """ Show the top sitewide entities. """
    return render_template("index/charts.html")


@index_bp.route("/statistics/")
def stats():
    """ Show sitewide stats """
    return render_template("index/stats.html")
