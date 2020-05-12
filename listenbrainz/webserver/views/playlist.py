import uuid
import ujson
from werkzeug.exceptions import BadRequest
from flask import Blueprint, render_template, current_app, request
from flask_login import current_user, login_required
from listenbrainz.domain import spotify
from brainzutils.musicbrainz_db import recording as mb_rec
from brainzutils.musicbrainz_db.exceptions import NoDataFoundException

playlist_bp = Blueprint("playlist", __name__)


@playlist_bp.route("/", methods=["POST"])
@login_required

def load():
    """
        This is the start of the BrainzPlayer concept where anyone (logged into LB) can post playlist
        composed of recording MBIDs and have the player attempt to make the list playable.
    """

    raw_data = request.get_data()
    try:
        data = ujson.loads(raw_data.decode("utf-8"))
    except ValueError as e:
        return render_template(
            "index/playlist.html",
            error_msg="Cannot parse JSON document: %s" % e
        )

    if not isinstance(data, list):
        return render_template(
                "index/playlist.html",
                error_msg="submitted data must be a list"
            )


    user_data = {
        "id": current_user.id,
        "name": current_user.musicbrainz_id,
        "auth_token": current_user.auth_token,
    }
    spotify_data = spotify.get_user_dict(current_user.id)
    props = {
        "user": user_data,
        "spotify": spotify_data,
        "api_url": current_app.config["API_URL"],
        "listens" : data,
        # "metadata" : metadata
    }

    return render_template(
        "index/playlist.html",
        props=ujson.dumps(props),
        user=current_user,
        spotify_data=spotify_data,
        absolute_urls= True
    )