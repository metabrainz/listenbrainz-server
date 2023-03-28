from flask import Blueprint, render_template, current_app
import orjson
from werkzeug.exceptions import NotFound

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
