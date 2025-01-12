from brainzutils.ratelimit import ratelimit
from datasethoster import RequestSource
from flask import Blueprint, request, jsonify, current_app

from listenbrainz.db.mbid_manual_mapping import create_mbid_manual_mapping, get_mbid_manual_mapping
from listenbrainz.db.metadata import get_metadata_for_recording, get_metadata_for_artist, get_metadata_for_release_group
from listenbrainz.db.model.mbid_manual_mapping import MbidManualMapping
from listenbrainz.labs_api.labs.api.artist_credit_recording_lookup import ArtistCreditRecordingLookupQuery, \
    ArtistCreditRecordingLookupInput
from listenbrainz.labs_api.labs.api.artist_credit_recording_release_lookup import \
    ArtistCreditRecordingReleaseLookupQuery, ArtistCreditRecordingReleaseLookupInput
from listenbrainz.labs_api.labs.api.mbid_mapping import MBIDMappingQuery, MBIDMappingInput
from listenbrainz.mbid_mapping_writer.mbid_mapper import MBIDMapper
from listenbrainz.webserver import ts_conn
from listenbrainz.webserver.decorators import crossdomain
from listenbrainz.webserver.errors import APIBadRequest, APIInternalServerError
from listenbrainz.webserver.utils import parse_boolean_arg
from listenbrainz.webserver.views.api_tools import is_valid_uuid, validate_auth_header, MAX_ITEMS_PER_GET

metadata_bp = Blueprint('metadata', __name__)

#: The maximum length of the query permitted for a mapping search
MAX_MAPPING_QUERY_LENGTH = 250
#: The maximum number of lookups permitted in a bulk POST query
MAX_LOOKUPS_PER_POST = 50


def parse_incs(incs):
    allowed_incs = ("artist", "tag", "release", "recording", "release_group")

    if not incs:
        return []
    incs = incs.split()
    for inc in incs:
        if inc not in allowed_incs:
            raise APIBadRequest("invalid inc argument '%s'. Must be one of %s." % (inc, ", ".join(allowed_incs)))

    return incs


def fetch_metadata(recording_mbids, incs):
    metadata = get_metadata_for_recording(ts_conn, recording_mbids)
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


def fetch_release_group_metadata(release_group_mbids, incs):
    metadata = get_metadata_for_release_group(ts_conn, release_group_mbids)
    result = {}
    for entry in metadata:
        data = {"release_group": entry.release_group_data}
        if "artist" in incs:
            data["artist"] = entry.artist_data

        if "tag" in incs:
            data["tag"] = entry.tag_data

        if "release" in incs:
            data["release"] = entry.release_group_data

        if "recording" in incs:
            if "recordings" in entry.recording_data:
                del entry.recording_data["recordings"]
            data["recording"] = entry.recording_data

        result[str(entry.release_group_mbid)] = data

    return result


@metadata_bp.get("/recording/")
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
    incs = parse_incs(request.args.get("inc"))

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


@metadata_bp.post("/recording/")
@crossdomain
@ratelimit()
def metadata_recording_post():
    """
    This endpoint is the POST verson for fetching recording metadata, since it allows up to the
    max number of items allowed. (:data:`~webserver.views.api.MAX_ITEMS_PER_GET` items)

    A JSON document with a list of recording_mbids and inc string must be POSTed
    to this endpoint to returns an array of dicts that contain
    recording metadata suitable for showing in a context that requires as much detail about
    a recording and the artist. Using the inc parameter, you can control which portions of metadata
    to fetch.


    .. code-block:: json

       {
            "recording_mbids": [ "25d47b0c-5177-49db-b740-c166e4acebd1", "..." ],
            "inc": "artist tag"
       }

    To see what data this endpoint returns, please look at the data above for the GET version.

    :statuscode 200: you have data!
    :statuscode 400: invalid recording_mbid arguments
    """
    data = request.json

    try:
        incs = parse_incs(data["inc"])
    except KeyError:
        incs = []

    try:
        recording_mbids = data["recording_mbids"]
    except KeyError:
        raise APIBadRequest(
            "recording_mbids JSON element must be present and contain a list of recording_mbids")

    for mbid in recording_mbids:
        if not is_valid_uuid(mbid):
            raise APIBadRequest(f"recording_mbid {mbid} is not valid.")

    if len(recording_mbids) == 0:
        raise APIBadRequest("At least one valid recording_mbid must be present.")

    if len(recording_mbids) > MAX_ITEMS_PER_GET:
        raise APIBadRequest("Maximum number of recordings_mbids that can be fetched at once is %s" % MAX_ITEMS_PER_GET)

    result = fetch_metadata(recording_mbids, incs)
    return jsonify(result)


