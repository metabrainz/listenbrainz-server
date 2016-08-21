from __future__ import absolute_import
from flask import Blueprint, render_template, current_app, redirect, url_for
from flask_login import current_user
from webserver.redis_connection import _redis
from redis_keys import REDIS_LISTEN_NEXTID, REDIS_LISTEN_CONSUMERS, REDIS_LISTEN_JSON, \
    REDIS_LISTEN_JSON_REFCOUNT, REDIS_LISTEN_CONSUMER_IDS
import os
import subprocess
import locale

index_bp = Blueprint('index', __name__)
locale.setlocale(locale.LC_ALL, '')

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
    consumers = _redis.redis.smembers(REDIS_LISTEN_CONSUMERS)
    listens = len(_redis.redis.keys(REDIS_LISTEN_JSON + "*"))
    listen_refcounts = len(_redis.redis.keys(REDIS_LISTEN_JSON_REFCOUNT + "*"))
    listen_ids = []
    for consumer in consumers:
        listen_ids.append("%s: %d" % (consumer, _redis.redis.llen(REDIS_LISTEN_CONSUMER_IDS + consumer)))

    return render_template("index/current-status.html", 
                           load=load, 
                           consumers=len(consumers),
                           listens=listens, 
                           listen_refcounts=listen_refcounts,
                           listen_ids=", ".join(listen_ids))
