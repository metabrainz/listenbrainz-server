import json

from botocore.exceptions import ClientError
from flask import Blueprint, current_app, jsonify, send_file
from flask_login import current_user
from psycopg2 import DatabaseError
from sqlalchemy import text

from listenbrainz.garage import get_error_code, get_garage_client, get_user_data_export_bucket
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
        query = """
            INSERT INTO user_data_export (user_id, type, status, progress)
                 VALUES (:user_id, :type, 'waiting', :progress)
            ON CONFLICT (user_id, type)
                  WHERE status = 'waiting' OR status = 'in_progress'
             DO NOTHING
              RETURNING id, type, available_until, created, progress, status, filename
        """
        result = db_conn.execute(text(query), {
            "user_id": current_user.id,
            "type": "export_all_user_data",
            "progress": "Your data export will start soon."
        })
        export = result.first()

        if export is not None:
            query = "INSERT INTO background_tasks (user_id, task, metadata) VALUES (:user_id, :task, :metadata) ON CONFLICT DO NOTHING RETURNING id"
            result = db_conn.execute(text(query), {
                "user_id": current_user.id,
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
        current_app.logger.error('Error while exporting user data: %s', current_user.musicbrainz_id, exc_info=True)
        raise APIInternalServerError(f'Error while exporting user data {current_user.musicbrainz_id}, please try again later.')


@export_bp.get("/<export_id>/")
@api_login_required
@web_listenstore_needed
def get_export_task(export_id):
    """ Retrieve the requested export's data if it belongs to the specified user """
    result = db_conn.execute(
        text("SELECT * FROM user_data_export WHERE user_id = :user_id AND id = :export_id"),
        {"user_id": current_user.id, "export_id": export_id}
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


@export_bp.get("/list/")
@api_login_required
@web_listenstore_needed
def list_export_tasks():
    """ Retrieve the all export tasks for the current user """
    result = db_conn.execute(
        text("SELECT * FROM user_data_export WHERE user_id = :user_id ORDER BY created DESC"),
        {"user_id": current_user.id}
    )
    rows = result.mappings().all()
    return jsonify([{
        "export_id": row.id,
        "type": row.type,
        "available_until": row.available_until.isoformat() if row.available_until is not None else None,
        "created": row.created.isoformat(),
        "progress": row.progress,
        "status": row.status,
        "filename": row.filename,
    } for row in rows])


@export_bp.post("/download/<export_id>/")
@api_login_required
@web_listenstore_needed
def download_export_archive(export_id):
    """ Download the requested export if it is complete and belongs to the specified user """
    result = db_conn.execute(
        text("SELECT filename FROM user_data_export WHERE user_id = :user_id AND status = 'completed' AND id = :export_id"),
        {"user_id": current_user.id, "export_id": export_id}
    )
    row = result.first()
    if row is None:
        raise APINotFound("Export not found")

    filename = str(row.filename)
    try:
        archive = get_garage_client().get_object(Bucket=get_user_data_export_bucket(), Key=filename)
    except ClientError as e:
        if get_error_code(e) in ("NoSuchKey", "NoSuchBucket", "404"):
            raise APINotFound("Export not found")
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
    result = db_conn.execute(
        text("DELETE FROM user_data_export WHERE user_id = :user_id AND id = :export_id RETURNING filename"),
        {"user_id": current_user.id, "export_id": export_id}
    )
    row = result.first()
    if row is not None:
        db_conn.execute(
            text("DELETE FROM background_tasks WHERE user_id = :user_id AND (metadata->'export_id')::int = :export_id"),
            {"user_id": current_user.id, "export_id": export_id}
        )
        db_conn.commit()
        # archive is deleted from garage by cronjob
        return jsonify({"success": True})
    else:
        raise APINotFound("Export not found")
