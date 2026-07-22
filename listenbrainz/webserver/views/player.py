from datetime import datetime

import psycopg2
from flask import Blueprint, render_template, request, current_app, jsonify
from flask_login import current_user, login_required
from werkzeug.exceptions import BadRequest, NotFound
import orjson

from brainzutils.musicbrainz_db import engine as mb_engine
from brainzutils.musicbrainz_db.release import get_release_by_mbid

from listenbrainz.db.cover_art import get_caa_ids_for_release_mbids
from listenbrainz.db.model.playlist import WritablePlaylistRecording, WritablePlaylist
from listenbrainz.webserver.views.api_tools import is_valid_uuid
from listenbrainz.webserver.views.playlist_api import fetch_playlist_recording_metadata

player_bp = Blueprint("player", __name__)


@player_bp.post("/")
def load_instant():
    """
    Create an instant JSPF playlist from a list of recording MBIDs.

    This endpoint accepts a comma-separated list of recording MBIDs as a query
    parameter, fetches their metadata, and returns a JSPF playlist suitable for
    immediate playback. All parameters are passed as query string arguments.

    The response is a JSON object containing a JSPF playlist with track entries
    for each valid recording MBID.

    .. note::
        We recommend that you do not send more than 50 recording_mbids in one request -- our
        server infrastructure will likely give you a gateway error (502) if you do.

    :param recording_mbids: A comma separated list of recording MBIDs (query string).
    :type recording_mbids: ``str``
    :param desc: A description for this instant playlist (optional, defaults to "Instant playlist").
    :type desc: ``str``
    :param name: A name for this instant playlist (optional, defaults to "Instant playlist").
    :type name: ``str``
    :statuscode 200: playlist generated, returns JSPF.
    :statuscode 400: ``recording_mbids`` parameter is missing or contains an invalid UUID.
    :resheader Content-Type: *application/json*
    """

    recordings = request.args.get("recording_mbids", default=None)
    if recordings is None:
        raise BadRequest("recording_mbids argument must be present and contain a comma separated list of recording_mbids")

    recording_mbids = []
    for mbid in recordings.split(","):
        mbid_clean = mbid.strip()
        if not is_valid_uuid(mbid_clean):
            raise BadRequest(f"Recording mbid {mbid} is not valid.")

        recording_mbids.append(mbid_clean)

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

    return jsonify({"playlist": playlist.serialize_jspf()})


@player_bp.post("/release/<release_mbid>/")
def load_release(release_mbid):
    """
    Create a JSPF playlist from all tracks on a MusicBrainz release.

    Given a release MBID, this endpoint looks up the release in MusicBrainz,
    retrieves all tracks across all media, and returns them as a JSPF playlist.
    Cover art information is included when available.

    :param release_mbid: A valid MusicBrainz release MBID (URL path parameter).
    :type release_mbid: ``str``
    :statuscode 200: playlist generated, returns JSPF.
    :statuscode 400: the provided ``release_mbid`` is not a valid UUID.
    :statuscode 404: the release was not found in the MusicBrainz database.
    :resheader Content-Type: *application/json*
    """

    release_mbid = release_mbid.strip()
    if not is_valid_uuid(release_mbid):
        raise BadRequest(f"Release mbid {release_mbid} is not valid.")

    playlist = None
    if mb_engine:
        release = get_release_by_mbid(release_mbid, includes=["media", "artists"])
        if not release:
            return jsonify({"error": "This release was not found in our database. \
                            It may not have replicated to this server yet."}), 404

        with psycopg2.connect(current_app.config["MB_DATABASE_URI"]) as conn, \
                conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as curs:
            cover = get_caa_ids_for_release_mbids(curs, [release_mbid])[release_mbid]

        name = "Release %s by %s" % (release["name"], release["artist-credit-phrase"])
        desc = 'Release <a href="https://musicbrainz.org/release/%s">%s</a> by %s' % (release["mbid"],
                                                                                      release["name"],
                                                                                      release["artist-credit-phrase"])
        now = datetime.now()
        playlist = WritablePlaylist(description=desc, name=name, creator="listenbrainz", creator_id=1, created=now)

        if release.get("medium-list"):
            for medium in release["medium-list"]:
                if not medium.get("track-list"):
                    continue

                for recording in medium.get("track-list", []):
                    rec = WritablePlaylistRecording(
                        title=recording["name"],
                        artist_credit=recording["artist-credit-phrase"],
                        artist_mbids=[a["artist"]["mbid"] for a in recording["artist-credit"]],
                        release_name=release["name"],
                        release_mbid=release["mbid"],
                        position=recording["position"],
                        mbid=recording["recording_id"],
                        additional_metadata={"caa_id": cover["caa_id"], "caa_release_mbid": cover["caa_release_mbid"]},
                        added_by_id=1,
                        created=now
                    )
                    playlist.recordings.append(rec)

    return jsonify({"playlist": playlist.serialize_jspf() if playlist is not None else {}})


@player_bp.get('/', defaults={'path': ''})
@player_bp.get('/<path:path>/')
def index(path):
    return render_template("index.html")
