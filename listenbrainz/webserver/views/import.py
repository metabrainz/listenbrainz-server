import json
import os

from flask import Blueprint, current_app, jsonify, send_file
from flask_login import current_user
from psycopg2 import DatabaseError
from sqlalchemy import text

from listenbrainz.webserver import db_conn
from listenbrainz.webserver.decorators import web_listenstore_needed
from listenbrainz.webserver.errors import APIInternalServerError, APINotFound, APIBadRequest
from listenbrainz.webserver.login import api_login_required

import_bp = Blueprint("import", __name__)


@import_bp.post("/")
@api_login_required
@web_listenstore_needed
def create_import_task(file_path):
    """ Add a request to import the listening history data in background. """
    try:
        query = """
            INSERT INTO user_data_import (user_id, file_path, type, status, progress)
                 VALUES (:user_id, :file_path, :type, 'waiting', :progress)
            ON CONFLICT (user_id, type)
                  WHERE status = 'waiting' OR status = 'in_progress'
             DO NOTHING
              RETURNING id, type, created, progress, status
        """
        result = db_conn.execute(text(query), {
            "user_id": current_user.id,
            "type": "import_all_user_data",
            "file_path": file_path,
            "progress": "Your data import will start soon."
        })
        import_task = result.first()

        if import_task is not None:
            query = "INSERT INTO background_tasks (user_id, task, metadata) VALUES (:user_id, :task, :metadata) ON CONFLICT DO NOTHING RETURNING id"
            result = db_conn.execute(text(query), {
                "user_id": current_user.id,
                "task": "import_all_user_data",
                "metadata": json.dumps({"import_id": import_task.id, "file_path": file_path})
            })
            task = result.first()
            if task is not None:
                db_conn.commit()
                return jsonify({
                    "import_id": import_task.id,
                    "type": import_task.type,
                    "created": import_task.created.isoformat(),
                    "progress": import_task.progress,
                    "status": import_task.status,
                })

        # task already exists in queue, rollback new entry
        db_conn.rollback()
        raise APIBadRequest(message="Data import already requested.")

    except DatabaseError:
        current_app.logger.error('Error while importing user data: %s', current_user.musicbrainz_id, exc_info=True)
        raise APIInternalServerError(f'Error while importing user data {current_user.musicbrainz_id}, please try again later.')

@import_bp.get("/list/")
@api_login_required
@web_listenstore_needed
def list_export_tasks():
    """ Retrieve the all import tasks for the current user """
    result = db_conn.execute(
        text("SELECT * FROM user_data_import WHERE user_id = :user_id ORDER BY created DESC"),
        {"user_id": current_user.id}
    )
    rows = result.mappings().all()
    return jsonify([{
        "import_id": row.id,
        "type": row.type,
        "created": row.created.isoformat(),
        "progress": row.progress,
        "status": row.status,
        "file_path": row.file_path,
    } for row in rows])


@import_bp.get("/<import_id>/")
@api_login_required
@web_listenstore_needed
def get_import_task(import_id):
    """ Retrieve the requested import's data if it belongs to the specified user """
    result = db_conn.execute(
        text("SELECT * FROM user_data_import WHERE user_id = :user_id AND id = :import_id"),
        {"user_id": current_user.id, "import_id": import_id}
    )
    row = result.first()
    if row is None:
        raise APINotFound("Import not found")
    return jsonify({
        "import_id": row.id,
        "type": row.type,
        "created": row.created.isoformat(),
        "progress": row.progress,
        "status": row.status,
        "file_path": row.file_path,
    })