@metadata_bp.get("/release_group/")
@crossdomain
@ratelimit()
def metadata_release_group():
    """
    This endpoint takes in a list of release_group_mbids and returns an array of dicts that contain
    release_group metadata suitable for showing in a context that requires as much detail about
    a release_group and the artist. Using the inc parameter, you can control which portions of metadata
    to fetch.

    The data returned by this endpoint can be seen here:

    .. literalinclude:: ../../../listenbrainz/testdata/mb_release_group_metadata_cache_example.json
       :language: json

    :param release_group_mbids: A comma separated list of release_group_mbids
    :type release_group_mbids: ``str``
    :param inc: A space separated list of "artist", "tag" and/or "release" to indicate which portions
                of metadata you're interested in fetching. We encourage users to only fetch the data
                they plan to consume.
    :type inc: ``str``
    :statuscode 200: you have data!
    :statuscode 400: invalid release_group_mbid arguments
    """
    incs = parse_incs(request.args.get("inc"))

    release_groups = request.args.get("release_group_mbids", default=None)
    if release_groups is None:
        raise APIBadRequest(
            "release_group_mbids argument must be present and contain a comma separated list of release_group_mbids")

    release_group_mbids = []
    for mbid in release_groups.split(","):
        mbid_clean = mbid.strip()
        if not is_valid_uuid(mbid_clean):
            raise APIBadRequest(f"Release group mbid {mbid} is not valid.")

        release_group_mbids.append(mbid_clean)

    result = fetch_release_group_metadata(release_group_mbids, incs)
    return jsonify(result)


def process_results(match, metadata, incs):
    recording_mbid = str(match["recording_mbid"])
    result = {
        "recording_mbid": recording_mbid,
        "release_mbid": str(match["release_mbid"]),
        "artist_mbids": [str(artist_mbid) for artist_mbid in match["artist_mbids"]],
        "recording_name": match["recording_name"],
        "release_name": match["release_name"],
        "artist_credit_name": match["artist_credit_name"]
    }
    if metadata:
        extras = fetch_metadata([recording_mbid], incs)
        result["metadata"] = extras.get(recording_mbid, {})
    return result


