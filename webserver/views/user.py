from __future__ import absolute_import
from flask import Blueprint, render_template, request, url_for, Response
from flask_login import current_user
from werkzeug.exceptions import NotFound
from webserver.decorators import crossdomain
import db.user

user_bp = Blueprint("user", __name__)


@user_bp.route("/<user_id>/scraper.js")
@crossdomain()
def lastfmscraper(user_id):
    user_token = request.args.get("user_token")
    lastfm_username = request.args.get("lastfm_username")
    if user_token is None or lastfm_username is None:
        raise NotFound
    scraper = render_template(
        "user/scraper.js",
        base_url=url_for("1.submit_listen", user_id=user_id, _external=True),
        user_token=user_token,
        lastfm_username=lastfm_username,
    )
    return Response(scraper, content_type="text/javascript")


@user_bp.route("/<user_id>")
def profile(user_id):
    return render_template("user/profile.html", user=_get_user(user_id))


@user_bp.route("/<user_id>/import")
def import_data(user_id):
    user = _get_user(user_id)
    lastfm_username = request.args.get("lastfm_username")

    if lastfm_username:
        loader = render_template(
            "user/loader.js",
            base_url=url_for("user.lastfmscraper", user_id=user_id, _external=True),
            user_token=user.auth_token,
            lastfm_username=lastfm_username,
        )
        loader = "javascript:%s" % loader
    else:
        loader = None

    return render_template("user/import.html", user=user, loader=loader,
                           lastfm_username=lastfm_username)


def _get_user(user_id):
    if current_user.is_authenticated() and \
       current_user.musicbrainz_id == user_id:
        return current_user
    else:
        user = db.user.get_by_mb_id(user_id)
        if user is None:
            raise NotFound("Can't find this user.")
        return user
