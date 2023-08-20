from flask import Blueprint, render_template, current_app, request
from flask_login import current_user
import orjson
from werkzeug.exceptions import NotFound, BadRequest

from listenbrainz.db.similar_users import get_top_similar_users

explore_bp = Blueprint('explore', __name__)


@explore_bp.route("/")
def index():
    """ Main explore page for users to browse the various explore features """

    return render_template(
        "explore/index.html",
        props=orjson.dumps({}).decode("utf-8")
    )


@explore_bp.route("/huesound/")
def huesound():
    """ Hue Sound browse music by color of cover art """

    return render_template(
        "explore/huesound.html",
        props=orjson.dumps({}).decode("utf-8")
    )


@explore_bp.route("/similar-users/")
def similar_users():
    """ Show all of the users with the highest similarity in order to make
        them visible to all of our users. This view can show bugs in the algorithm
        and spammers as well.
    """

    similar_users = get_top_similar_users()
    return render_template(
        "explore/similar-users.html",
        similar_users=similar_users
    )


@explore_bp.route("/fresh-releases/")
def fresh_releases():
    """ Explore fresh releases """

    return render_template(
        "explore/fresh-releases.html",
        props=orjson.dumps({}).decode("utf-8")
    )

@explore_bp.route("/art-creator/")
def art_creator():

    return render_template(
        "explore/stats-art-designer.html",
        props=orjson.dumps({}).decode("utf-8")
    )

@explore_bp.route("/cover-art-collage/")
@explore_bp.route("/cover-art-collage/<int:year>/")
def cover_art_collage(year: int = 2022):
    """ A collage of album covers from 2022
        Raises:
            NotFound if the there is no collage for the year
    """
    if year != 2022:
        raise NotFound(f"Cannot find Coveer Art Collage for year: {year}")

    return render_template(
        "explore/cover-art-collage.html"
    )

@explore_bp.route("/ai-brainz/")
def ai_brainz():
    """ Explore your love of Rick """

    return render_template("explore/ai-brainz.html")

@explore_bp.route("/lb-radio/")
def lb_radio():
    """ LB Radio view

        Possible page arguments:
           mode: string, must be easy, medium or hard.
           prompt: string, the prompt for playlist generation.
    """

    mode = request.args.get("mode", "")
    if mode != "" and mode not in ("easy", "medium", "hard"):
        raise BadRequest("mode parameter is required and must be one of 'easy', 'medium' or 'hard'")

    prompt = request.args.get("prompt", "")
    if prompt != "" and prompt == "":
        raise BadRequest("prompt parameter is required and must be non-zero length.")

    if current_user.is_authenticated:
        user = current_user.musicbrainz_id
        token = current_user.auth_token
    else:
        user = ""
        token = ""
    props = {
        "mode": mode,
        "prompt": prompt,
        "user": user,
        "token": token
    }

    return render_template("explore/lb-radio.html", props=orjson.dumps(props).decode("utf-8"))
