from datetime import datetime, timezone
from typing import Optional, Union

from sqlalchemy import text

from data.model.external_service import ExternalServiceType
import sqlalchemy
import json


def update_latest_listened_at(db_conn, user_id: int, service: ExternalServiceType, timestamp: Union[int, float]):
    """ Update the timestamp of the last listen imported for the user with
    specified LB user ID.

    Args:
        db_conn: database connection
        user_id (int): the ListenBrainz row ID of the user
        service (data.model.ExternalServiceType): service to update latest listen timestamp for
        timestamp (int): the unix timestamp of the latest listen imported for the user
    """
    db_conn.execute(sqlalchemy.text("""
        INSERT INTO listens_importer (user_id, service, last_updated, latest_listened_at)
             VALUES (:user_id, :service, now(), :timestamp)
        ON CONFLICT (user_id, service)
          DO UPDATE 
                SET last_updated = now()
                  , latest_listened_at = :timestamp
        """), {
            'user_id': user_id,
            'service': service.value,
            'timestamp': datetime.fromtimestamp(timestamp, timezone.utc),
        })
    db_conn.commit()


def get_import_status(db_conn, user_id: int, service: ExternalServiceType) -> dict:
    """ Returns the timestamp of the last listen imported for the user with
    specified LB user ID from the given service.

    Args:
        db_conn: database connection
        user_id: the ListenBrainz row ID of the user
        service: service to update latest listen timestamp for
    Returns:
        a dict containing the latest listen unix timestamp and status information for
        the user, if any, otherwise None.
    """
    result = db_conn.execute(sqlalchemy.text("""
        SELECT latest_listened_at
             , status
             , error
          FROM listens_importer
         WHERE user_id = :user_id
           AND service = :service
        """), {
            "user_id": user_id,
            "service": service.value,
        })
    row = result.fetchone()
    if row is None:
        return {"status": None, "latest_listened_at": 0}

    return {
        "status": row.status,
        "latest_listened_at": int(row.latest_listened_at.timestamp()) if row.latest_listened_at is not None else 0,
        "error": row.error,
    }


def get_active_users_to_process(db_conn, service, exclude_error=False) -> list[dict]:
    """ Returns a list of users whose listens should be imported from the external service.
    """
    filters = ["external_service_oauth.service = :service"]
    # always exclude users with non-retryable errors
    if exclude_error:
        filters.append("error IS NULL")
    else:
        filters.append("(error IS NULL OR (error->>'retry')::boolean)")
    filter_str = " AND ".join(filters)

    result = db_conn.execute(text(f"""
        SELECT external_service_oauth.user_id
             , "user".musicbrainz_id
             , "user".musicbrainz_row_id
             , access_token
             , refresh_token
             , listens_importer.last_updated
             , token_expires
             , scopes
             , latest_listened_at
             , status
             , external_service_oauth.external_user_id
             , error
             , is_paused
          FROM external_service_oauth
          JOIN "user"
            ON "user".id = external_service_oauth.user_id
          JOIN listens_importer
            ON listens_importer.external_service_oauth_id = external_service_oauth.id
         WHERE {filter_str}
      ORDER BY latest_listened_at DESC NULLS LAST
    """), {"service": service.value})
    users = [row for row in result.mappings()]
    db_conn.rollback()
    return users


CLAIM_TIMEOUT_HOURS = 24

def claim_users_to_process(db_conn, service, batch_size=50, exclude_error=False) -> list[dict]:
    """ Claim a batch of users for import processing using SKIP LOCKED.

    Uses FOR UPDATE SKIP LOCKED so multiple workers safely distribute users.
    A claim expires after CLAIM_TIMEOUT_HOURS so crashed workers' users get
    auto-reclaimed.
    """
    filters = [
        "external_service_oauth.service = :service",
        "NOT is_paused",
        f"(listens_importer.claimed_at IS NULL OR listens_importer.claimed_at < now() - interval '{CLAIM_TIMEOUT_HOURS} hours')"
    ]
    if exclude_error:
        filters.append("error IS NULL")
    else:
        filters.append("(error IS NULL OR (error->>'retry')::boolean)")
    filter_str = " AND ".join(filters)

    # Phase 1: claim — lock rows briefly, mark claimed_at, commit
    result = db_conn.execute(text(f"""
        WITH claimable AS (
            SELECT listens_importer.id
              FROM external_service_oauth
              JOIN "user"
                ON "user".id = external_service_oauth.user_id
              JOIN listens_importer
                ON listens_importer.external_service_oauth_id = external_service_oauth.id
             WHERE {filter_str}
          ORDER BY listens_importer.latest_listened_at ASC NULLS FIRST
             LIMIT :batch_size
               FOR UPDATE OF listens_importer SKIP LOCKED
        )
        UPDATE listens_importer
           SET claimed_at = now()
         WHERE id IN (SELECT id FROM claimable)
     RETURNING id
    """), {
        "service": service.value,
        "batch_size": batch_size,
    })
    claimed_ids = [row.id for row in result]
    db_conn.commit()

    if not claimed_ids:
        return []

    # Phase 2: fetch full user data for claimed rows
    result = db_conn.execute(text("""
        SELECT external_service_oauth.user_id
             , "user".musicbrainz_id
             , "user".musicbrainz_row_id
             , access_token
             , refresh_token
             , listens_importer.last_updated
             , token_expires
             , scopes
             , latest_listened_at
             , status
             , external_service_oauth.external_user_id
             , error
          FROM external_service_oauth
          JOIN "user"
            ON "user".id = external_service_oauth.user_id
          JOIN listens_importer
            ON listens_importer.external_service_oauth_id = external_service_oauth.id
         WHERE listens_importer.id = ANY(:claimed_ids)
    """), {"claimed_ids": claimed_ids})
    users = [dict(row) for row in result.mappings()]
    db_conn.rollback()
    return users


def release_user_claim(db_conn, user_id: int, service):
    """ Release a claimed user after processing (success or failure). """
    db_conn.execute(text("""
        UPDATE listens_importer
           SET claimed_at = NULL
             , last_updated = now()
         WHERE user_id = :user_id
           AND service = :service
    """), {"user_id": user_id, "service": service.value})
    db_conn.commit()


def update_status(
    db_conn,
    user_id: int,
    service: ExternalServiceType,
    state: str,
    listens_count: int,
    error: dict = None
):
    """
        Update status information for a user's import.

    Args:
        db_conn: database connection
        user_id: ListenBrainz row ID of the user
        service: ExternalServiceType enum of the service
        state: Import status of that service
        listens_count: Number of listens imported
        error: optional error dict with 'message' (str) and 'retry' (bool) fields
    """

    params = {
        "status": json.dumps({
            "state": state,
            "count": listens_count
        }),
        "error": json.dumps(error) if error else None,
        "service": service.value,
        "user_id": user_id,
    }

    query = """
        UPDATE listens_importer
           SET status = :status
             , last_updated = now()
             , error = :error
         WHERE user_id = :user_id
           AND service = :service
    """

    db_conn.execute(text(query), params)
    db_conn.commit()


