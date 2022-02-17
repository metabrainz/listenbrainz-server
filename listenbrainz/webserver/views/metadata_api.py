from brainzutils.ratelimit import ratelimit
from flask import Blueprint, request, jsonify, current_app

import listenbrainz.db.user as db_user
from listenbrainz.db.metadata import get_metadata_for_recording

metadata_bp = Blueprint('metadata', __name__)


@metadata_bp.route("/recording/", methods=["GET", "OPTIONS"])
@crossdomain(headers="Authorization, Content-Type")
@ratelimit()
def metadata_recording():
    """
    This endpoint takes in a list of recording_mbids and returns an array of dicts that contain
    recording metadata suitable for showing in a context that requires as much detail about
    a recording and the artist.

    TODO: Add a sample entry

    :param recording_mbids: A comma separated list of recording_mbids
    :type recording_mbids: ``str``
    :statuscode 200: playlist generated
    :statuscode 400: invalid recording_mbid arguments
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

    return jsonify(get_metadata_for_recording(recording_mbids)
