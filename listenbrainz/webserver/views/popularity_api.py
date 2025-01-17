from brainzutils.ratelimit import ratelimit
from flask import Blueprint, request, current_app

from listenbrainz.db import popularity
from listenbrainz.webserver import ts_conn, db_conn
from listenbrainz.webserver.decorators import crossdomain
from listenbrainz.webserver.errors import APIBadRequest, APIInternalServerError
from listenbrainz.webserver.views.api_tools import is_valid_uuid, MAX_ITEMS_PER_GET

popularity_api_bp = Blueprint('popularity_api_v1', __name__)


@popularity_api_bp.get("/top-recordings-for-artist/<artist_mbid>")
@crossdomain
@ratelimit()
def top_recordings_for_artist(artist_mbid):
    """ Get the top recordings by listen count for a given artist. The response is of the following format:

     .. code-block:: json

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
            "release_color": {
                "blue": 104,
                "green": 104,
                "red": 84
            },
            "release_mbid": "ba8701ba-dc7c-4bca-9c83-846ee8c3d576",
            "release_name": "The Downward Spiral",
            "total_listen_count": 1380798,
            "total_user_count": 129454
          }
        ]

    :statuscode 200: you have data!
    :statuscode 400: invalid artist_mbid
    """
    if not is_valid_uuid(artist_mbid):
        raise APIBadRequest(f"artist_mbid: '{artist_mbid}' is not a valid uuid")

    try:
        recordings = popularity.get_top_recordings_for_artist(db_conn, ts_conn, artist_mbid)
        return recordings
    except Exception:
        current_app.logger.error("Error while fetching metadata for recordings: ", exc_info=True)
        raise APIInternalServerError("Failed to fetch metadata for recordings. Please try again.")


@popularity_api_bp.get("/top-release-groups-for-artist/<artist_mbid>")
@crossdomain
@ratelimit()
def top_release_groups_for_artist(artist_mbid):
    """ Get the top release groups by listen count for a given artist. The response is of the following format:

     .. code-block:: json

        [
          {
            "artist": {
              "artist_credit_id": 368737,
              "artists": [],
              "name": "Pritam"
            },
            "release": {
              "caa_id": 14996821464,
              "caa_release_mbid": "488ef20e-7a2b-4daf-8bee-4f54fe26c7ab",
              "date": "2016-10-26",
              "name": "Ae Dil Hai Mushkil",
              "rels": [],
              "type": "Album"
            },
            "release_color": {
              "blue": 64,
              "green": 69,
              "red": 113
            },
            "release_group": {
              "caa_id": 14996821464,
              "caa_release_mbid": "488ef20e-7a2b-4daf-8bee-4f54fe26c7ab",
              "date": "2016-10-26",
              "name": "Ae Dil Hai Mushkil",
              "rels": [],
              "type": "Album"
            },
            "release_group_mbid": "d0991cc9-2277-4f5e-bd4d-2fa44507f623",
            "tag": {},
            "total_listen_count": 1432,
            "total_user_count": 82
          },
        ]

    :param artist_mbid: the mbid of the artist to get top release groups for
    :type artist_mbid: ``str``
    :statuscode 200: you have data!
    :statuscode 400: invalid artist_mbid
    """
    if not is_valid_uuid(artist_mbid):
        raise APIBadRequest(f"artist_mbid: '{artist_mbid}' is not a valid uuid")

    try:
        releases = popularity.get_top_release_groups_for_artist(db_conn, ts_conn, artist_mbid)
        return releases
    except Exception:
        current_app.logger.error("Error while fetching metadata for release groups: ", exc_info=True)
        raise APIInternalServerError("Failed to fetch metadata for release groups. Please try again.")


def fetch_entity_popularity_counts(entity):
    """ Validate API request and retrieve popularity counts for the requested entities """
    entity_mbid_key = f"{entity}_mbids"
    try:
        entity_mbids = request.json[entity_mbid_key]
    except KeyError:
        raise APIBadRequest(f"{entity_mbid_key} JSON element must be present and contain a list of {entity_mbid_key}")

    for mbid in entity_mbids:
        if not is_valid_uuid(mbid):
            raise APIBadRequest(f"{entity}_mbid {mbid} is not valid.")

    if len(entity_mbids) == 0:
        raise APIBadRequest(f"At least one valid {entity}_mbid must be present.")

    if len(entity_mbids) > MAX_ITEMS_PER_GET:
        raise APIBadRequest(f"Maximum number of {entity_mbid_key} that can be fetched at once is %s" % MAX_ITEMS_PER_GET)

    popularity_data, _ = popularity.get_counts(ts_conn, entity, entity_mbids)
    return popularity_data


