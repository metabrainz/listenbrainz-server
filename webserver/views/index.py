from __future__ import absolute_import
from flask import Blueprint, render_template
from db.stats import get_last_submitted_recordings, get_stats

index_bp = Blueprint('index', __name__)


@index_bp.route("/")
def index():
    stats, last_collected = get_stats()
    return render_template("index/index.html", stats=stats, last_collected=last_collected,
                           last_submitted_data=get_last_submitted_recordings())


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
