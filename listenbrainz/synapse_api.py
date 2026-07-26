"""
Synapse HTTP API client for ListenBrainz notification settings.
"""

import requests
from flask import current_app

from listenbrainz.domain.musicbrainz import MusicBrainzService

TENANT = "listenbrainz"

# channels we've launched support for — filters what Synapse returns
ENABLED_CHANNELS = {"email"}


def _auth(user_id: int) -> dict:
    """Get Authorization header using the user's MB OAuth token, refreshing if expired."""

    svc = MusicBrainzService()
    user = svc.get_user(user_id)

    if not user:
        raise ValueError("User has not authenticated with MusicBrainz")

    if svc.user_oauth_token_has_expired(user):
        user = svc.refresh_access_token(user_id, user["refresh_token"])

    return {"Authorization": f"Bearer {user['access_token']}"}


def _is_enabled() -> bool:
    return bool(current_app.config.get("SYNAPSE_API_URL"))


def _url(path: str) -> str:
    return current_app.config["SYNAPSE_API_URL"].rstrip("/") + path


def get_notification_state(user_id: int, email: str | None) -> dict:
    """Aggregate the user's notification config into a single response for the settings page.

    If the user has an email but no email channel in Synapse, provision one automatically.
    """
    if not _is_enabled():
        return {"email": email, "event_types": [], "subscriptions": []}

    h = _auth(user_id)

    # user's channels (email, webhook, telegram)
    channels = requests.get(_url("/v1/me/channels"), headers=h, timeout=10).json()

    # event types the tenant exposes, with their allowed channels
    event_types = requests.get(_url(f"/v1/me/tenants/{TENANT}/event-types"), headers=h, timeout=10).json()

    # which channels are assigned to this tenant
    tenant_channels = requests.get(_url(f"/v1/me/tenants/{TENANT}/channels"), headers=h, timeout=10).json()

    # per-event-type subscription toggles
    subs = requests.get(_url(f"/v1/me/tenants/{TENANT}/subscriptions"), headers=h, timeout=10).json()

    # auto-provision email channel from the user's MB profile
    existing = _find_channel(channels, tenant_channels, "email")
    if email and not existing:
        _provision_email_channel(h, email)
    elif email and existing and existing["config"].get("to") != email:
        # email changed in MB profile — update the channel
        requests.delete(_url(f"/v1/me/tenants/{TENANT}/channels/email"), headers=h, timeout=10)
        requests.delete(_url(f"/v1/me/channels/{existing['id']}"), headers=h, timeout=10)
        _provision_email_channel(h, email)

    return {
        "email": email,
        "event_types": [
            {
                "name": et["name"],
                "allowed_channels": [ch for ch in (et.get("allowed_channels") or []) if ch in ENABLED_CHANNELS],
            }
            for et in event_types
        ],
        "subscriptions": [
            {"event_type": s["event_type"], "channel_type": s["channel_type"]}
            for s in subs if s.get("is_enabled") and s["channel_type"] in ENABLED_CHANNELS
        ],
    }


def toggle_subscription(user_id: int, event_type: str, channel_type: str, enabled: bool) -> None:
    """Subscribe or unsubscribe from a specific event type on a channel."""
    if not _is_enabled():
        return

    h = _auth(user_id)
    url = _url(f"/v1/me/tenants/{TENANT}/subscriptions/{event_type}/{channel_type}")

    if enabled:
        requests.put(url, headers=h, timeout=10).raise_for_status()
    else:
        requests.delete(url, headers=h, timeout=10).raise_for_status()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _find_channel(channels, tenant_channels, channel_type: str) -> dict | None:
    """Find the user's channel assigned to a tenant for a given channel type."""

    mapping = next((tc for tc in tenant_channels if tc["channel_type"] == channel_type), None)

    if not mapping:
        return None

    return next((c for c in channels if c["id"] == mapping["user_channel_id"]), None)


def _provision_email_channel(headers: dict, email: str) -> None:
    """Create an email channel in Synapse and assign it to the tenant."""

    ch = requests.post(_url("/v1/me/channels"), headers=headers, timeout=10,
                       json={"channel_type": "email", "label": email, "config": {"to": email}}).json()

    requests.put(_url(f"/v1/me/tenants/{TENANT}/channels/email"), headers=headers, timeout=10,
                 json={"channel_id": ch["id"]})
