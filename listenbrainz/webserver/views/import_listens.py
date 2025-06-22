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

import_bp = Blueprint("import", __name__)


@import_bp.post("/")
@api_login_required
@web_listenstore_needed
def create_import_task():
    """ Add a request to upload files and create a background task for the importer """


    UPLOAD_DIR = os.path.join(os.getcwd(), 'uploads')
    os.makedirs(UPLOAD_DIR, exist_ok=True)

    uploaded_file = request.files.get('file')
    service = request.form.get('service').lower()

    if not uploaded_file:
        raise APINoContent("No file uploaded!")
    
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
    
    # Determine file size
    saved_filename = secure_filename(filename)
    uploaded_file.seek(0, os.SEEK_END)
    file_size = uploaded_file.tell()
    uploaded_file.seek(0)

    if file_size > current_app.config['MAX_IMPORT_CONTENT_LENGTH']:
        raise APIBadRequest("File size exceeds the maximum allowed size!")
    
    try:
        save_path = os.path.join(UPLOAD_DIR, saved_filename)
        uploaded_file.save(save_path)
    except Exception as e:
        raise APIInternalServerError("Failed to upload the file!")


    return jsonify({"path": save_path}) # WIP