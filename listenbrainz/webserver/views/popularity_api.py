import psycopg2
from brainzutils.ratelimit import ratelimit
from flask import Blueprint, request, current_app
from psycopg2.extras import DictCursor

from listenbrainz.db import popularity
from listenbrainz.db.recording import load_recordings_from_mbids_with_redirects
from listenbrainz.webserver.decorators import crossdomain
from listenbrainz.webserver.errors import APIBadRequest, APIInternalServerError
from listenbrainz.webserver.views.api_tools import is_valid_uuid

popularity_api_bp = Blueprint('popularity_api_v1', __name__)


@popularity_api_bp.get("/top-recordings-for-artist")
@crossdomain
@ratelimit()
def top_recordings():
    """ Get the top recordings by listen count for a given artist. The response is of the following format:

    .. code:: json

        [
          {
            "artist_mbids": [
              "b7ffd2af-418f-4be2-bdd1-22f8b48613da"
            ],
            "artist_name": "Nine Inch Nails",
            "caa_id": 2546761764,
            "caa_release_mbid": "2d410836-5add-3661-b0b0-168ba1696611",
            "length": 373133,
            "recording_mbid": "13dd61c7-ce73-4e97-9f0c-9f0e53144411",
            "recording_name": "Closer",
            "release_mbid": "ba8701ba-dc7c-4bca-9c83-846ee8c3d576",
            "release_name": "The Downward Spiral",
            "total_listen_count": 1380798,
            "total_user_count": 129454
          }
        ]

    :param artist_mbid: the mbid of the artist to get top recordings for
    :type artist_mbid: ``str``
    :statuscode 200: you have data!
    :statuscode 400: invalid artist_mbid argument
    """
    artist_mbid = request.args.get("artist_mbid")
    if not is_valid_uuid(artist_mbid):
        raise APIBadRequest(f"artist_mbid: '{artist_mbid}' is not a valid uuid")

    recordings = popularity.get_top_entity_for_entity("recording", artist_mbid, popularity_entity="recording")
    recording_mbids = [str(r["recording_mbid"]) for r in recordings]

    try:
        with psycopg2.connect(current_app.config["MB_DATABASE_URI"]) as mb_conn, \
                psycopg2.connect(current_app.config["SQLALCHEMY_TIMESCALE_URI"]) as ts_conn, \
                mb_conn.cursor(cursor_factory=DictCursor) as mb_curs, \
                ts_conn.cursor(cursor_factory=DictCursor) as ts_curs:
            recordings_data = load_recordings_from_mbids_with_redirects(mb_curs, ts_curs, recording_mbids)
    except Exception:
        current_app.logger.error("Error while fetching metadata for recordings: ", exc_info=True)
        raise APIInternalServerError("Failed to fetch metadata for recordings. Please try again.")

    for recording, data in zip(recordings, recordings_data):
        data.pop("artist_credit_id", None)
        data.pop("canonical_recording_mbid", None)
        data.pop("original_recording_mbid", None)
        data.update({
            "artist_name": data.pop("artist_credit_name"),
            "artist_mbids": data.pop("[artist_credit_mbids]"),
            "total_listen_count": recording["total_listen_count"],
            "total_user_count": recording["total_user_count"]
        })

    return recordings_data
