
#TODO(param): alphabetize these
from flask import Blueprint, render_template, current_app, redirect, url_for
from flask_login import current_user
from listenbrainz.webserver.redis_connection import _redis
import os
import subprocess
import locale
import listenbrainz.db.user as db_user
from listenbrainz.db.exceptions import DatabaseException
from listenbrainz import webserver
from listenbrainz.webserver.influx_connection import _influx
from influxdb.exceptions import InfluxDBClientError, InfluxDBServerError
import pika
import listenbrainz.webserver.rabbitmq_connection as rabbitmq_connection


index_bp = Blueprint('index', __name__)
locale.setlocale(locale.LC_ALL, '')

STATS_PREFIX = 'listenbrainz.stats' # prefix used in key to cache stats
CACHE_TIME = 10 * 60 # time in seconds we cache the stats

@index_bp.route("/")
def index():

    # get total listen count
    try:
        listen_count = _influx.get_total_listen_count()
    except Exception as e:
        current_app.logger.error('Error while trying to get total listen count: %s', str(e))
        listen_count = None


    return render_template(
        "index/index.html",
        listen_count=listen_count,
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
            incoming_ch = connection.channel()
            queue = incoming_ch.queue_declare(current_app.config['INCOMING_QUEUE'], durable=True)
            incoming_len = queue.method.message_count

            unique_ch = connection.channel()
            queue = unique_ch.queue_declare(current_app.config['UNIQUE_QUEUE'], durable=True)
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


def _get_user_count():
    """ Gets user count from either the redis cache or from the database.
        If not present in the cache, it makes a query to the db and stores the
        result in the cache for 10 minutes.
    """
    redis_connection = _redis.redis
    user_count_key = "{}.{}".format(STATS_PREFIX, 'user_count')
    if redis_connection.exists(user_count_key):
        return redis_connection.get(user_count_key)
    else:
        try:
            user_count = db_user.get_user_count()
        except DatabaseException as e:
            raise
        redis_connection.setex(user_count_key, user_count, CACHE_TIME)
        return user_count
