import json

from sqlalchemy import text


def _with_validation_counts(metadata):
    """Ensure metadata dict includes attempted/success counters with sensible defaults."""
    metadata = dict(metadata or {})
    metadata.setdefault("attempted_count", 0)
    metadata.setdefault("success_count", 0)
    return metadata


def create_import_task(db_conn, user_id, service, from_date, to_date, save_path, filename, user_timezone=None):
    """ Create a new import task for the specified user.

        Note, this method does not commit so that the API can commit only if the file upload
        completes successfully.
    """
    query = """\
        INSERT INTO user_data_import (user_id, service, from_date, to_date, file_path, metadata)
        VALUES (:user_id, :service, :from_date, :to_date, :file_path, :metadata)
        RETURNING id, service, created, file_path, metadata"""
    result = db_conn.execute(text(query), {
        "user_id": user_id,
        "service": service,
        "from_date": from_date,
        "to_date": to_date,
        "file_path": save_path,
        "metadata": json.dumps({
            "status": "waiting",
            "progress": "Your data import will start soon.",
            "filename": filename,
            "attempted_count": 0,
            "success_count": 0,
            **({"user_timezone": user_timezone} if user_timezone else {})
        })
    })
    import_task = result.first()

    if import_task is not None:
        query = "INSERT INTO background_tasks (user_id, task, metadata) VALUES (:user_id, :task, :metadata) ON CONFLICT DO NOTHING RETURNING id"
        db_conn.execute(text(query), {
            "user_id": user_id,
            "task": "import_listens",
            "metadata": json.dumps({"import_id": import_task.id})
        })

        return {
            "import_id": import_task.id,
            "service": import_task.service,
            "created": import_task.created.isoformat(),
            "metadata": _with_validation_counts(import_task.metadata),
            "file_path": import_task.file_path,
        }

    return None
