import json
import os

from flask import Blueprint, current_app, jsonify, send_file, request
from psycopg2 import DatabaseError
from sqlalchemy import text
from datetime import datetime, date

from werkzeug.utils import secure_filename
from listenbrainz.webserver import db_conn
from listenbrainz.webserver.decorators import web_listenstore_needed, crossdomain
from brainzutils.ratelimit import ratelimit
from brainzutils.musicbrainz_db import engine as mb_engine
from listenbrainz.webserver.errors import APIInternalServerError, APINotFound, APIBadRequest, APINoContent, APIUnauthorized
from listenbrainz.webserver.utils import REJECT_LISTENS_WITHOUT_EMAIL_ERROR, REJECT_LISTENS_FROM_PAUSED_USER_ERROR
from listenbrainz.webserver.login import api_login_required
from listenbrainz.webserver.views.api_tools import validate_auth_header

import_api_bp = Blueprint("import_listens_api_v1", __name__)


@import_api_bp.post("/")
@web_listenstore_needed
@crossdomain
@ratelimit()
def create_import_task():
    """ Add a request to upload files and create a background task for the importer """

    user = validate_auth_header(fetch_email=True, scopes=["listenbrainz:submit-listens"])

    if mb_engine and current_app.config["REJECT_LISTENS_WITHOUT_USER_EMAIL"] and not user["email"]:
        raise APIUnauthorized(REJECT_LISTENS_WITHOUT_EMAIL_ERROR)

    if user['is_paused']:
        raise APIUnauthorized(REJECT_LISTENS_FROM_PAUSED_USER_ERROR)

    UPLOAD_DIR = os.path.join(os.getcwd(), 'uploads')
    os.makedirs(UPLOAD_DIR, exist_ok=True)

    uploaded_file = request.files.get('file')
    service = request.form.get('service')
    from_date = request.form.get('from_date')
    to_date = request.form.get('to_date')

    


    try:
        from_date = datetime.strptime(from_date, '%Y-%m-%d').date()
    except:
        from_date = date(1970, 1, 1) # Epoch date
    
    try:
        to_date = datetime.strptime(to_date, '%Y-%m-%d').date()
    except:
        to_date = date.today()

    if not uploaded_file:
        raise APIBadRequest("No file uploaded!")
    
    if not service:
        raise APIBadRequest("No service selected!")
    
    service = service.lower()
    
    allowed_extensions = ['.json', '.jsonl', '.csv', '.zip']
    allowed_services = ['spotify', 'applemusic', 'listenbrainz']
    filename = uploaded_file.filename

    if not filename:
        raise APIBadRequest("Invalid file name!")
    
    extension = os.path.splitext(filename)[1].lower()
    
    if extension not in allowed_extensions:
        raise APIBadRequest("File type not allowed!")
    
    if service not in allowed_services:
        raise APIBadRequest("This service is not supported!")
    
    saved_filename = secure_filename(filename)
    
    try:
        save_path = os.path.join(UPLOAD_DIR, saved_filename)
        uploaded_file.save(save_path)
    except Exception as e:
        raise APIInternalServerError("Failed to upload the file!")

    try:

        query = """
            SELECT id FROM user_data_import
            WHERE user_id = :user_id AND service = :service
                AND metadata->>'status' IN ('waiting', 'in_progress');
        """

        result = db_conn.execute(text(query), {
            "user_id": user['id'],
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
            "user_id": user['id'],
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
                "user_id": user['id'],
                "task": "import_listens",
                "metadata": json.dumps({"import_id": import_task.id})
            })
            task = result.first()
            if task is not None:
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
        current_app.logger.error('Error while importing user data: %s', user['musicbrainz_id'], exc_info=True)
        raise APIInternalServerError(f'Error while importing user data {user['musicbrainz_id']}, please try again later.')
    

@import_api_bp.get("/<import_id>/")
@web_listenstore_needed
@crossdomain
@ratelimit()
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
        "service": row.type,
        "created": row.created.isoformat(),
        "metadata": row.metadata,
        "file_path": row.file_path,
    })


@import_api_bp.get("/list/")
@web_listenstore_needed
@crossdomain
@ratelimit()
def list_import_tasks():
    """ Retrieve the all import tasks for the current user """

    user = validate_auth_header(fetch_email=True, scopes=["listenbrainz:submit-listens"])

    result = db_conn.execute(
        text("SELECT * FROM user_data_import WHERE user_id = :user_id ORDER BY created DESC"),
        {"user_id": user["id"]}
    )
    rows = result.mappings().all()
    return jsonify([{
        "import_id": row.id,
        "service": row.type,
        "created": row.created.isoformat(),
        "metadata": row.metadata,
        "file_path": row.file_path,
    } for row in rows])