from flask import Blueprint, render_template, current_app
from flask_login import current_user, login_required
from listenbrainz import webserver
from listenbrainz.webserver.decorators import web_listenstore_needed
from listenbrainz.db.metadata import get_metadata_for_artist, get_metadata_for_release_group
from listenbrainz.webserver.views.api_tools import is_valid_uuid
from listenbrainz.db.popularity import get_top_entity_for_entity
import requests
from werkzeug.exceptions import BadRequest, NotFound
import orjson

artist_bp = Blueprint("artist", __name__)
album_bp = Blueprint("album", __name__)

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
        popular_recordings = list(r.json())[:10]

    # Fetch similar artists
    r = requests.post("https://labs.api.listenbrainz.org/similar-artists/json",
                  json=[{
                      'artist_mbid':
                      artist_mbid,
                      'algorithm':
                      "session_based_days_7500_session_300_contribution_5_threshold_10_limit_100_filter_True_skip_30"
                  }])

    if r.status_code != 200:
        raise RuntimeError(f"Cannot fetch similar artists: {r.status_code} ({r.text})")

    try:
        artists = r.json()[3]["data"][:15]
    except IndexError:
        artists = []


    top_releases = get_top_entity_for_entity("release", artist_mbid, "release")
    print(top_releases)

    props = {
        "artist_data": item,
        "popular_recordings": popular_recordings,
        "similar_artists": artists,
	    "listening_stats": {}, #for that artist,  # DO NOT IMPLEMENT RIGHT NOW. WAIT FOR PROPER CACHING
            # total plays for artist
            # total # of listeners for artist
            # top listeners (10)
	    "albums": []  #list of albums for that artist if possible with cover art info,
           # release group: name, release date, type, caa_id, caa_release_mbid, listen_counts
    }

    return render_template(
        "entities/artist.html",
        props=orjson.dumps(props).decode("utf-8")
    )


@album_bp.route("/<release_group_mbid>", methods=["GET"])
# TODO: unsure if this is needed
@web_listenstore_needed
def album_entity(release_group_mbid):
    """ Show an album page with all their relevant information """

    if not is_valid_uuid(release_group_mbid):
        raise BadRequest("Provided release group ID is invalid: %s" % release_group_mbid)

    # Fetch the artist cached data
    release_group_data = get_metadata_for_release_group([release_group_mbid])
    if len(release_group_data) == 0:
        raise NotFound(f"release group {release_group_mbid} not found in the metadata cache")

    item = {"release_group_mbid": release_group_data[0].release_group_mbid}
    item.update(**release_group_data[0].release_group_data)
    item["tag"] = release_group_data[0].tag_data

    props = {
        "release_group_data": item,
        "release_group_mbid": release_group_mbid
    }

    return render_template(
        "entities/album.html",
        props=orjson.dumps(props).decode("utf-8")
    )
