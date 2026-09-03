import os

from brainzutils.ratelimit import ratelimit
from flask import Blueprint, current_app, jsonify, send_file
from psycopg2 import DatabaseError

from listenbrainz.db import user_data_export
from listenbrainz.webserver import db_conn
from listenbrainz.webserver.decorators import api_listenstore_needed, crossdomain
from listenbrainz.webserver.errors import APIBadRequest, APIInternalServerError, APINotFound
from listenbrainz.webserver.views.api_tools import validate_auth_header

export_api_bp = Blueprint("export_api", __name__)


@export_api_bp.post("/")
@crossdomain
@api_listenstore_needed
@ratelimit()
def create_export_task():
    """ Add a request to export the user data to an archive in background. """
    user = validate_auth_header()
    try:
        export_data = user_data_export.request_user_data_export(db_conn, user["id"])
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
        raise APINotFound("Export not found")
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
    filename = user_data_export.get_completed_export_filename(db_conn, user["id"], export_id)
    if filename is None:
        raise APINotFound("Export not found")

    file_path = os.path.join(current_app.config["USER_DATA_EXPORT_BASE_DIR"], filename)
    return send_file(file_path, mimetype="application/zip", as_attachment=True)
