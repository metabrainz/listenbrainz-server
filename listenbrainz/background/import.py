import os.path
import shutil
import tempfile
import zipfile
from datetime import datetime, date, time, timedelta, timezone
from pathlib import Path

import orjson
from brainzutils.mail import send_mail
from dateutil.relativedelta import relativedelta
from flask import current_app, render_template
from data.model.external_service import ExternalServiceType
from sqlalchemy import text

from listenbrainz.db import user as db_user
from listenbrainz.webserver import timescale_connection

BATCH_SIZE = 1000
USER_DATA_IMPORT_FILES_AVAILABILITY = timedelta(days=2)  # how long should a user data import files be saved for on our servers

def update_import_status(db_conn, user_id: int, service: ExternalServiceType, progress: dict, error_message: str = None):
    """ Add an error message to be shown to the user, thereby setting the user as inactive.

    Args:
        db_conn: database connection
        user_id (int): the ListenBrainz row ID of the user
        service (data.model.ExternalServiceType): service to add error for the user
        error_message (str): the user-friendly error message to be displayed
    """
    db_conn.execute(sqlalchemy.text("""
        UPDATE listens_importer
           SET last_updated = now()
             , error_message = :error_message
             , progress = :progress
         WHERE user_id = :user_id
           AND service = :service
    """), {
        "user_id": user_id,
        "error_message": error_message,
        "service": service.value,
        "progress": progress
    })
    db_conn.commit()

def process_spotify_upload(file_path: str):
    pass # Yet to be implemented