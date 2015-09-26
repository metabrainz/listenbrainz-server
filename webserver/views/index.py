from __future__ import absolute_import
from flask import Blueprint, render_template, current_app, redirect, url_for
from flask_login import current_user
import os
import config
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


@index_bp.route("/roadmap")
def roadmap():
    return render_template("index/roadmap.html")


@index_bp.route("/current-status")
def current_status():

    load = "%.2f %.2f %.2f" % os.getloadavg()

    process = subprocess.Popen([config.KAFKA_RUN_CLASS_BINARY, "kafka.tools.ConsumerOffsetChecker",
        '--topic', 'listens', '--group', 'listen-group'], stdout=subprocess.PIPE)
    out, err = process.communicate()

    print out

    lines = out.split("\n")
    data = []
    for line in lines:
        if line.startswith("listen-group"):
            data = line.split()

    if len(data) >= 6:
        kafka_stats = { 
                        'offset' : locale.format("%d", int(data[3]), grouping=True),
                        'size' : locale.format("%d", int(data[4]), grouping=True),
                        'lag' : locale.format("%d", int(data[5]), grouping=True) 
                      } 
    else:
        kafka_stats = { 'offset' : "(unknown/empty)", 'size' : "-", 'lag' : "-" } 

    return render_template("index/current-status.html", load=load, kstats=kafka_stats)
