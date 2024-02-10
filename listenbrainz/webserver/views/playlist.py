import orjson
from werkzeug.exceptions import NotFound, BadRequest

from flask import Blueprint, render_template, jsonify
from flask_login import current_user

from listenbrainz.webserver import ts_conn, db_conn
from listenbrainz.webserver.decorators import web_listenstore_needed
from listenbrainz.webserver.views.api_tools import is_valid_uuid
from listenbrainz.webserver.views.playlist_api import fetch_playlist_recording_metadata
import listenbrainz.db.playlist as db_playlist

playlist_bp = Blueprint("playlist", __name__)


@playlist_bp.route("/",  defaults={'path': ''})
@playlist_bp.route('/<path:path>/')
def playlist_page(path):
    return render_template("index.html")


@playlist_bp.route("/<playlist_mbid>/", methods=["POST"])
@web_listenstore_needed
def load_playlist(playlist_mbid: str):
    """Load a single playlist by id
    """
    if not is_valid_uuid(playlist_mbid):
        return jsonify({"error": "Provided playlist ID is invalid: %s" % playlist_mbid}), 400

    current_user_id = None
    if current_user.is_authenticated:
        current_user_id = current_user.id

    playlist = db_playlist.get_by_mbid(db_conn, ts_conn, playlist_mbid, True)
    if playlist is None or not playlist.is_visible_by(current_user_id):
        return jsonify({"error": "Cannot find playlist: %s" % playlist_mbid}), 404

    fetch_playlist_recording_metadata(playlist)

    return jsonify({
        "playlist": playlist.serialize_jspf(),
    })
