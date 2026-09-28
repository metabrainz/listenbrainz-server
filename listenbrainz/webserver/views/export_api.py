from datetime import datetime, timezone

from brainzutils.ratelimit import ratelimit
from flask import Blueprint, current_app, jsonify, request, send_file
from psycopg2 import DatabaseError

from listenbrainz.db import user_data_export
from listenbrainz.webserver import db_conn
from listenbrainz.webserver.decorators import api_listenstore_needed, crossdomain
from listenbrainz.webserver.errors import APIBadRequest, APIInternalServerError, APINotFound
from listenbrainz.webserver.views.api_tools import validate_auth_header

export_api_bp = Blueprint("export_api", __name__)


def _parse_export_time_range():
    """Parse optional inclusive UNIX-second bounds from an export request."""
    if not request.get_data():
        return None, None
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        raise APIBadRequest("Request body must be a JSON object.")

    for name in ("start_time", "end_time"):
        if name not in data:
            continue
        value = data[name]
        if type(value) is not int:
            raise APIBadRequest(f"{name} must be an integer UNIX timestamp in seconds.")
        try:
            datetime.fromtimestamp(value, timezone.utc)
        except (ValueError, OverflowError, OSError):
            raise APIBadRequest(f"{name} is outside the supported timestamp range.")

    start_time, end_time = data.get("start_time"), data.get("end_time")
    if start_time is not None and end_time is not None and start_time > end_time:
        raise APIBadRequest("start_time must be less than or equal to end_time.")
    return start_time, end_time


def _prepare_export_download_response(archive, filename):
    """Prepare an HTTP response for a completed export archive."""
    response = send_file(
        archive["Body"],
        mimetype="application/zip",
        as_attachment=True,
        download_name=filename,
        conditional=False,
    )
    content_length = archive.get("ContentLength")
    if content_length is not None:
        response.content_length = content_length
    return response


@export_api_bp.post("/")
@crossdomain
@api_listenstore_needed
@ratelimit()
def create_export_task():
    """ Add a request to export the user data to an archive in background. """
    user = validate_auth_header()
    start_time, end_time = _parse_export_time_range()
    try:
        export_data = user_data_export.request_user_data_export(db_conn, user["id"], start_time, end_time)
        if export_data is not None:
            return jsonify(export_data)
        raise APIBadRequest(message="Data export already requested.")
    except DatabaseError:
        current_app.logger.error('Error while exporting user data: %s', user["musicbrainz_id"], exc_info=True)
        raise APIInternalServerError(f'Error while exporting user data {user["musicbrainz_id"]}, please try again later.')


@export_api_bp.get("/<int:export_id>")
@crossdomain
@api_listenstore_needed
@ratelimit()
def get_export_task(export_id):
    """ Retrieve the requested export's data if it belongs to the specified user """
    user = validate_auth_header()
    export_data = user_data_export.get_export_task(db_conn, user["id"], export_id)
    if export_data is None:
        raise APINotFound("Export %s not found" % export_id)
    return jsonify(export_data)


@export_api_bp.get("/list")
@crossdomain
@api_listenstore_needed
@ratelimit()
def list_export_tasks():
    """ Retrieve all export tasks for the current user """
    user = validate_auth_header()
    export_tasks = user_data_export.list_export_tasks(db_conn, user["id"])
    return jsonify(export_tasks)


@export_api_bp.get("/<int:export_id>/download")
@crossdomain
@api_listenstore_needed
@ratelimit()
def download_export_archive(export_id):
    """ Download the requested export if it is complete and belongs to the specified user """
    user = validate_auth_header()
    archive, filename = user_data_export.get_completed_export_archive(db_conn, user["id"], export_id)
    if archive is None:
        raise APINotFound("Export %s not found" % export_id)

    try:
        response = _prepare_export_download_response(archive, filename)
    except Exception:
        current_app.logger.error("Error while downloading user data export: %s", filename, exc_info=True)
        raise APIInternalServerError("Error while downloading export, please try again later.")

    return response

@export_api_bp.post("/<int:export_id>/delete")
@crossdomain
@api_listenstore_needed
@ratelimit()
def delete_export_archive(export_id):
    """ Delete the requested export if it belongs to the specified user """
    user = validate_auth_header()
    success = user_data_export.delete_export_task(db_conn, user["id"], export_id)
    if success:
        return jsonify({"success": True})
    else:
        raise APINotFound("Export %s not found" % export_id)
