from brainzutils.ratelimit import ratelimit
from flask import Blueprint, request, jsonify, current_app

import listenbrainz.db.user as db_user
from listenbrainz.db.metadata import get_metadata_for_recording
from listenbrainz.webserver.decorators import crossdomain
from listenbrainz.webserver.views.api_tools import is_valid_uuid
from listenbrainz.webserver.errors import APIBadRequest

metadata_bp = Blueprint('metadata', __name__)


@metadata_bp.route("/recording/", methods=["GET", "OPTIONS"])
@crossdomain
@ratelimit()
def metadata_recording():
    """
    This endpoint takes in a list of recording_mbids and returns an array of dicts that contain
    recording metadata suitable for showing in a context that requires as much detail about
    a recording and the artist. Using the inc parameter, you can control which portions of metadata
    to fetch.

    The data returned by this endpoint can be seen here: (TODO: Changes this to a fancy link)

       listenbrainz-server/listenbrainz/testdata/mb_metadata_cache_example.json 

    :param recording_mbids: A comma separated list of recording_mbids
    :type recording_mbids: ``str``
    :param inc: A space separated list of "artist", "tag" and/or "release" to indicate which portions
                of metadata you're interested in fetching. We encourage users to only fetch the data
                they plan to consume.
    :statuscode 200: you have data!
    :statuscode 400: invalid recording_mbid arguments
    """

    allowed_incs = ("artist", "tag", "release")

    recordings = request.args.get("recording_mbids", default=None)
    if recordings is None:
        raise BadRequest("recording_mbids argument must be present and contain a comma separated list of recording_mbids")

    incs = request.args.get("inc", default="")
    incs = incs.split()
    for inc in incs:
        if inc not in allowed_incs:
            raise APIBadRequest("invalid inc argument '%s'. Must be one of %s." % (inc, ",".join(allowed_incs)))

    recording_mbids = []
    for mbid in recordings.split(","):
        mbid_clean = mbid.strip()
        if not is_valid_uuid(mbid_clean):
            raise APIBadRequest(f"Recording mbid {mbid} is not valid.")

        recording_mbids.append(mbid_clean)

    metadata = get_metadata_for_recording(recording_mbids)
    result = {}
    for entry in metadata:
        data = {"recording": entry.recording_data}
        if "artist" in incs:
            data["artist"] = entry.artist_data

        if "tag" in incs:
            data["tag"] = entry.tag_data

        if "release" in incs:
            data["release"] = entry.release_data

        result[str(entry.recording_mbid)] = data

    return jsonify(result)
