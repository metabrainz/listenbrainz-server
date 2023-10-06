from flask import Blueprint, render_template, current_app
from flask_login import current_user, login_required
from listenbrainz import webserver
from listenbrainz.webserver.decorators import web_listenstore_needed
from listenbrainz.db.metadata import get_metadata_for_artist
from listenbrainz.webserver.views.api_tools import is_valid_uuid
import requests
from werkzeug.exceptions import BadRequest, NotFound
import orjson

artist_bp = Blueprint("artist", __name__)

@artist_bp.route("/<artist_mbid>", methods=["GET"])
# TODO: unsure if this is needed
@web_listenstore_needed
def artist_entity(artist_mbid):
    """ Show a artist page with all their relevant information """

    if not is_valid_uuid(artist_mbid):
        raise BadRequest("Provided artist ID is invalid: %s" % artist_mbid)

    # Fetch the artist cached data
    artist_data = get_metadata_for_artist([artist_mbid])
    if len(artist_data) == 0:
        raise NotFound(f"artist {artist_mbid} not found in the metadata cache")

    item = {"artist_mbid": artist_data[0].artist_mbid}
    item.update(**artist_data[0].artist_data)
    item["tag"] = artist_data[0].tag_data

    # Fetch top recordings for artist
    r = requests.post("https://datasets.listenbrainz.org/popular-recordings/json?count=15", json=[{"[artist_mbid]": artist_mbid}])
    if r.status_code != 200:
        popular_recordings = []
    else:
        popular_recordings = list(r.json())

    props = {
        "artist_data": item,
        "popular_recordings": popular_recordings
    }

    return render_template(
        "entities/artist.html",
        props=orjson.dumps(props).decode("utf-8")
    )
