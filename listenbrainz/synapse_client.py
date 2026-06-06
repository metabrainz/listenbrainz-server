"""
Synapse event publisher for ListenBrainz.
"""

import logging

import orjson
from kombu import Connection, Exchange, Queue, pools

logger = logging.getLogger(__name__)

MAX_RECIPIENTS_PER_EVENT = 5000

_enabled: bool = False
_queue: Queue | None = None
_TENANT_ID: str = "listenbrainz"
_lb_base_url: str = "https://listenbrainz.org"
_producer_pool = None
SYNAPSE_QUEUE = "events.ingest"


def init_synapse_client(app) -> None:
    """Call once from the Flask app factory when SYNAPSE_ENABLED is True."""
    global _enabled, _queue, _lb_base_url, _producer_pool

    if not app.config.get("SYNAPSE_ENABLED", False):
        return

    rabbitmq_url = app.config.get("SYNAPSE_RABBITMQ_URL")
    if not rabbitmq_url:
        app.logger.error("SYNAPSE_ENABLED is True but SYNAPSE_RABBITMQ_URL is not set — Synapse disabled")
        return

    _lb_base_url = app.config.get("SYNAPSE_LB_BASE_URL", "https://listenbrainz.org").rstrip("/")
    _queue = Queue(SYNAPSE_QUEUE, Exchange("", "direct"), routing_key=SYNAPSE_QUEUE, durable=True)
    _producer_pool = pools.producers[Connection(rabbitmq_url)]
    _enabled = True
    app.logger.info("Synapse client enabled — broker %s, queue %s", rabbitmq_url, SYNAPSE_QUEUE)


# ---------------------------------------------------------------------------
# Public publish functions — one per event type.
#
# recipients: list of str(musicbrainz_row_id). For social events the caller
#   resolves followers; for direct events it is a single-element list.
# actor:      user['musicbrainz_id'] — the username used for display.
# ---------------------------------------------------------------------------

def publish_recording_recommendation(recipients: list[str], actor: str, track_metadata: dict) -> None:
    recording = _build_recording(track_metadata)
    if not recording:
        return
    _publish(recipients, "recording_recommendation", {
        "actor": _build_actor(actor),
        "recording": recording,
        "summary": f"{actor} recommended {recording['track_name']} by {recording['artist_name']}",
    })


def publish_personal_recommendation(recipients: list[str], actor: str, track_metadata: dict, blurb: str | None) -> None:
    recording = _build_recording(track_metadata)
    if not recording:
        return
    payload = {
        "actor": _build_actor(actor),
        "recording": recording,
        "summary": f"{actor} recommended {recording['track_name']} by {recording['artist_name']} to you",
    }
    if blurb:
        payload["message"] = blurb
    _publish(recipients, "personal_recording_recommendation", payload)


def publish_notification(recipients: list[str], creator: str, message: str) -> None:
    _publish(recipients, "notification", {
        "actor": _build_actor(creator),
        "message": message,
        "summary": message,
    })


def publish_cb_review(recipients: list[str], actor: str, review_id: str, entity_name: str) -> None:
    _publish(recipients, "cb_review", {
        "actor": _build_actor(actor),
        "entity": {
            "id": review_id,
            "name": entity_name,
            "type": "review",
            "url": f"https://critiquebrainz.org/review/{review_id}",
        },
        "summary": f"{actor} reviewed {entity_name}",
    })


def publish_thanks(recipients: list[str], actor: str, track_metadata: dict, blurb: str | None) -> None:
    recording = _build_recording(track_metadata)
    if not recording:
        return
    payload = {
        "actor": _build_actor(actor),
        "recording": recording,
        "summary": f"{actor} thanked you for recommending {recording['track_name']} by {recording['artist_name']}",
    }
    if blurb:
        payload["message"] = blurb
    _publish(recipients, "thanks", payload)


def publish_follow(recipients: list[str], follower: str) -> None:
    _publish(recipients, "follow", {
        "actor": _build_actor(follower),
        "summary": f"{follower} started following you",
    })


def publish_recording_pin(recipients: list[str], actor: str, track_metadata: dict, blurb: str | None) -> None:
    recording = _build_recording(track_metadata)
    if not recording:
        return
    payload = {
        "actor": _build_actor(actor),
        "recording": recording,
        "summary": f"{actor} pinned {recording['track_name']} by {recording['artist_name']}",
    }
    if blurb:
        payload["message"] = blurb
    _publish(recipients, "recording_pin", payload)


# ---------------------------------------------------------------------------
# Internals
# ---------------------------------------------------------------------------

def _publish(recipients: list[str], event_type: str, payload: dict) -> None:
    if not _enabled or not recipients:
        return

    recipients = list(dict.fromkeys(str(r) for r in recipients if r))
    if not recipients:
        return

    try:
        with _producer_pool.acquire(block=True, timeout=5) as producer:
            for i in range(0, len(recipients), MAX_RECIPIENTS_PER_EVENT):
                chunk = recipients[i:i + MAX_RECIPIENTS_PER_EVENT]
                producer.publish(
                    exchange="",
                    routing_key=_queue.name,
                    body=orjson.dumps({
                        "tenant_id": _TENANT_ID,
                        "event_type": event_type,
                        "recipients": chunk,
                        "payload": payload,
                    }),
                    delivery_mode=2,
                    retry=True,
                    retry_policy={"max_retries": 3},
                    declare=[_queue],
                )
    except Exception:
        logger.error("Failed to publish %s event to Synapse (%d recipients)",
                     event_type, len(recipients), exc_info=True)


def _build_actor(username: str) -> dict:
    return {
        "username": username,
        "url": f"{_lb_base_url}/user/{username}",
    }


def _build_recording(track_metadata: dict) -> dict | None:
    """Convert LB's track_metadata dict to the Synapse recording namespace.

    Returns None if metadata is missing or malformed — caller skips publishing
    rather than sending an incomplete payload that Synapse would reject.
    """
    if not track_metadata:
        return None

    track_name = track_metadata.get("track_name")
    artist_name = track_metadata.get("artist_name")
    if not track_name or not artist_name:
        return None

    recording: dict = {"track_name": track_name, "artist_name": artist_name}

    release_name = track_metadata.get("release_name")
    if release_name:
        recording["release_name"] = release_name

    mbid_mapping = track_metadata.get("mbid_mapping") or {}
    mbid = mbid_mapping.get("recording_mbid")
    if mbid:
        recording["mbid"] = mbid
        recording["url"] = f"{_lb_base_url}/music/recording/{mbid}"

    return recording
