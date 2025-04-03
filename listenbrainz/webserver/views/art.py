from flask import render_template, Blueprint, current_app

art_bp = Blueprint('art', __name__)


@art_bp.get("/")
def index():
    """ This page shows of a bit of what can be done with the cover art, as a sort of showcase. """
    return render_template("art/index.html", api_url=current_app.config["API_URL"])
