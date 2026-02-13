import os

from flask import Blueprint, current_app, jsonify, send_file
from psycopg2 import DatabaseError

import listenbrainz.db.export as db_export
from listenbrainz.webserver import db_conn
from listenbrainz.webserver.decorators import crossdomain, api_listenstore_needed
from listenbrainz.webserver.errors import APIInternalServerError, APINotFound, APIBadRequest
from listenbrainz.webserver.views.api_tools import validate_auth_header
from brainzutils.ratelimit import ratelimit

export_api_bp = Blueprint("export_api", __name__)


@export_api_bp.post("/")
@crossdomain
@api_listenstore_needed
@ratelimit()
def create_export_task():
    """ Add a request to export the user data to an archive in background. """
    user = validate_auth_header()
    try:
        export = db_export.create(db_conn, user["id"])

        if export is not None:
            db_conn.commit()
            return jsonify(export)

        # task already exists in queue, rollback new entry
        db_conn.rollback()
        raise APIBadRequest(message="Data export already requested.")

    except DatabaseError:
        current_app.logger.error('Error while exporting user data: %s', user["musicbrainz_id"], exc_info=True)
        raise APIInternalServerError(f'Error while exporting user data {user["musicbrainz_id"]}, please try again later.')


@export_api_bp.get("/<int:export_id>/")
@crossdomain
@api_listenstore_needed
@ratelimit()
def get_export_task(export_id):
    """ Retrieve the requested export's data if it belongs to the specified user """
    user = validate_auth_header()
    export = db_export.get(db_conn, user["id"], export_id)
    if export is None:
        raise APINotFound("Export not found")
    return jsonify(export)


@export_api_bp.get("/list/")
@crossdomain
@api_listenstore_needed
@ratelimit()
def list_export_tasks():
    """ Retrieve the all export tasks for the current user """
    user = validate_auth_header()
    exports = db_export.list_for_user(db_conn, user["id"])
    return jsonify(exports)


@export_api_bp.get("/download/<int:export_id>/")
@crossdomain
@api_listenstore_needed
@ratelimit()
def download_export_archive(export_id):
    """ Download the requested export if it is complete and belongs to the specified user """
    user = validate_auth_header()
    export = db_export.get_completed(db_conn, user["id"], export_id)
    if export is None:
        raise APINotFound("Export not found")

    file_path = os.path.join(current_app.config["USER_DATA_EXPORT_BASE_DIR"], str(export["filename"]))
    return send_file(file_path, mimetype="application/zip", as_attachment=True)


@export_api_bp.post("/delete/<int:export_id>/")
@crossdomain
@api_listenstore_needed
@ratelimit()
def delete_export_archive(export_id):
    """ Delete the specified export archive """
    user = validate_auth_header()
    filename = db_export.delete(db_conn, user["id"], export_id)
    if filename is not None:
        db_conn.commit()
        # file is deleted from disk by cronjob
        return jsonify({"success": True})
    else:
        raise APINotFound("Export not found")
