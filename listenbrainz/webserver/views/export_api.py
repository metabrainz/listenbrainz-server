import json
import os
from flask import Blueprint, current_app, jsonify, send_file
from sqlalchemy import text
from psycopg2 import DatabaseError

from listenbrainz.webserver import db_conn
from listenbrainz.webserver.decorators import api_listenstore_needed
from listenbrainz.webserver.errors import APIBadRequest, APIInternalServerError, APINotFound
from listenbrainz.webserver.views.api_tools import validate_auth_header

export_api_bp = Blueprint("export_api", __name__)


@export_api_bp.route("/", methods=["POST"])
@api_listenstore_needed
def create_export_task():
    """ Add a request to export the user data to an archive in background. """
    user = validate_auth_header()
    user_id = user["id"]
    try:
        query = """
            INSERT INTO user_data_export (user_id, type, status, progress)
                 VALUES (:user_id, :type, 'waiting', :progress)
            ON CONFLICT (user_id, type)
                  WHERE status = 'waiting' OR status = 'in_progress'
             DO NOTHING
              RETURNING id, type, available_until, created, progress, status, filename
        """
        result = db_conn.execute(text(query), {
            "user_id": user_id,
            "type": "export_all_user_data",
            "progress": "Your data export will start soon."
        })
        export = result.first()

        if export is not None:
            query = "INSERT INTO background_tasks (user_id, task, metadata) VALUES (:user_id, :task, :metadata) ON CONFLICT DO NOTHING RETURNING id"
            result = db_conn.execute(text(query), {
                "user_id": user_id,
                "task": "export_all_user_data",
                "metadata": json.dumps({"export_id": export.id})
            })
            task = result.first()
            if task is not None:
                db_conn.commit()
                return jsonify({
                    "export_id": export.id,
                    "type": export.type,
                    "available_until": export.available_until.isoformat() if export.available_until is not None else None,
                    "created": export.created.isoformat(),
                    "progress": export.progress,
                    "status": export.status,
                    "filename": export.filename,
                })

        # task already exists in queue, rollback new entry
        db_conn.rollback()
        raise APIBadRequest(message="Data export already requested.")

    except DatabaseError:
        current_app.logger.error('Error while exporting user data: %s', user["musicbrainz_id"], exc_info=True)
        raise APIInternalServerError(f'Error while exporting user data {user["musicbrainz_id"]}, please try again later.')


@export_api_bp.route("/<int:export_id>", methods=["GET"])
@api_listenstore_needed
def get_export_task(export_id):
    """ Retrieve the requested export's data if it belongs to the specified user """
    user = validate_auth_header()
    user_id = user["id"]
    
    result = db_conn.execute(
        text("SELECT * FROM user_data_export WHERE user_id = :user_id AND id = :export_id"),
        {"user_id": user_id, "export_id": export_id}
    )
    row = result.first()
    if row is None:
        raise APINotFound("Export not found")
    return jsonify({
        "export_id": row.id,
        "type": row.type,
        "available_until": row.available_until.isoformat() if row.available_until is not None else None,
        "created": row.created.isoformat(),
        "progress": row.progress,
        "status": row.status,
        "filename": row.filename,
    })


@export_api_bp.route("/", methods=["GET"])
@api_listenstore_needed
def list_export_tasks():
    """ Retrieve the all export tasks for the current user """
    user = validate_auth_header()
    user_id = user["id"]

    result = db_conn.execute(
        text("SELECT * FROM user_data_export WHERE user_id = :user_id ORDER BY created DESC"),
        {"user_id": user_id}
    )
    rows = result.mappings().all()
    return jsonify([{
        "export_id": row["id"],
        "type": row["type"],
        "available_until": row["available_until"].isoformat() if row["available_until"] is not None else None,
        "created": row["created"].isoformat(),
        "progress": row["progress"],
        "status": row["status"],
        "filename": row["filename"],
    } for row in rows])


@export_api_bp.route("/<int:export_id>/download", methods=["GET"])
@api_listenstore_needed
def download_export_archive(export_id):
    """ Download the requested export if it is complete and belongs to the specified user """
    user = validate_auth_header()
    user_id = user["id"]

    result = db_conn.execute(
        text("SELECT filename FROM user_data_export WHERE user_id = :user_id AND status = 'completed' AND id = :export_id"),
        {"user_id": user_id, "export_id": export_id}
    )
    row = result.first()
    if row is None:
        raise APINotFound("Export not found")

    file_path = os.path.join(current_app.config["USER_DATA_EXPORT_BASE_DIR"], str(row["filename"]))
    return send_file(file_path, mimetype="application/zip", as_attachment=True)