@metadata_bp.get("/lookup/")
@crossdomain
@ratelimit()
def get_mbid_mapping():
    """
    This endpoint looks up mbid metadata for the given artist, recording and optionally a release name.
    The total number of characters in the artist name, recording name and release name query arguments should be
    less than or equal to :data:`~webserver.views.metadata_api.MAX_MAPPING_QUERY_LENGTH`.

    The data returned by this endpoint can be seen here:

    .. literalinclude:: ../../../listenbrainz/testdata/mb_lookup_metadata_example.json
       :language: json

    :param artist_name: artist name of the listen
    :type artist_name: ``str``
    :param recording_name: track name of the listen
    :type recording_name: ``str``
    :param release_name: release name of the listen
    :type release_name: ``str``
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
    release_name = request.args.get("release_name")
    if not artist_name:
        raise APIBadRequest("artist_name is invalid or not present in arguments")
    if not recording_name:
        raise APIBadRequest("recording_name is invalid or not present in arguments")
    if len(artist_name) + len(recording_name) + len(release_name or "") > MAX_MAPPING_QUERY_LENGTH:
        raise APIBadRequest(f"total number of characters in artist_name, recording_name and release_name"
                            f" arguments must be less than {MAX_MAPPING_QUERY_LENGTH}")

    metadata = parse_boolean_arg("metadata")
    incs = parse_incs(request.args.get("inc")) if metadata else []

    params = [
        ArtistCreditRecordingReleaseLookupInput(
            artist_credit_name=artist_name,
            recording_name=recording_name,
            release_name=release_name or "",
        )
    ]

    try:
        if release_name:
            q = ArtistCreditRecordingReleaseLookupQuery(debug=False)
            exact_results = q.fetch(params, RequestSource.json_post)
            if exact_results:
                return process_results(exact_results[0].dict(), metadata, incs)

        q = ArtistCreditRecordingLookupQuery(debug=False)
        exact_results = q.fetch(params, RequestSource.json_post)
        if exact_results:
            return process_results(exact_results[0].dict(), metadata, incs)

        q = MBIDMapper(timeout=10, remove_stop_words=True, debug=False, retry_on_timeout=False)
        fuzzy_result = q.search(artist_name, recording_name, release_name)
        if fuzzy_result:
            return process_results(fuzzy_result, metadata, incs)

    except Exception as e:
        current_app.logger.error("Server failed to lookup recording: {}".format(e), exc_info=True)
        raise APIInternalServerError("Server failed to lookup recording")

    return jsonify({})


def make_acrr_input(recording):
    """ Create input for ArtistCreditRecordingReleaseLookup labs api query """
    if "release_name" in recording:
        return ArtistCreditRecordingReleaseLookupInput(
            artist_credit_name=recording["artist_name"],
            recording_name=recording["recording_name"],
            release_name=recording["release_name"],
        )
    else:
        return None


def make_acr_input(recording):
    """ Create input for ArtistCreditRecordingLookup labs api query """
    return ArtistCreditRecordingLookupInput(
        artist_credit_name=recording["artist_name"],
        recording_name=recording["recording_name"],
    )


def make_mapping_input(recording):
    """ Create input for MBIDMapper labs api query """
    return MBIDMappingInput(
        artist_credit_name=recording["artist_name"],
        recording_name=recording["recording_name"],
    )


def process_bulk_lookup_results(all_results, all_params, query, make_input):
    """ Lookup recordings using the specified query and update successful lookups in all results"""
    query_params = []
    reverse_index = {}
    param_idx = 0

    for original_idx, recording in all_params.items():
        param = make_input(recording)
        if param is None:
            continue
        query_params.append(param)
        reverse_index[param_idx] = original_idx
        param_idx += 1

    if not query_params:
        return all_results, all_params

    query_results = query.fetch(query_params, RequestSource.json_post)

    for query_result in query_results:
        original_idx = reverse_index[query_result.index]
        original_result = all_results[original_idx]

        result_dict = query_result.dict(exclude={"index", "artist_credit_arg", "recording_name_arg", "release_name_arg"})
        original_result.update(**result_dict)
        all_params.pop(original_idx)

    return all_results, all_params


@metadata_bp.post("/lookup/")
@crossdomain
@ratelimit()
def get_mbid_mapping_post():
    """
    This endpoint is the POST version for looking up recording mbids and associated MusicBrainz data. It allows up to
    max number of items allowed. (:data:`~webserver.views.api.MAX_LOOKUPS_PER_POST` items)

    A JSON document with a list of dicts each of which contain metadata (artist_name, recording_name and optionally
    a release name) for the recording to be looked up. The total number of characters in the artist name, recording name
    and release name for each recording should be less than or equal to :data:`~webserver.views.metadata_api.MAX_MAPPING_QUERY_LENGTH`.

    .. code:: json

        {
          "recordings": [
            {
              "recording_name": "Never Gonna Give You Up",
              "artist_name": "Rick Astley",
              "release_name": "Red Hot"
            },
            {
              "recording_name": "Blinding Lights",
              "artist_name": "The Weeknd"
            }
          ]
        }

    To see what data this endpoint returns, please look at the data above for the GET version. Note that this endpoint
    does not support metadata and incs parameters.

    :statuscode 200: lookup succeeded, does not indicate whether a match was found or not
    :statuscode 400: invalid arguments
    """
    data = request.json
    recordings = data.get("recordings", [])
    if not recordings:
        raise APIBadRequest("recordings is invalid or not present in body")

    if len(recordings) > MAX_LOOKUPS_PER_POST:
        raise APIBadRequest(f"Number of recordings in request body exceeds maximum permitted. ({MAX_LOOKUPS_PER_POST})")

    all_params = {}
    all_results = []
    for idx, recording in enumerate(recordings):
        artist_name = recording.get("artist_name")
        recording_name = recording.get("recording_name")
        release_name = recording.get("release_name")
        if not artist_name:
            raise APIBadRequest(f"Recording {idx} artist_name is invalid or not present")
        if not recording_name:
            raise APIBadRequest(f"Recording {idx} recording_name is invalid or not present")
        if len(artist_name) + len(recording_name) + len(release_name or "") > MAX_MAPPING_QUERY_LENGTH:
            raise APIBadRequest(f"Recording {idx} total number of characters in artist_name, recording_name and"
                                f" release_name arguments must be less than {MAX_MAPPING_QUERY_LENGTH}")

        all_params[idx] = recording
        all_results.append({
            "artist_name_arg": artist_name,
            "recording_name_arg": recording_name,
            "release_name_arg": release_name,
            "index": idx
        })

    try:
        acrr_query = ArtistCreditRecordingReleaseLookupQuery(debug=False)
        all_results, all_params = process_bulk_lookup_results(all_results, all_params, acrr_query, make_acrr_input)

        acr_query = ArtistCreditRecordingLookupQuery(debug=False)
        all_results, all_params = process_bulk_lookup_results(all_results, all_params, acr_query, make_acr_input)

        mapping_query = MBIDMappingQuery(timeout=10, remove_stop_words=True, debug=False)
        all_results, _ = process_bulk_lookup_results(all_results, all_params, mapping_query, make_mapping_input)

        return jsonify(all_results)
    except Exception as e:
        current_app.logger.error("Server failed to lookup recording: {}".format(e), exc_info=True)
        raise APIInternalServerError("Server failed to lookup recording")


@metadata_bp.post("/submit_manual_mapping/")
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

    create_mbid_manual_mapping(ts_conn, mapping)

    return jsonify({"status": "ok"})


@metadata_bp.get("/get_manual_mapping/")
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

    existing_mapping = get_mbid_manual_mapping(ts_conn, recording_msid=recording_msid, user_id=user["id"])

    if existing_mapping:
        return jsonify({
            "status": "ok",
            "mapping": existing_mapping.to_api()
        })
    else:
        return jsonify({"status": "none"}), 404


@metadata_bp.get("/artist/")
@crossdomain
@ratelimit()
def metadata_artist():
    """
    This endpoint takes in a list of artist_mbids and returns an array of dicts that contain
    recording metadata suitable for showing in a context that requires as much detail about
    a recording and the artist. Using the inc parameter, you can control which portions of metadata
    to fetch.

    The data returned by this endpoint can be seen here:

    .. literalinclude:: ../../../listenbrainz/testdata/mb_artist_metadata_example.json
       :language: json

    :param artist_mbids: A comma separated list of recording_mbids
    :type artist_mbids: ``str``
    :param inc: A space separated list of "artist", "tag" and/or "release" to indicate which portions
                of metadata you're interested in fetching. We encourage users to only fetch the data
                they plan to consume.
    :type inc: ``str``
    :statuscode 200: you have data!
    :statuscode 400: invalid recording_mbid arguments
    """
    incs = parse_incs(request.args.get("inc"))

    artists = request.args.get("artist_mbids", default=None)
    if artists is None:
        raise APIBadRequest(
            "artist_mbids argument must be present and contain a comma separated list of artist_mbids")

    artist_mbids = []
    for mbid in artists.split(","):
        mbid_clean = mbid.strip()
        if not is_valid_uuid(mbid_clean):
            raise APIBadRequest(f"artist mbid {mbid} is not valid.")

        artist_mbids.append(mbid_clean)

    results = []
    for row in get_metadata_for_artist(ts_conn, artist_mbids):
        item = {"artist_mbid": row.artist_mbid}
        item.update(**row.artist_data)
        if "tag" in incs:
            item["tag"] = row.tag_data
        if "release_group" in incs:
            item["release_group"] = row.release_group_data
        results.append(item)
    return jsonify(results)
