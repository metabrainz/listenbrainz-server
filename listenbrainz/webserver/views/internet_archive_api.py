from flask import Blueprint, request, jsonify
from listenbrainz.webserver import ts_conn
from listenbrainz.metadata_cache.internetarchive.store import search_ia_tracks

internet_archive_api_bp = Blueprint('internet_archive_api', __name__)

@internet_archive_api_bp.route('/internet_archive/search', methods=['GET'])
def search_ia():
    artist = request.args.get('artist')
    track = request.args.get('track')
    album = request.args.get('album')

    results = search_ia_tracks(ts_conn, artist=artist, track=track, album=album)
    return jsonify({'results': results})

