""" Storage of the files users upload to import their listens.

The webserver uploads the file to the import bucket in garage and the background tasks
container downloads it from there when it runs the import, so that the two do not need a
shared directory.
"""
import os
from datetime import datetime, timedelta, timezone

from botocore.exceptions import BotoCoreError, ClientError
from flask import current_app
from sqlalchemy import text

from listenbrainz.garage import delete_objects, ensure_bucket, get_garage_client, \
    get_user_data_import_bucket, list_objects

# statuses of the imports that will not run again and whose file is therefore of no further use,
# an import in any other status may still need its file
FINISHED_STATUSES = ("completed", "cancelled", "failed")
# the file is uploaded before the import row it belongs to is committed, a file that has only
# just been uploaded cannot be told apart from one whose row is still on its way
IMPORT_FILE_MIN_AGE = timedelta(days=1)


def object_name_for(file_path: str) -> str:
    """ Get the object name of the file recorded for an import.

    Imports created before the uploaded files moved to garage recorded the full path of the
    file on disk. migrate_user_data_imports rewrites those to the object name, but an import
    queued before the migration ran may still be picked up with the old value, and the file is
    stored under its basename either way.
    """
    return os.path.basename(file_path)


def upload_import_file(object_name: str, uploaded_file):
    """ Upload the file the user submitted for an import to garage. """
    client = get_garage_client()
    bucket = get_user_data_import_bucket()
    ensure_bucket(client, bucket)

    extra_args = {"ContentType": uploaded_file.mimetype} if uploaded_file.mimetype else None
    # upload_fileobj reads the stream in chunks and uses a multipart upload for large files,
    # so the file is never buffered in memory in its entirety
    client.upload_fileobj(uploaded_file.stream, bucket, object_name, ExtraArgs=extra_args)


def download_import_file(object_name: str, directory: str) -> str:
    """ Download the file uploaded for an import into the given directory, returning its path.

    The importers seek around in the file, so it cannot be streamed out of garage.
    """
    object_name = object_name_for(object_name)
    local_path = os.path.join(directory, object_name)
    get_garage_client().download_file(get_user_data_import_bucket(), object_name, local_path)
    return local_path


def delete_import_file(object_name: str):
    """ Remove the file uploaded for an import from garage.

    The file is of no use once the import has run or been cancelled. Failing to delete it must
    not fail the caller, the import it belongs to is already gone.
    """
    if not object_name:
        return
    try:
        get_garage_client().delete_object(
            Bucket=get_user_data_import_bucket(), Key=object_name_for(object_name)
        )
    except (ClientError, BotoCoreError):
        current_app.logger.error("Error while deleting import file: %s", object_name, exc_info=True)


def cleanup_import_files(db_conn):
    """ Delete the files of imports that are never going to run from garage.

    The importer deletes the file of an import as soon as it is done with it, but a file is
    left behind whenever it does not get that far: the import was cancelled or had already
    failed when the task ran, or the row the upload belongs to was never committed.
    """
    result = db_conn.execute(text("""
        SELECT file_path
          FROM user_data_import
         WHERE metadata->>'status' != ALL(:statuses)
           AND file_path IS NOT NULL
    """), {"statuses": list(FINISHED_STATUSES)})
    files_to_keep = {object_name_for(row.file_path) for row in result}

    client = get_garage_client()
    bucket = get_user_data_import_bucket()
    ensure_bucket(client, bucket)

    cutoff = datetime.now(timezone.utc) - IMPORT_FILE_MIN_AGE
    objects_to_delete = []
    for obj in list_objects(client, bucket):
        if obj["Key"] in files_to_keep or obj["LastModified"] > cutoff:
            continue
        current_app.logger.info("Removing import file: %s", obj["Key"])
        objects_to_delete.append(obj["Key"])

    for error in delete_objects(client, bucket, objects_to_delete):
        current_app.logger.error("Failed to remove import file %s: %s", error.get("Key"), error.get("Message"))
