import json
import os

from botocore.exceptions import ClientError
from flask import Blueprint, current_app, jsonify, send_file
from flask_login import current_user
from psycopg2 import DatabaseError
from sqlalchemy import text

from listenbrainz.garage import get_error_code, get_garage_client, get_user_data_export_bucket
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
            return jsonify(export_data)
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
    try:
        archive, filename = user_data_export.get_completed_export_archive(db_conn, current_user.id, export_id)
        if archive is None:
            raise APINotFound("Export not found")
    except Exception as e:
        current_app.logger.error("Error while downloading user data export: %s", filename, exc_info=True)
        raise APIInternalServerError("Error while downloading export, please try again later.")

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


@export_bp.post("/delete/<export_id>/")
@api_login_required
@web_listenstore_needed
def delete_export_archive(export_id):
    """ Delete the specified export archive """
    result = user_data_export.delete_export_task(db_conn, current_user.id, export_id)
    if result is True:
        return jsonify({"success": True})
    else:
        raise APINotFound("Export not found")
