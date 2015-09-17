from __future__ import absolute_import
from flask import Blueprint, render_template, request, url_for, Response
from flask_login import current_user, login_required
from werkzeug.exceptions import NotFound, BadRequest
from webserver.decorators import crossdomain
import webserver
import db.user

user_bp = Blueprint("user", __name__)


@user_bp.route("/lastfmscraper/<user_id>.js")
@crossdomain()
def lastfmscraper(user_id):
    user_token = request.args.get("user_token")
    lastfm_username = request.args.get("lastfm_username")
    if user_token is None or lastfm_username is None:
        raise NotFound
    scraper = render_template(
        "user/scraper.js",
        base_url=url_for("listen.submit_listen", user_id=user_id, _external=True),
        user_token=user_token,
        lastfm_username=lastfm_username,
    )
    return Response(scraper, content_type="text/javascript")


@user_bp.route("/<user_id>")
def profile(user_id):
    cassandra = webserver.create_cassandra()

    # Getting data for current page
    min_ts = request.args.get("min_ts")
    if min_ts is not None:
        try:
            min_ts = int(min_ts)
        except ValueError:
            raise BadRequest("Incorrect timestamp argument min-ts:" %
                             request.args.get("min_ts"))
    listens = []
    for listen in cassandra.fetch_listens(user_id, limit=25, to_id=min_ts):
        listens.append({
            "track_metadata": listen.data,
            "listened_at": listen.timestamp,
        })

    # Checking if there is a "previous" page
    previous_listens = list(cassandra.fetch_listens(user_id, limit=25, from_id=listens[0]["listened_at"] + 1, order="asc"))
    print(listens[0]["listened_at"] + 1)
    if previous_listens:
        previous_listen_ts = previous_listens[-1].timestamp
    else:
        previous_listen_ts = None

    # Checking if there is a "next" page
    next_listens = list(cassandra.fetch_listens(user_id, limit=1, to_id=listens[-1]["listened_at"] - 1))
    if next_listens:
        next_listen_ts = listens[-1]["listened_at"] - 1
    else:
        next_listen_ts = None

    return render_template(
        "user/profile.html",
        user=_get_user(user_id),
        listens=listens,
        previous_listen_ts=previous_listen_ts,
        next_listen_ts=next_listen_ts,
    )


@user_bp.route("/import")
@login_required
def import_data():
    lastfm_username = request.args.get("lastfm_username")
    if lastfm_username:
        loader = render_template(
            "user/loader.js",
            base_url=url_for("user.lastfmscraper",
                             user_id=current_user.musicbrainz_id,
                             _external=True),
            user_token=current_user.auth_token,
            lastfm_username=lastfm_username,
        )
        loader = "javascript:%s" % loader
    else:
        loader = None
    return render_template("user/import.html", user=current_user, loader=loader,
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
