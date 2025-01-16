from flask import Blueprint, current_app, render_template, jsonify
from flask_login import current_user

from listenbrainz.webserver import ts_conn, db_conn
from listenbrainz.webserver.decorators import web_listenstore_needed
from listenbrainz.webserver.views.api_tools import is_valid_uuid
from listenbrainz.webserver.views.playlist_api import fetch_playlist_recording_metadata
import listenbrainz.db.playlist as db_playlist

playlist_bp = Blueprint("playlist", __name__)



@playlist_bp.get("/",  defaults={'playlist_mbid': ''})
@playlist_bp.get('/<playlist_mbid>/')
def playlist_page(playlist_mbid: str):
    current_user_id = None
    og_meta_tags = None

    if current_user.is_authenticated:
        current_user_id = current_user.id

    if is_valid_uuid(playlist_mbid):
        playlist = db_playlist.get_by_mbid(db_conn, ts_conn, playlist_mbid, False)
        if playlist is not None and playlist.is_visible_by(current_user_id):
            recordings_count = db_playlist.get_recordings_count_for_playlist(ts_conn, playlist.id)
            og_meta_tags = {
                "title": f'{playlist.name} — Playlist on ListenBrainz',
                "description": f'Playlist by {playlist.creator} — {recordings_count} track{"s" if recordings_count > 1 else ""} — ListenBrainz',
                "type": "music:playlist",
                "url": f'{current_app.config["SERVER_ROOT_URL"]}/playlist/{playlist_mbid}',
                "music:creator": f'{current_app.config["SERVER_ROOT_URL"]}/user/{playlist.creator}',
                # "image": Once we have playlist images we can try adding it here
            }
    return render_template("index.html", og_meta_tags=og_meta_tags)


@playlist_bp.post("/<playlist_mbid>/")
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
