from flask import Blueprint, render_template, current_app
import ujson

from listenbrainz.db.similar_users import get_top_similar_users

explore_bp = Blueprint('explore', __name__)


@explore_bp.route("/huesound/")
def huesound():
    """ Hue Sound browse music by color of cover art """

    return render_template(
        "explore/huesound.html",
        props=ujson.dumps({})
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
        props=ujson.dumps({})
    )

@explore_bp.route("/cover-art-collage/")
def cover_art_collage():
    """ A collage of album covers from 2022 """

    return render_template(
        "explore/cover-art-collage.html"
    )