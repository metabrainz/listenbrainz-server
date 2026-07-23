import json
import os

from flask import Blueprint, current_app, jsonify, send_file
from flask_login import current_user
from psycopg2 import DatabaseError

from listenbrainz.db import user_data_export
from listenbrainz.webserver import db_conn
from listenbrainz.webserver.decorators import web_listenstore_needed
from listenbrainz.webserver.errors import APIInternalServerError, APINotFound, APIBadRequest
from listenbrainz.webserver.login import api_login_required

export_bp = Blueprint("export", __name__)


@export_bp.post("/")
@api_login_required
@web_listenstore_needed
def create_export_task():
    """ Add a request to export the user data to an archive in background. """
    try:
        export_data = user_data_export.request_user_data_export(db_conn, current_user.id)
        if export_data is not None:
            db_conn.commit()
            return jsonify(export_data)

        # task already exists in queue, rollback new entry
        db_conn.rollback()
        raise APIBadRequest(message="Data export already requested.")

    except DatabaseError:
        current_app.logger.error('Error while exporting user data: %s', current_user.musicbrainz_id, exc_info=True)
        raise APIInternalServerError(f'Error while exporting user data {current_user.musicbrainz_id}, please try again later.')


@export_bp.get("/<export_id>/")
@api_login_required
@web_listenstore_needed
def get_export_task(export_id):
    """ Retrieve the requested export's data if it belongs to the specified user """
    export_data = user_data_export.get_export_task(db_conn, current_user.id, export_id)
    if export_data is None:
        raise APINotFound("Export not found")
    return jsonify(export_data)


@export_bp.get("/list/")
@api_login_required
@web_listenstore_needed
def list_export_tasks():
    """ Retrieve the all export tasks for the current user """
    export_tasks = user_data_export.list_export_tasks(db_conn, current_user.id)
    return jsonify(export_tasks)


@export_bp.post("/download/<export_id>/")
@api_login_required
@web_listenstore_needed
def download_export_archive(export_id):
    """ Download the requested export if it is complete and belongs to the specified user """
    filename = user_data_export.get_completed_export_filename(db_conn, current_user.id, export_id)
    if filename is None:
        raise APINotFound("Export not found")

    file_path = os.path.join(current_app.config["USER_DATA_EXPORT_BASE_DIR"], filename)
    return send_file(file_path, mimetype="application/zip", as_attachment=True)



@export_bp.post("/delete/<export_id>/")
@api_login_required
@web_listenstore_needed
def delete_export_archive(export_id):
    """ Delete the specified export archive """
    success = user_data_export.delete_export_task(db_conn, current_user.id, export_id)
    if success:
        db_conn.commit()
        # file is deleted from disk by cronjob
        return jsonify({"success": True})
    else:
        raise APINotFound("Export not found")
