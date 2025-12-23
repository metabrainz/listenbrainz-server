import logging
from typing import Any

from listenbrainz.db import user as db_user
from listenbrainz.webserver import db_conn

logger = logging.getLogger(__name__)


def handle_user_created(payload: dict[str, Any], delivery_id: str) -> None:
    """
    Process user.created webhook event.

    This event is triggered when a new user account is created in the MetaBrainz system.

    Payload structure:
    {
        "user_id": <int>,
        "name": <str>,
        "email": <str>,
        "is_email_confirmed": <bool>,
        "created_at": <str (ISO 8601)>
    }

    Args:
        payload: The webhook payload containing user creation data
        delivery_id: Unique delivery identifier for idempotency
    """
    # todo: email is not verified yet
    db_user.create(
        db_conn, 
        musicbrainz_row_id=payload["user_id"],
        musicbrainz_id=payload["name"],
        email=payload["email"]
    )


def handle_user_verified(payload: dict[str, Any], delivery_id: str) -> None:
    """
    Process user.verified webhook event.

    This event is triggered when a user verifies their email address.

    Payload structure:
    {
        "user_id": <int>,
        "email": <str>,
        "verified_at": <str (ISO 8601)>
    }

    Args:
        payload: The webhook payload containing user verification data
        delivery_id: Unique delivery identifier for idempotency
    """
    # todo: implement support verified and unverified emails in LB


def handle_user_updated(payload: dict[str, Any], delivery_id: str) -> None:
    """
    Process user.updated webhook event.

    Args:
        payload: The webhook payload containing user update data
        delivery_id: Unique delivery identifier for idempotency
    """
    # TODO: Implement when this event type becomes available


def handle_user_deleted(payload: dict[str, Any], delivery_id: str) -> None:
    """
    Process user.deleted webhook event.

    Args:
        payload: The webhook payload containing user deletion data
        delivery_id: Unique delivery identifier for idempotency
    """
    # TODO: Implement when this event type becomes available


EVENT_HANDLERS = {
    "user.created": handle_user_created,
    "user.verified": handle_user_verified,
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
