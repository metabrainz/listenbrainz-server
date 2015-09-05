from __future__ import absolute_import
from flask import Blueprint, render_template

index_bp = Blueprint('index', __name__)

@index_bp.route("/")
def index():
    return render_template("index/index.html")

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
