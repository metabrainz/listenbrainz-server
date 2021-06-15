from flask import Blueprint, request, jsonify
from listenbrainz.webserver.errors import APIBadRequest, APINotFound
from listenbrainz.webserver.rate_limiter import ratelimit

import listenbrainz.db.dump as db_dump

status_api_bp = Blueprint("status_api_v1", __name__)


@status_api_bp.route("/get-dump-info", methods=["GET"])
@ratelimit()
def get_dump_info():
    """
    Get information about ListenBrainz data dumps.
    You need to pass the `id` parameter in a GET request to get data about that particular
    dump.

    **Example response**:

    .. code-block:: json

        {
            "id": 1,
            "timestamp": "20190625-165900"
        }

    :query id: Integer specifying the ID of the dump, if not provided, the endpoint returns information about the latest data dump.
    :statuscode 200: You have data.
    :statuscode 400: You did not provide a valid dump ID. See error message for details.
    :statuscode 404: Dump with given ID does not exist.
    :resheader Content-Type: *application/json*
    """

    dump_id = request.args.get("id")
    if dump_id is None:
        try:
            dump = db_dump.get_dump_entries()[0] # return the latest dump
        except IndexError:
            raise APINotFound("No dump entry exists.")
    else:
        try:
            dump_id = int(dump_id)
        except ValueError:
            raise APIBadRequest("The `id` parameter needs to be an integer.")
        dump = db_dump.get_dump_entry(dump_id)
        if dump is None:
            raise APINotFound("No dump exists with ID: %d" % dump_id)

    return jsonify({
        "id": dump["id"],
        "timestamp": _convert_timestamp_to_string_dump_format(dump["created"]),
    })


def _convert_timestamp_to_string_dump_format(timestamp):
    """Convert datetime object to string.

    The string is the same format as the format in the file name.

    Args:
        timestamp (datetime): the datetime obj to be converted

    Returns:
        String of the format "20190625-170100"
    """
    return timestamp.strftime("%Y%m%d-%H%M%S")
