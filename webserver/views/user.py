from __future__ import absolute_import
from flask import Blueprint, render_template, request, url_for, Response
from flask_login import current_user
from werkzeug.exceptions import NotFound
from webserver.decorators import crossdomain
import db.user

user_bp = Blueprint("user", __name__)

@user_bp.route("/lastfmscraper/<musicbrainz_id>.js")
@crossdomain()
def lastfmscraper(musicbrainz_id):
    user_token = request.args.get("user_token")
    lastfm_username = request.args.get("lastfm_username")
    if user_token is None or lastfm_username is None:
        raise NotFound
    params = {"base_url": url_for("listen.submit_listen", user_id=musicbrainz_id, _external=True),
            "user_token": user_token,
            "lastfm_username": lastfm_username}
    scraper = render_template("user/scraper.js", **params)
    return Response(scraper, content_type="text/javascript")


@user_bp.route("/<musicbrainz_id>")
def profile(musicbrainz_id):

    lastfm_username = request.args.get("lastfm_username")
    if current_user.is_authenticated() and \
       current_user.musicbrainz_id == musicbrainz_id:
        user = current_user
    else:
        user = db.user.get_by_mb_id(musicbrainz_id)
        if user is None:
            raise NotFound("Can't find this user.")
        datasets = db.dataset.get_by_user_id(user["id"])

    if lastfm_username:
        params = {"base_url": url_for("user.lastfmscraper", musicbrainz_id=musicbrainz_id, _external=True),
                "user_token": user.auth_token,
                "lastfm_username": lastfm_username}
        loader = render_template("user/loader.js", **params)
        loader = "javascript:%s" % loader
    else:
        loader = None

    return render_template("user/profile.html", user=user, loader=loader)
