import ujson
from werkzeug.exceptions import NotFound, BadRequest

from flask import Blueprint, render_template, current_app, request
from flask_login import current_user, login_required
from listenbrainz.domain import spotify
from listenbrainz.webserver.views.api_tools import is_valid_uuid
from listenbrainz.webserver.views.playlist_api import serialize_jspf
import listenbrainz.db.playlist as db_playlist
import listenbrainz.db.user as db_user

playlist_bp = Blueprint("playlist", __name__)


@playlist_bp.route("/<playlist_mbid>", methods=["GET"])

def load_playlist(playlist_mbid: str):
    """Load a single playlist by id
    """
    if not is_valid_uuid(playlist_mbid):
        raise BadRequest("Provided playlist ID is invalid: %s" % playlist_mbid)

    playlist = db_playlist.get_by_mbid(playlist_mbid, True)
    if playlist is None or \
        (playlist.creator_id != current_user.get_id() and not playlist.public):
        raise NotFound("Cannot find playlist: %s" % playlist_mbid)

    spotify_data = {}
    current_user_data = {}
    if current_user.is_authenticated:
        spotify_data = spotify.get_user_dict(current_user.id)

        current_user_data = {
                "id": current_user.id,
                "name": current_user.musicbrainz_id,
                "auth_token": current_user.auth_token,
        }
    playlist_user = db_user.get(playlist.creator_id)
    props = {
        "current_user": current_user_data,
        "spotify": spotify_data,
        "api_url": current_app.config["API_URL"],
        "playlist": serialize_jspf(playlist, playlist_user)
    }

    return render_template(
        "playlists/playlist.html",
        props=ujson.dumps(props)
    )
