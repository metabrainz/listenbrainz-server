from datetime import datetime

from flask import Blueprint, render_template, current_app, request
from flask_login import current_user, login_required
from werkzeug.exceptions import BadRequest
import ujson

from listenbrainz.webserver.views.playlist_api import serialize_jspf
from listenbrainz.db.model.playlist import WritablePlaylistRecording, WritablePlaylist
from listenbrainz.webserver.views.api_tools import is_valid_uuid
from listenbrainz.webserver.views.playlist_api import fetch_playlist_recording_metadata

player_bp = Blueprint("player", __name__)


@player_bp.route("/", methods=["POST"])
@login_required
def load():
    """This is the start of the BrainzPlayer concept where anyone (logged into LB) can post a playlist
        composed of an array of listens-formatted items and get returned a playable playlist page.
    """

    try:
        raw_listens = request.form['listens']
    except KeyError:
        return render_template(
            "index/player.html",
            error_msg="Missing form data key 'listens'"
        )

    try:
        listens = ujson.loads(raw_listens)
    except ValueError as e:
        return render_template(
            "index/player.html",
            error_msg="Could not parse JSON array. Error: %s" % e
        )

    if not isinstance(listens, list):
        return render_template(
            "index/player.html",
            error_msg="'listens' should be a stringified JSON array."
        )

    if len(listens) <= 0:
        return render_template(
            "index/player.html",
            error_msg="'Listens' array must have one or more items."
        )

    # `user` == `curent_user` since player isn't for a user but the recommendation component
    # it uses expects `user` and `current_user` as keys.
    props = {
        "user": {
            "id": current_user.id,
            "name": current_user.musicbrainz_id,
        },
        "recommendations": listens,
    }

    return render_template(
        "index/player.html",
        props=ujson.dumps(props),
        user=current_user
    )

@player_bp.route("/", methods=["GET"])
def load_instant():
    """
        This endpoint takes in a list of recording_mbids and then loads their metadata and creates
        a JSPF file from this data. 
    """

    recordings = request.args.get("recording_mbids", default=None)
    if recordings is None:
        raise BadRequest("recording_mbids argument must be present and contain a comma separated list of recording_mbids")

    recording_mbids = []
    for mbid in recordings.split(","):
        if not is_valid_uuid(mbid):
            raise BadRequest(f"Recording mbid {mbid} is not valid.")

        recording_mbids.append(mbid)

    desc = request.args.get("desc", default="")
    if not desc:
        desc = "Instant playlist"

    name = request.args.get("name", default="")
    if not name:
        name = "Instant playlist"

    now = datetime.now()
    playlist = WritablePlaylist(description=desc, name=name, creator="listenbrainz", creator_id=1, created=now)
    for i, mbid in enumerate(recording_mbids):
        rec = WritablePlaylistRecording(position=i, mbid=mbid, added_by_id=1, created=now)
        playlist.recordings.append(rec)

    fetch_playlist_recording_metadata(playlist)

    return render_template(
        "index/entity-pages/release-page.html",
        props=ujson.dumps(serialize_jspf(playlist))
    )
