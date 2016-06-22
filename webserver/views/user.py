from __future__ import absolute_import
from flask import Blueprint, render_template, request, url_for, Response
from flask_login import current_user, login_required
from werkzeug.exceptions import NotFound, BadRequest
from webserver.decorators import crossdomain
from datetime import datetime
import webserver
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
        base_url=url_for("api_v1.submit_listen", user_id=user_id, _external=True),
        user_token=user_token,
        lastfm_username=lastfm_username,
        user_id=user_id,
    )
    return Response(scraper, content_type="text/javascript")


@user_bp.route("/<user_id>")
def profile(user_id):
    # Which database to use to showing user listens.
    db_conn = webserver.create_postgres()

    # Getting data for current page
    max_ts = request.args.get("max_ts")
    if max_ts is not None:
        try:
            max_ts = int(float(max_ts))
        except ValueError:
            raise BadRequest("Incorrect timestamp argument to_id:" %
                             request.args.get("to_id"))
    listens = []
    for listen in db_conn.fetch_listens(user_id, limit=25, to_id=max_ts):
        listens.append({
            "track_metadata": listen.data,
            "listened_at": listen.timestamp,
            "listened_at_iso": datetime.fromtimestamp(int(listen.timestamp)).isoformat() + "Z",
        })

    if listens:
        # Checking if there is a "previous" page...
        previous_listens = list(db_conn.fetch_listens(user_id, limit=25, from_id=listens[0]["listened_at"]))
        if previous_listens:
            # Getting from the last item because `fetch_listens` returns in ascending
            # order when `from_id` is used.
            previous_listen_ts = previous_listens[-1].timestamp + 1
        else:
            previous_listen_ts = None

        # Checking if there is a "next" page...
        next_listens = list(db_conn.fetch_listens(user_id, limit=1, to_id=listens[-1]["listened_at"]))
        if next_listens:
            next_listen_ts = listens[-1]["listened_at"]
        else:
            next_listen_ts = None

    else:
        previous_listen_ts = None
        next_listen_ts = None

    return render_template(
        "user/profile.html",
        user=_get_user(user_id),
        listens=listens,
        previous_listen_ts=previous_listen_ts,
        next_listen_ts=next_listen_ts,
        spotify_uri=_get_spotify_uri_for_listens(listens)
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


def _get_spotify_uri_for_listens(listens):

    def get_track_id_from_listen(listen):
        additional_info = listen["track_metadata"]["additional_info"]
        if "spotify_id" in additional_info:
            return additional_info["spotify_id"].rsplit('/', 1)[-1]
        else:
            return None

    track_ids = [get_track_id_from_listen(l) for l in listens]
    track_ids = [t_id for t_id in track_ids if t_id]

    if track_ids:
        return "spotify:trackset:Recent listens:" + ",".join(track_ids)
    else:
        return None
