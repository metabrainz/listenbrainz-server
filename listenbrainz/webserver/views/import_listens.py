import json
import os

from flask import Blueprint, current_app, jsonify, send_file, request
from flask_login import current_user
from psycopg2 import DatabaseError
from sqlalchemy import text

from werkzeug.utils import secure_filename
from listenbrainz.webserver import db_conn
from listenbrainz.webserver.decorators import web_listenstore_needed
from listenbrainz.webserver.errors import APIInternalServerError, APINotFound, APIBadRequest, APINoContent
from listenbrainz.webserver.login import api_login_required
from listenbrainz.webserver.views.api_tools import validate_auth_header

import_bp = Blueprint("import", __name__)


@import_bp.post("/")
@api_login_required
@web_listenstore_needed
def create_import_task():
    """ Add a request to upload files and create a background task for the importer """

    UPLOAD_DIR = os.path.join(os.getcwd(), 'uploads')
    os.makedirs(UPLOAD_DIR, exist_ok=True)

    uploaded_file = request.files.get('file')
    service = request.form.get('service')

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
            INSERT INTO user_data_import (user_id, type, progress)
                 VALUES (:user_id, :type, 'waiting', :progress)
            ON CONFLICT (user_id, type)
                  WHERE status = 'waiting' OR status = 'in_progress'
             DO NOTHING
              RETURNING id, type, file_available_until, created, progress, status, file_path
        """
        result = db_conn.execute(text(query), {
            "user_id": current_user.id,
            "type": "import_user_data",
            "progress": "Your data import will start soon."
        })
        import_task = result.first()

        if import_task is not None:
            query = "INSERT INTO background_tasks (user_id, task, metadata) VALUES (:user_id, :task, :metadata) ON CONFLICT DO NOTHING RETURNING id"
            result = db_conn.execute(text(query), {
                "user_id": current_user.id,
                "task": "import_user_data",
                "metadata": json.dumps({"import_id": import_task.id})
            })
            task = result.first()
            if task is not None:
                db_conn.commit()
                return jsonify({
                    "import_id": import_task.id,
                    "type": import_task.type,
                    "file_available_until": import_task.available_until.isoformat() if import_task.available_until is not None else None,
                    "created": import_task.created.isoformat(),
                    "progress": import_task.progress,
                    "status": import_task.status,
                    "file_path": import_task.filename,
                })

        # task already exists in queue, rollback new entry
        db_conn.rollback()
        raise APIBadRequest(message="Data import already requested.")

    except DatabaseError:
        current_app.logger.error('Error while importing user data: %s', current_user.musicbrainz_id, exc_info=True)
        raise APIInternalServerError(f'Error while importing user data {current_user.musicbrainz_id}, please try again later.')