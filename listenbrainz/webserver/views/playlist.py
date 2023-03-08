import orjson
from werkzeug.exceptions import NotFound, BadRequest

from flask import Blueprint, render_template, current_app
from flask_login import current_user
from listenbrainz.webserver.decorators import web_listenstore_needed
from listenbrainz.webserver.views.api_tools import is_valid_uuid
from listenbrainz.webserver.views.playlist_api import serialize_jspf, fetch_playlist_recording_metadata
import listenbrainz.db.playlist as db_playlist

playlist_bp = Blueprint("playlist", __name__)


@playlist_bp.route("/<playlist_mbid>/", methods=["GET"])
@web_listenstore_needed
def load_playlist(playlist_mbid: str):
    """Load a single playlist by id
    """
    if not is_valid_uuid(playlist_mbid):
        raise BadRequest("Provided playlist ID is invalid: %s" % playlist_mbid)

    current_user_id = None
    if current_user.is_authenticated:
        current_user_id = current_user.id

    playlist = db_playlist.get_by_mbid(playlist_mbid, True)
    if playlist is None or not playlist.is_visible_by(current_user_id):
        raise NotFound("Cannot find playlist: %s" % playlist_mbid)

    fetch_playlist_recording_metadata(playlist)

    props = {
        "labs_api_url": current_app.config["LISTENBRAINZ_LABS_API_URL"],
        "playlist": serialize_jspf(playlist),
    }

    return render_template(
        "playlists/playlist.html",
        props=orjson.dumps(props).decode("utf-8")
    )
