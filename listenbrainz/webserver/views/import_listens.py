import json
import os
import uuid

from flask import Blueprint, current_app, jsonify, request
from psycopg2 import DatabaseError
from sqlalchemy import text
from datetime import datetime, timezone
from pathlib import Path

from werkzeug.utils import secure_filename
from listenbrainz.webserver import db_conn
from listenbrainz.webserver.decorators import web_listenstore_needed, crossdomain
from brainzutils.ratelimit import ratelimit
from brainzutils.musicbrainz_db import engine as mb_engine
from listenbrainz.webserver.errors import APIInternalServerError, APINotFound, APIBadRequest, APIUnauthorized
from listenbrainz.webserver.utils import REJECT_LISTENS_WITHOUT_EMAIL_ERROR, REJECT_LISTENS_FROM_PAUSED_USER_ERROR
from listenbrainz.webserver.views.api_tools import validate_auth_header

import_api_bp = Blueprint("import_listens_api_v1", __name__)


def _validate_datetime_param(param, default=None):
    value = request.form.get(param)
    if not value:
        return default
    try:
        value = datetime.fromisoformat(value)
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return value
    except (TypeError, ValueError):
        raise APIBadRequest(f"Invalid {param} format!")


@import_api_bp.post("/")
@web_listenstore_needed
@crossdomain
@ratelimit()
def create_import_task():
    """ Add a request to upload files and create a background task for the importer """
    user = validate_auth_header(fetch_email=True, scopes=["listenbrainz:submit-listens"])

    if mb_engine and current_app.config["REJECT_LISTENS_WITHOUT_USER_EMAIL"] and not user["email"]:
        raise APIUnauthorized(REJECT_LISTENS_WITHOUT_EMAIL_ERROR)

    if user["is_paused"]:
        raise APIUnauthorized(REJECT_LISTENS_FROM_PAUSED_USER_ERROR)

    uploaded_file = request.files.get("file")
    if not uploaded_file:
        raise APIBadRequest("No file uploaded!")

    service = request.form.get("service")
    if not service:
        raise APIBadRequest("No service selected!")
    service = service.lower()

    allowed_services = ["spotify", "listenbrainz"]
    if service not in allowed_services:
        raise APIBadRequest("This service is not supported!")

    from_date = _validate_datetime_param("from_date", datetime.fromtimestamp(0, timezone.utc))
    to_date = _validate_datetime_param("to_date", datetime.now(timezone.utc))

    filename = uploaded_file.filename
    if not filename:
        raise APIBadRequest("Invalid file name!")

    allowed_extensions = [".zip"]
    extension = os.path.splitext(filename)[1].lower()
    if extension not in allowed_extensions:
        raise APIBadRequest("File type not allowed!")

    # add a unique ID to the filename to avoid collisions
    saved_filename = str(uuid.uuid4()) + "-" + secure_filename(filename)
    save_path = os.path.join(current_app.config["UPLOAD_FOLDER"], saved_filename)

    try:
        query = """
            SELECT id FROM user_data_import
             WHERE user_id = :user_id AND service = :service
               AND metadata->>'status' IN ('waiting', 'in_progress');
        """
        result = db_conn.execute(text(query), {
            "user_id": user["id"],
            "service": service,
        })
        check_existing = result.first()
        if check_existing is not None:
            raise APIBadRequest("An import task is already in progress!")

        query = """
            INSERT INTO user_data_import (user_id, service, from_date, to_date, file_path, metadata)
                 VALUES (:user_id, :service, :from_date, :to_date, :file_path, :metadata)
              RETURNING id, service, created, file_path, metadata
        """
        result = db_conn.execute(text(query), {
            "user_id": user["id"],
            "service": service,
            "from_date": from_date,
            "to_date": to_date,
            "file_path": save_path,
            "metadata": json.dumps({"status": "waiting", "progress": "Your data import will start soon.", "filename": filename})
        })
        import_task = result.first()

        if import_task is not None:
            query = "INSERT INTO background_tasks (user_id, task, metadata) VALUES (:user_id, :task, :metadata) ON CONFLICT DO NOTHING RETURNING id"
            result = db_conn.execute(text(query), {
                "user_id": user["id"],
                "task": "import_listens",
                "metadata": json.dumps({"import_id": import_task.id})
            })
            task = result.first()
            if task is not None:
                os.makedirs(current_app.config["UPLOAD_FOLDER"], exist_ok=True)
                uploaded_file.save(save_path)

                db_conn.commit()

                return jsonify({
                    "import_id": import_task.id,
                    "service": import_task.service,
                    "created": import_task.created.isoformat(),
                    "metadata": import_task.metadata,
                    "file_path": import_task.file_path,
                })

        # task already exists in queue, rollback new entry
        db_conn.rollback()
        raise APIBadRequest(message="Data import already requested.")

    except DatabaseError:
        current_app.logger.error("Error while creating import user data task: %s", user["musicbrainz_id"], exc_info=True)
        raise APIInternalServerError(f"Error while creating import user data task {user['musicbrainz_id']}, please try again later.")
    

@import_api_bp.get("/<import_id>/")
@web_listenstore_needed
@crossdomain
@ratelimit()
def get_import_task(import_id):
    """ Retrieve the requested import's data if it belongs to the specified user """
    user = validate_auth_header()
    result = db_conn.execute(
        text("SELECT * FROM user_data_import WHERE user_id = :user_id AND id = :import_id"),
        {"user_id": user["id"], "import_id": import_id}
    )
    row = result.first()
    if row is None:
        raise APINotFound("Import not found")
    return jsonify({
        "import_id": row.id,
        "service": row.service,
        "created": row.created.isoformat(),
        "metadata": row.metadata,
        "to_date": row.to_date.isoformat(),
        "from_date": row.from_date.isoformat(),
    })


@import_api_bp.get("/list/")
@web_listenstore_needed
@crossdomain
@ratelimit()
def list_import_tasks():
    """ Retrieve the all import tasks for the current user """
    user = validate_auth_header()
    result = db_conn.execute(
        text("SELECT * FROM user_data_import WHERE user_id = :user_id ORDER BY created DESC"),
        {"user_id": user["id"]}
    )
    rows = result.mappings().all()
    return jsonify([{
        "import_id": row.id,
        "service": row.service,
        "created": row.created.isoformat(),
        "metadata": row.metadata,
        "to_date": row.to_date.isoformat(),
        "from_date": row.from_date.isoformat(),
    } for row in rows])


@import_api_bp.post("/cancel/<import_id>/")
@web_listenstore_needed
@crossdomain
@ratelimit()
def delete_import_task(import_id):
    """ Cancel the specified import in progress """
    user = validate_auth_header()
    result = db_conn.execute(
        text("DELETE FROM user_data_import WHERE user_id = :user_id AND id = :import_id AND metadata->>'status' IN ('waiting') RETURNING file_path"),
        {"user_id": user["id"], "import_id": import_id}
    )
    row = result.first()
    if row is not None:
        db_conn.execute(
            text("DELETE FROM background_tasks WHERE user_id = :user_id AND (metadata->>'import_id')::int = :import_id"),
            {"user_id": user["id"], "import_id": import_id}
        )
        Path(row.file_path).unlink(missing_ok=True)
        db_conn.commit()
        return jsonify({"success": True})
    else:
        raise APINotFound("Import not found or is already being processed.")