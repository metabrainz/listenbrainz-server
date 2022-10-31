from flask import Flask, render_template, Blueprint

art_bp = Blueprint('art_v1', __name__)

@art_bp.route("/")
def index():
    return render_template("art/index.html")
