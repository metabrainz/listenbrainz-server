import ujson
from werkzeug.exceptions import BadRequest
from flask import Blueprint, render_template, current_app, request
from flask_login import current_user, login_required
from listenbrainz.domain import spotify

player_bp = Blueprint("player", __name__)


@player_bp.route("/", methods=["POST"])
@login_required

def load():
    """This is the start of the BrainzPlayer concept where anyone (logged into LB) can post a playlist
        composed of an array of listens-formatted items and get returned a playable playlist page.
    """

    try:
        raw_listens = request.form['listens']
    except KeyError:
        return render_template(
            "index/player.html",
            error_msg="Missing form data key 'listens'"
        )

    try:
        listens = ujson.loads(raw_listens)
    except ValueError as e:
        return render_template(
            "index/player.html",
            error_msg="Could not parse JSON array. Error: %s" % e
        )

    if not isinstance(listens, list):
        return render_template(
            "index/player.html",
            error_msg="'listens' should be a stringified JSON array."
        )

    if len(listens) <= 0:
        return render_template(
            "index/player.html",
            error_msg="'Listens' array must have one or more items."
        )

    current_user_data = {
        "id": current_user.id,
        "name": current_user.musicbrainz_id,
        "auth_token": current_user.auth_token,
    }
    spotify_data = spotify.get_user_dict(current_user.id)
    # `user` == `curent_user` since player isn't for a user but the recommendation component
    # it uses expects `user` and `current_user` as keys.
    props = {
        "user": {
            "id": current_user.id,
            "name": current_user.musicbrainz_id,
        },
        "current_user": current_user_data,
        "spotify": spotify_data,
        "api_url": current_app.config["API_URL"],
        "recommendations": listens,
        "sentry_dsn": current_app.config.get("LOG_SENTRY", {}).get("dsn")
    }

    return render_template(
        "index/player.html",
        props=ujson.dumps(props),
        user=current_user
    )
