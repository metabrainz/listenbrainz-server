import json
from typing import Optional, Dict, Any, List
from sqlalchemy import text


def request_user_data_export(db_conn, user_id: int) -> Optional[Dict[str, Any]]:
    """ Add a request to export the user data to an archive in background. """
    query = """
        INSERT INTO user_data_export (user_id, type, status, progress)
             VALUES (:user_id, :type, 'waiting', :progress)
        ON CONFLICT (user_id, type)
              WHERE status = 'waiting' OR status = 'in_progress'
         DO NOTHING
          RETURNING id, type, available_until, created, progress, status, filename
    """
    result = db_conn.execute(text(query), {
        "user_id": user_id,
        "type": "export_all_user_data",
        "progress": "Your data export will start soon."
    })
    export = result.first()

    if export is not None:
        query = "INSERT INTO background_tasks (user_id, task, metadata) VALUES (:user_id, :task, :metadata) ON CONFLICT DO NOTHING RETURNING id"
        result = db_conn.execute(text(query), {
            "user_id": user_id,
            "task": "export_all_user_data",
            "metadata": json.dumps({"export_id": export.id})
        })
        task = result.first()
        if task is not None:
            return {
                "export_id": export.id,
                "type": export.type,
                "available_until": export.available_until.isoformat() if export.available_until is not None else None,
                "created": export.created.isoformat(),
                "progress": export.progress,
                "status": export.status,
                "filename": export.filename,
            }
    return None


def get_export_task(db_conn, user_id: int, export_id: int) -> Optional[Dict[str, Any]]:
    """ Retrieve the requested export's data if it belongs to the specified user """
    result = db_conn.execute(
        text("SELECT * FROM user_data_export WHERE user_id = :user_id AND id = :export_id"),
        {"user_id": user_id, "export_id": export_id}
    )
    row = result.first()
    if row is None:
        return None
        
    return {
        "export_id": row.id,
        "type": row.type,
        "available_until": row.available_until.isoformat() if row.available_until is not None else None,
        "created": row.created.isoformat(),
        "progress": row.progress,
        "status": row.status,
        "filename": row.filename,
    }


def list_export_tasks(db_conn, user_id: int) -> List[Dict[str, Any]]:
    """ Retrieve all export tasks for the current user """
    result = db_conn.execute(
        text("SELECT * FROM user_data_export WHERE user_id = :user_id ORDER BY created DESC"),
        {"user_id": user_id}
    )
    rows = result.mappings().all()
    return [{
        "export_id": row["id"],
        "type": row["type"],
        "available_until": row["available_until"].isoformat() if row["available_until"] is not None else None,
        "created": row["created"].isoformat(),
        "progress": row["progress"],
        "status": row["status"],
        "filename": row["filename"],
    } for row in rows]


def get_completed_export_filename(db_conn, user_id: int, export_id: int) -> Optional[str]:
    """ Retrieve the filename of a completed export task """
    result = db_conn.execute(
        text("SELECT filename FROM user_data_export WHERE user_id = :user_id AND status = 'completed' AND id = :export_id"),
        {"user_id": user_id, "export_id": export_id}
    )
    row = result.first()
    if row is None:
        return None
    return str(row.filename)


def delete_export_task(db_conn, user_id: int, export_id: int) -> bool:
    """ Delete the specified export archive and its background task """
    result = db_conn.execute(
        text("DELETE FROM user_data_export WHERE user_id = :user_id AND id = :export_id RETURNING filename"),
        {"user_id": user_id, "export_id": export_id}
    )
    row = result.first()
    if row is not None:
        db_conn.execute(
            text("DELETE FROM background_tasks WHERE user_id = :user_id AND (metadata->'export_id')::int = :export_id"),
            {"user_id": user_id, "export_id": export_id}
        )
        return True
    return False
