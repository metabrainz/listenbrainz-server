from flask import Blueprint, render_template, current_app
from flask_login import current_user, login_required
from listenbrainz import webserver
from listenbrainz.webserver.decorators import web_listenstore_needed
import orjson

metadata_viewer_bp = Blueprint("metadata_viewer", __name__)


@metadata_viewer_bp.route("/", methods=["GET"])
@web_listenstore_needed
@login_required
def playing_now_metadata_viewer():
    """ Show a page with details of the currently playing listen """

    # Which database to use to show playing_now stream.
    playing_now_conn = webserver.redis_connection._redis

    # Get the now_playing listen for this user
    playing_now = playing_now_conn.get_playing_now(current_user.id)
    if playing_now is not None:
        playing_now = playing_now.to_api()

    # TODO: Load initial recording metadata for playing_now listen
    # and add to props as 'metadata'

    props = {
        "playing_now": playing_now
    }

    return render_template(
        "player/metadata-viewer.html",
        props=orjson.dumps(props).decode("utf-8")
    )
