from flask import Blueprint, request, jsonify
from listenbrainz.webserver import ts_conn
from listenbrainz.webserver.decorators import crossdomain
from listenbrainz.metadata_cache.internetarchive.store import search_ia_tracks

internet_archive_api_bp = Blueprint("internet_archive_api", __name__)

@internet_archive_api_bp.get("/search")
@crossdomain
def search_ia():
    artist = request.args.get("artist")
    track = request.args.get("track")
    album = request.args.get("album")

    if not artist and not track and not album:
        return jsonify({"results": []})

    results = search_ia_tracks(ts_conn, artist=artist, track=track, album=album)
    return jsonify({"results": results})
