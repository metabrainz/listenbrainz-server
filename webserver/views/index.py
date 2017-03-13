from __future__ import absolute_import
from flask import Blueprint, render_template, current_app, redirect, url_for
from flask_login import current_user
from webserver.redis_connection import _redis
from redis_pubsub import RedisPubSubPublisher
import os
import subprocess
import locale
import db.user
from db.exceptions import DatabaseException
import webserver
from influxdb.exceptions import InfluxDBClientError, InfluxDBServerError

index_bp = Blueprint('index', __name__)
locale.setlocale(locale.LC_ALL, '')

STATS_PREFIX = 'listenbrainz.stats' # prefix used in key to cache stats
CACHE_TIME = 10 * 60 # time in seconds we cache the stats

@index_bp.route("/")
def index():
    return render_template("index/index.html")


@index_bp.route("/import")
def import_data():
    if current_user.is_authenticated():
        return redirect(url_for("user.import_data"))
    else:
        return current_app.login_manager.unauthorized()


@index_bp.route("/download")
def downloads():
    return render_template("index/downloads.html")


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


@index_bp.route("/roadmap")
def roadmap():
    return render_template("index/roadmap.html")


@index_bp.route("/current-status")
def current_status():

    load = "%.2f %.2f %.2f" % os.getloadavg()

    stats = []
    pubsub = RedisPubSubPublisher(_redis.redis, "ilisten")
    stats_dict = pubsub.get_stats()
    stats.append({ 'data' : stats_dict, 'desc' : "Incoming listens" })
    pubsub = RedisPubSubPublisher(_redis.redis, "ulisten")
    stats_dict = pubsub.get_stats()
    stats.append({ 'data' : stats_dict, 'desc' : "Unique listens" })

    try:
        user_count = _get_user_count()
    except DatabaseException as e:
        user_count = None

    db_conn = webserver.influx_connection._influx
    try:
        listen_count = db_conn.get_total_listen_count()
    except (InfluxDBServerError, InfluxDBClientError):
        listen_count = None

    return render_template(
        "index/current-status.html",
        load=load,
        stats=stats,
        user_count=user_count,
        listen_count=listen_count,
        alpha_importer_size=_get_alpha_importer_queue_size(),
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
            user_count = db.user.get_user_count()
        except DatabaseException as e:
            raise
        redis_connection.setex(user_count_key, user_count, CACHE_TIME)
        return user_count

def _get_alpha_importer_queue_size():
    """ Returns the number of people in queue for an import from LB alpha
    """
    redis_connection = _redis.redis
    alpha_importer_size_key = "{}.{}".format(STATS_PREFIX, "alpha_importer_queue_size")
    if redis_connection.exists(alpha_importer_size_key):
        return redis_connection.get(alpha_importer_size_key)
    else:
        count = redis_connection.llen(current_app.config['IMPORTER_QUEUE_KEY'])
        count = 0 if not count else count
        redis_connection.setex(alpha_importer_size_key, count, CACHE_TIME)
        return count
