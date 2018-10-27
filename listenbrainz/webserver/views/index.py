
#TODO(param): alphabetize these
from brainzutils import cache
from flask import Blueprint, render_template, current_app, redirect, url_for, request, jsonify
from flask_login import current_user, login_required
from werkzeug.exceptions import Unauthorized, NotFound
from requests.exceptions import HTTPError
import os
import subprocess
import requests
import locale
import listenbrainz.db.user as db_user
from listenbrainz.db.exceptions import DatabaseException
from listenbrainz import webserver
from listenbrainz.webserver.influx_connection import _influx
from listenbrainz.webserver.views.user import delete_user
from influxdb.exceptions import InfluxDBClientError, InfluxDBServerError
import pika
import listenbrainz.webserver.rabbitmq_connection as rabbitmq_connection
import listenbrainz.webserver.redis_connection as redis_connection


index_bp = Blueprint('index', __name__)
locale.setlocale(locale.LC_ALL, '')

STATS_PREFIX = 'listenbrainz.stats'  # prefix used in key to cache stats
CACHE_TIME = 10 * 60  # time in seconds we cache the stats

@index_bp.route("/")
def index():

    # get total listen count
    try:
        listen_count = _influx.get_total_listen_count()
    except Exception as e:
        current_app.logger.error('Error while trying to get total listen count: %s', str(e))
        listen_count = None
    try:
        latest_listens = redis_connection._redis.get_latest_listens()
    except Exception as e:
        current_app.logger.error('Error while trying to get 10 latest listens: %s', str(e))
        latest_listens = None
    return render_template(
        "index/index.html",
        listen_count=listen_count,
        latest_listens=latest_listens
    )


@index_bp.route("/import")
def import_data():
    if current_user.is_authenticated():
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


@index_bp.route("/goals")
def goals():
    return render_template("index/goals.html")


@index_bp.route("/faq")
def faq():
    return render_template("index/faq.html")


@index_bp.route("/api-docs")
def api_docs():
    return render_template("index/api-docs.html")


@index_bp.route("/lastfm-proxy")
def proxy():
    return render_template("index/lastfm-proxy.html")


@index_bp.route("/roadmap")
def roadmap():
    return render_template("index/roadmap.html")


@index_bp.route("/current-status")
def current_status():

    load = "%.2f %.2f %.2f" % os.getloadavg()

    incoming_len = -1
    unique_len = -1
    try:
        with rabbitmq_connection._rabbitmq.acquire() as connection:
            queue = connection.channel.queue_declare(current_app.config['INCOMING_QUEUE'], durable=True)
            incoming_len = queue.method.message_count

            queue = connection.channel.queue_declare(current_app.config['UNIQUE_QUEUE'], durable=True)
            unique_len = queue.method.message_count

    except (pika.exceptions.ConnectionClosed, AttributeError):
        pass

    listen_count = _influx.get_total_listen_count()
    try:
        user_count = _get_user_count()
    except DatabaseException as e:
        user_count = None

    return render_template(
        "index/current-status.html",
        load=load,
        listen_count=format(int(listen_count), ",d"),
        incoming_len=format(int(incoming_len), ",d"),
        unique_len=format(int(unique_len), ",d"),
        user_count=format(int(user_count), ",d"),
    )


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
