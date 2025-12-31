import logging
from typing import Any

from listenbrainz.background.background_tasks import add_task
from listenbrainz.db import user as db_user
from listenbrainz.webserver import db_conn
from listenbrainz.webserver.timescale_connection import _ts as ts

logger = logging.getLogger(__name__)


def handle_user_created(payload: dict[str, Any], delivery_id: str) -> None:
    """
    Process user.created webhook event.

    This event is triggered when a new user account is created in the MetaBrainz system.

    Payload structure:
    {
        "user_id": <int>,
        "name": <str>,
    }

    Args:
        payload: The webhook payload containing user creation data
        delivery_id: Unique delivery identifier for idempotency
    """
    lb_user_id = db_user.create(
        db_conn, 
        musicbrainz_row_id=payload["user_id"],
        musicbrainz_id=payload["name"],
    )
    ts.set_empty_values_for_user(lb_user_id)


def handle_user_updated(payload: dict[str, Any], delivery_id: str) -> None:
    """
    Process user.updated webhook event.

    This event is triggered when a user's profile is updated in the MetaBrainz system.

    Payload structure:
    {
        "user_id": <int>,  # corresponds to musicbrainz_row_id
        "old": {"username": <str>, "email": <str>},  # fields that changed (optional keys)
        "new": {"username": <str>, "email": <str>}   # new values (optional keys)
    }

    Args:
        payload: The webhook payload containing user update data
        delivery_id: Unique delivery identifier for idempotency
    """
    user_id = payload["user_id"]
    new_data = payload.get("new", {})

    new_username = new_data.get("username")
    new_email = new_data.get("email")

    if not new_username and not new_email:
        logger.info(f"No username or email update in user.updated webhook for user_id={user_id}")
        return

    user = db_user.get_by_mb_row_id(db_conn, user_id, fetch_email=True)
    if not user:
        logger.warning(f"User with musicbrainz_row_id={user_id} not found for user.updated webhook")
        return

    db_user.update_user_details(
        db_conn,
        lb_id=user["id"],
        musicbrainz_id=new_username or user["musicbrainz_id"],
        email=new_email or user["email"]
    )


def handle_user_deleted(payload: dict[str, Any], delivery_id: str) -> None:
    """
    Process user.deleted webhook event.

    This event is triggered when a user is deleted in the MetaBrainz system.

    Payload structure:
    {
        "user_id": <int>  # corresponds to musicbrainz_row_id
    }

    Args:
        payload: The webhook payload containing user deletion data
        delivery_id: Unique delivery identifier for idempotency
    """
    user_id = payload["user_id"]
    user = db_user.get_by_mb_row_id(db_conn, user_id)
    if not user:
        logger.warning(f"User with musicbrainz_row_id={user_id} not found for user.deleted webhook")
        return

    add_task(user["id"], "delete_user")


EVENT_HANDLERS = {
    "user.created": handle_user_created,
    "user.updated": handle_user_updated,
    "user.deleted": handle_user_deleted,
}


def get_event_handler(event_type: str):
    """
    Get the handler function for a specific webhook event type.

    Args:
        event_type: The event type.

    Returns:
        Handler function or None if event type is not supported
    """
    return EVENT_HANDLERS.get(event_type)
