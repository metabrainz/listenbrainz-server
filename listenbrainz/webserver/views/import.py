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
def create_import_task(file_path, service):
    """ Add a request to import the listening history data in background. """
    try:

        fetch_oauth_query = text("""
            SELECT id FROM external_service_oauth
            WHERE user_id = :user_id AND service = :service
        """)
        result = db_conn.execute(fetch_oauth_query, {
            "user_id": current_user.id,
            "service": service
        }).first()

        if result:
            external_oauth_id = result.id
        else:
            insert_oauth_query = text("""
                INSERT INTO external_service_oauth (user_id, service, last_updated)
                VALUES (:user_id, :service, NOW())
                RETURNING id
            """)
            result = db_conn.execute(insert_oauth_query, {
                "user_id": current_user.id,
                "service": service
            }).first()
            external_oauth_id = result.id

        insert_importer_query = text("""
            INSERT INTO listens_importer (
                external_service_oauth_id, user_id, service, last_updated, status
            )
            VALUES (:external_id, :user_id, :service, NOW(), :progress)
        """)
        import_task = db_conn.execute(insert_importer_query, {
            "external_id": external_oauth_id,
            "user_id": current_user.id,
            "service": service,
            "progress": "Your data import will start soon."
        }).first()

        
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
                    "service": import_task.service,
                    "last_updated": import_task.last_updated.isoformat(),
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
        text("SELECT * FROM listens_importer WHERE user_id = :user_id ORDER BY last_updated DESC"),
        {"user_id": current_user.id}
    )
    rows = result.mappings().all()
    return jsonify([{
        "import_id": row.id,
        "service": row.service,
        "last_updated": row.last_updated.isoformat(),
        "status": row.status,
    } for row in rows])


@import_bp.get("/<import_id>/")
@api_login_required
@web_listenstore_needed
def get_import_task(import_id):
    """ Retrieve the requested import's data if it belongs to the specified user """
    result = db_conn.execute(
        text("SELECT * FROM listens_importer WHERE user_id = :user_id AND id = :import_id"),
        {"user_id": current_user.id, "import_id": import_id}
    )
    row = result.first()
    if row is None:
        raise APINotFound("Import not found")
    return jsonify({
        "import_id": row.id,
        "service": row.service,
        "last_updated": row.last_updated.isoformat(),
        "status": row.status,
    })