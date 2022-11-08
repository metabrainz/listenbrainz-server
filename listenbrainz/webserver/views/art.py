from flask import Flask, render_template, Blueprint

art_bp = Blueprint('art', __name__)

@art_bp.route("/", subdomain="art")
def index():
    """ This page shows of a bit of what can be done with the cover art, as a sort of showcase. """
    return render_template("art/index.html")