@popularity_api_bp.post("/recording")
@crossdomain
@ratelimit()
def popularity_recording():
    """ Get the total listen count and total unique listeners count for a given recording.

    A JSON document with a list of recording_mbids and inc string must be POSTed. Up to
    :data:`~webserver.views.api.MAX_ITEMS_PER_GET` items can be requested at once. Example:

    .. code-block:: json

        {
            "recording_mbids": [
                "13dd61c7-ce73-4e97-9f0c-9f0e53144411",
                "22ad712e-ce73-9f0c-4e97-9f0e53144411"
            ]
        }

    The response maintains the order of the recording mbids supplied and also includes any recordings
    for which the data was not found with counts set to null. Example:

    .. code-block:: json

        [
            {
                "recording_mbid": "13dd61c7-ce73-4e97-9f0c-9f0e53144411",
                "total_listen_count": 1000,
                "total_user_count": 10
            },
            {
                "recording_mbid": "22ad712e-ce73-9f0c-4e97-9f0e53144411",
                "total_listen_count": null,
                "total_user_count": null
            }
        ]

    :statuscode 200: you have data!
    :statuscode 400: invalid recording_mbid(s)
    """
    return fetch_entity_popularity_counts("recording")


@popularity_api_bp.post("/artist")
@crossdomain
@ratelimit()
def popularity_artist():
    """ Get the total listen count and total unique listeners count for a given artist.

    A JSON document with a list of artists and inc string must be POSTed. Up to
    :data:`~webserver.views.api.MAX_ITEMS_PER_GET` items can be requested at once. Example:

    .. code-block:: json

        {
            "artist_mbids": [
                "13dd61c7-ce73-4e97-9f0c-9f0e53144411",
                "22ad712e-ce73-9f0c-4e97-9f0e53144411"
            ]
        }

    The response maintains the order of the artist mbids supplied and also includes any artists
    for which the data was not found with counts set to null. Example:

    .. code-block:: json

        [
            {
                "artist_mbid": "13dd61c7-ce73-4e97-9f0c-9f0e53144411",
                "total_listen_count": 1000,
                "total_user_count": 10
            },
            {
                "artist_mbid": "22ad712e-ce73-9f0c-4e97-9f0e53144411",
                "total_listen_count": null,
                "total_user_count": null
            }
        ]

    :statuscode 200: you have data!
    :statuscode 400: invalid artist_mbid(s)
    """
    return fetch_entity_popularity_counts("artist")


@popularity_api_bp.post("/release")
@crossdomain
@ratelimit()
def popularity_release():
    """ Get the total listen count and total unique listeners count for a given release.

    A JSON document with a list of releases and inc string must be POSTed. Up to
    :data:`~webserver.views.api.MAX_ITEMS_PER_GET` items can be requested at once. Example:

    .. code-block:: json

        {
            "release_mbids": [
                "13dd61c7-ce73-4e97-9f0c-9f0e53144411",
                "22ad712e-ce73-9f0c-4e97-9f0e53144411"
            ]
        }

    The response maintains the order of the release mbids supplied and also includes any releases
    for which the data was not found with counts set to null. Example:

    .. code-block:: json

        [
            {
                "release_mbid": "13dd61c7-ce73-4e97-9f0c-9f0e53144411",
                "total_listen_count": 1000,
                "total_user_count": 10
            },
            {
                "release_mbid": "22ad712e-ce73-9f0c-4e97-9f0e53144411",
                "total_listen_count": null,
                "total_user_count": null
            }
        ]

    :statuscode 200: you have data!
    :statuscode 400: invalid release_mbid(s)
    """
    return fetch_entity_popularity_counts("release")


@popularity_api_bp.post("/release-group")
@crossdomain
@ratelimit()
def popularity_release_group():
    """ Get the total listen count and total unique listeners count for a given release group.

    A JSON document with a list of release groups and inc string must be POSTed. Up to
    :data:`~webserver.views.api.MAX_ITEMS_PER_GET` items can be requested at once. Example:

    .. code-block:: json

        {
            "release_group_mbids": [
                "13dd61c7-ce73-4e97-9f0c-9f0e53144411",
                "22ad712e-ce73-9f0c-4e97-9f0e53144411"
            ]
        }

    The response maintains the order of the release group mbids supplied and also includes any release groups
    for which the data was not found with counts set to null. Example:

    .. code-block:: json

        [
            {
                "release_group_mbid": "13dd61c7-ce73-4e97-9f0c-9f0e53144411",
                "total_listen_count": 1000,
                "total_user_count": 10
            },
            {
                "release_group_mbid": "22ad712e-ce73-9f0c-4e97-9f0e53144411",
                "total_listen_count": null,
                "total_user_count": null
            }
        ]

    :statuscode 200: you have data!
    :statuscode 400: invalid release_group_mbid(s)
    """
    return fetch_entity_popularity_counts("release_group")
