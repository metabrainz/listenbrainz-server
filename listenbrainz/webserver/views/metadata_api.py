from brainzutils.ratelimit import ratelimit
from flask import Blueprint, request, jsonify

from listenbrainz.db.mbid_manual_mapping import create_mbid_manual_mapping, get_mbid_manual_mapping
from listenbrainz.db.metadata import get_metadata_for_recording
from listenbrainz.db.model.mbid_manual_mapping import MbidManualMapping
from listenbrainz.labs_api.labs.api.artist_credit_recording_lookup import ArtistCreditRecordingLookupQuery
from listenbrainz.mbid_mapping_writer.mbid_mapper_metadata_api import MBIDMapperMetadataAPI
from listenbrainz.webserver.decorators import crossdomain
from listenbrainz.webserver.errors import APIBadRequest
from listenbrainz.webserver.utils import parse_boolean_arg
from listenbrainz.webserver.views.api_tools import is_valid_uuid, validate_auth_header

metadata_bp = Blueprint('metadata', __name__)


def parse_incs():
    allowed_incs = ("artist", "tag", "release")

    incs = request.args.get("inc")
    if not incs:
        return []
    incs = incs.split()
    for inc in incs:
        if inc not in allowed_incs:
            raise APIBadRequest("invalid inc argument '%s'. Must be one of %s." % (inc, ", ".join(allowed_incs)))

    return incs


def fetch_metadata(recording_mbids, incs):
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

    return result


@metadata_bp.route("/recording/", methods=["GET", "OPTIONS"])
@crossdomain
@ratelimit()
def metadata_recording():
    """
    This endpoint takes in a list of recording_mbids and returns an array of dicts that contain
    recording metadata suitable for showing in a context that requires as much detail about
    a recording and the artist. Using the inc parameter, you can control which portions of metadata
    to fetch.

    The data returned by this endpoint can be seen here:

    .. literalinclude:: ../../../listenbrainz/testdata/mb_metadata_cache_example.json
       :language: json

    :param recording_mbids: A comma separated list of recording_mbids
    :type recording_mbids: ``str``
    :param inc: A space separated list of "artist", "tag" and/or "release" to indicate which portions
                of metadata you're interested in fetching. We encourage users to only fetch the data
                they plan to consume.
    :type inc: ``str``
    :statuscode 200: you have data!
    :statuscode 400: invalid recording_mbid arguments
    """
    incs = parse_incs()

    recordings = request.args.get("recording_mbids", default=None)
    if recordings is None:
        raise APIBadRequest(
            "recording_mbids argument must be present and contain a comma separated list of recording_mbids")

    recording_mbids = []
    for mbid in recordings.split(","):
        mbid_clean = mbid.strip()
        if not is_valid_uuid(mbid_clean):
            raise APIBadRequest(f"Recording mbid {mbid} is not valid.")

        recording_mbids.append(mbid_clean)

    result = fetch_metadata(recording_mbids, incs)
    return jsonify(result)


def process_results(match, metadata, incs):
    recording_mbid = match["recording_mbid"]
    result = {
        "recording_mbid": recording_mbid,
        "release_mbid": match["release_mbid"],
        "artist_mbids": match["artist_mbids"],
        "recording_name": match["recording_name"],
        "release_name": match["release_name"],
        "artist_credit_name": match["artist_credit_name"]
    }
    if metadata:
        extras = fetch_metadata([recording_mbid], incs)
        result["metadata"] = extras.get(recording_mbid, {})
    return result


@metadata_bp.route("/lookup/", methods=["GET", "OPTIONS"])
@crossdomain
@ratelimit()
def get_mbid_mapping():
    """
    This endpoint looks up mbid metadata for the given artist and recording name.

    :param artist_name: artist name of the listen
    :type artist_name: ``str``
    :param recording_name: track name of the listen
    :type artist_name: ``str``
    :param metadata: should extra metadata be also returned if a match is found,
                     see /metadata/recording for details.
    :type metadata: ``bool``
    :param inc: same as /metadata/recording endpoint
    :type inc: ``str``
    :statuscode 200: lookup succeeded, does not indicate whether a match was found or not
    :statuscode 400: invalid arguments
    """
    artist_name = request.args.get("artist_name")
    recording_name = request.args.get("recording_name")
    if not artist_name:
        raise APIBadRequest("artist_name is invalid or not present in arguments")
    if not recording_name:
        raise APIBadRequest("recording_name is invalid or not present in arguments")

    metadata = parse_boolean_arg("metadata")
    incs = parse_incs() if metadata else []

    params = [
        {
            "[artist_credit_name]": artist_name,
            "[recording_name]": recording_name
        }
    ]

    q = ArtistCreditRecordingLookupQuery(debug=False)
    exact_results = q.fetch(params)
    if exact_results:
        return process_results(exact_results[0], metadata, incs)

    q = MBIDMapperMetadataAPI(timeout=10, remove_stop_words=True, debug=False)
    fuzzy_result = q.search(artist_name, recording_name)
    if fuzzy_result:
        return process_results(fuzzy_result, metadata, incs)

    return jsonify({})


@metadata_bp.route("/submit_manual_mapping/", methods=["POST", "OPTIONS"])
@crossdomain
@ratelimit()
def submit_manual_mapping():
    """
    Submit a manual mapping of a recording messybrainz ID to a musicbrainz recording id.

    The format of the JSON to be POSTed to this endpoint is:

    .. code-block:: json

        {
            "recording_msid": "d23f4719-9212-49f0-ad08-ddbfbfc50d6f",
            "recording_mbid": "8f3471b5-7e6a-48da-86a9-c1c07a0f47ae"
        }

    :reqheader Authorization: Token <user token>
    :reqheader Content-Type: *application/json*
    :statuscode 200: Mapping added, or already exists.
    :statuscode 400: invalid JSON sent, see error message for details.
    :statuscode 401: invalid authorization. See error message for details.
    :resheader Content-Type: *application/json*
    """
    user = validate_auth_header()

    recording_msid = request.json.get("recording_msid")
    recording_mbid = request.json.get("recording_mbid")
    if not recording_msid or not is_valid_uuid(recording_msid):
        raise APIBadRequest("recording_msid is invalid or not present in arguments")
    if not recording_mbid or not is_valid_uuid(recording_mbid):
        raise APIBadRequest("recording_mbid is invalid or not present in arguments")

    mapping = MbidManualMapping(
        recording_msid=recording_msid,
        recording_mbid=recording_mbid,
        user_id=user["id"]
    )

    create_mbid_manual_mapping(mapping)

    return jsonify({"status": "ok"})


@metadata_bp.route("/get_manual_mapping/", methods=["GET", "OPTIONS"])
@crossdomain
@ratelimit()
def get_manual_mapping():
    """
    Get the manual mapping of a recording messybrainz ID that a user added.

    :reqheader Authorization: Token <user token>
    :reqheader Content-Type: *application/json*
    :statuscode 200: The response of the mapping.
    :statuscode 404: No such mapping for this user/recording msid
    :resheader Content-Type: *application/json*
    """
    user = validate_auth_header()

    recording_msid = request.args.get("recording_msid")
    if not recording_msid or not is_valid_uuid(recording_msid):
        raise APIBadRequest("recording_msid is invalid or not present in arguments")

    existing_mapping = get_mbid_manual_mapping(recording_msid=recording_msid, user_id=user["id"])

    if existing_mapping:
        return jsonify({
            "status": "ok",
            "mapping": existing_mapping.to_api()
        })
    else:
        return jsonify({"status": "none"}), 404
