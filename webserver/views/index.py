from __future__ import absolute_import
from flask import Blueprint, render_template, current_app, redirect, url_for
from flask_login import current_user

index_bp = Blueprint('index', __name__)


@index_bp.route("/")
def index():
    return render_template("index/index.html")


@index_bp.route("/import")
def import_data():
    if current_user.is_authenticated():
        return redirect(url_for("user.import_data", user_id=current_user.musicbrainz_id))
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
