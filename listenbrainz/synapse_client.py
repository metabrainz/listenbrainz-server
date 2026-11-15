"""Publishes ListenBrainz social events to Synapse over RabbitMQ.

Publishing is best effort: it runs after the user's action is committed, so a failure is
logged and never reaches the caller.
"""

import functools
import logging
import time

import orjson
from flask import current_app
from kombu import pools

import listenbrainz.db.user as db_user
import listenbrainz.db.user_relationship as db_user_relationship
from data.model.synapse_event import (
    Actor, CritiqueBrainzReviewEvent, FollowEvent, NotificationEvent, Recording,
)
from listenbrainz.db.msid_mbid_mapping import fetch_track_metadata_for_items
from listenbrainz.rabbitmq import create_rabbitmq_connection
from listenbrainz.webserver import db_conn, listens_conn

logger = logging.getLogger(__name__)

TENANT_ID = "listenbrainz"
EXCHANGE = "events.ingest"
ROUTING_KEY = "event"
MAX_RECIPIENTS_PER_EVENT = 5000  # Synapse rejects larger events
PUBLISH_TIMEOUT_SECONDS = 2
SLOW_PUBLISH_SECONDS = 1.0

_producer_pool = None


def init_synapse_client(app) -> None:
    """Set up the producer pool. Publishing stays off without RABBITMQ_HOSTS or SYNAPSE_RABBITMQ_VHOST."""
    global _producer_pool
    vhost = app.config.get("SYNAPSE_RABBITMQ_VHOST")
    if not vhost or not app.config.get("RABBITMQ_HOSTS"):
        return
    # kombu connects on the first publish, so a RabbitMQ outage doesn't block startup.
    connection = create_rabbitmq_connection(
        {**app.config, "RABBITMQ_VHOST": vhost},
        connection_name="synapse-publisher",
        # The publish timeouts don't cover the socket, e.g. closing the channel after a timed-out confirm.
        connect_timeout=PUBLISH_TIMEOUT_SECONDS,
        transport_options={"confirm_publish": True, "read_timeout": PUBLISH_TIMEOUT_SECONDS,
                           "write_timeout": PUBLISH_TIMEOUT_SECONDS},
    )
    _producer_pool = pools.producers[connection]


def _best_effort(func):
    """Skip the publish, and the lookups that prepare it, when publishing is off; log any failure."""
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        if _producer_pool is None:
            return
        try:
            func(*args, **kwargs)
        except Exception:
            logger.error("Failed to publish %s to Synapse", func.__name__, exc_info=True)
    return wrapper


@_best_effort
def publish_follow(follower: dict, followee: dict) -> None:
    payload: FollowEvent = {"actor": _actor(follower["musicbrainz_id"])}
    # Keyed on the pair, so unfollowing and following again doesn't notify again.
    _publish("follow", [followee["musicbrainz_row_id"]], payload, f"follow:{follower['id']}:{followee['id']}")


@_best_effort
def publish_notification(creator: dict, recipient: dict, message: str, event_id: int) -> None:
    payload: NotificationEvent = {"actor": _actor(creator["musicbrainz_id"]), "message": message}
    _publish("notification", [recipient["musicbrainz_row_id"]], payload, f"notification:{event_id}")


@_best_effort
def publish_cb_review(user: dict, review_id: str, entity_name: str) -> None:
    payload: CritiqueBrainzReviewEvent = {
        "actor": _actor(user["musicbrainz_id"]),
        "entity": {
            "id": review_id,
            "name": entity_name,
            "type": "review",
            "url": f"https://critiquebrainz.org/review/{review_id}",
        },
    }
    _publish("cb_review", _followers(user), payload, f"cb_review:{review_id}")


@_best_effort
def publish_recording_pin(user: dict, pin) -> None:
    _publish_recording("recording_pin", _followers(user), user, pin, pin.blurb_content, f"recording_pin:{pin.row_id}")


@_best_effort
def publish_recording_recommendation(user: dict, event) -> None:
    _publish_recording("recording_recommendation", _followers(user), user, event.metadata, None,
                       f"recording_recommendation:{event.id}")


@_best_effort
def publish_personal_recommendation(user: dict, event, usernames: list[str]) -> None:
    """usernames are the recipients; the stored event.metadata.users holds their user ids instead."""
    recipients = db_user.get_many_users_by_mb_id(db_conn, usernames).values()
    _publish_recording("personal_recording_recommendation", [r["musicbrainz_row_id"] for r in recipients],
                       user, event.metadata, event.metadata.blurb_content, f"personal_recording_recommendation:{event.id}")


@_best_effort
def publish_thanks(thanker: dict, thankee_id: int, item, metadata) -> None:
    """item is the pin or the recommendation's metadata that was thanked."""
    thankee = db_user.get(db_conn, thankee_id)
    # Keyed on what was thanked, so thanking the same event again doesn't notify again.
    key = f"thanks:{thanker['id']}:{metadata.original_event_type.value}:{metadata.original_event_id}"
    _publish_recording("thanks", [thankee["musicbrainz_row_id"]], thanker, item, metadata.blurb_content, key)


def _followers(user: dict) -> list:
    return [f["musicbrainz_row_id"] for f in db_user_relationship.get_followers_of_user(db_conn, user["id"])]


def _publish_recording(event_type: str, recipients: list, actor: dict, item, blurb: str | None, key: str) -> None:
    if not recipients:
        return
    # Fetch into a copy: the caller's item is also the API response, which must not change.
    item = fetch_track_metadata_for_items(listens_conn, [item.copy()])[0]
    recording = _recording(item.track_metadata)
    if recording is None:
        logger.info("Not publishing %s to Synapse: no track or artist name for %s", key, item.recording_mbid or item.recording_msid)
        return
    payload = {"actor": _actor(actor["musicbrainz_id"]), "recording": recording}
    if blurb:
        payload["message"] = blurb
    _publish(event_type, recipients, payload, key)


def _root_url() -> str:
    return current_app.config["SERVER_ROOT_URL"].rstrip("/")


def _actor(username: str) -> Actor:
    return {"username": username, "url": f"{_root_url()}/user/{username}"}


def _recording(track_metadata: dict | None) -> Recording | None:
    """Synapse requires a track and an artist name; None when either is missing."""
    track_metadata = track_metadata or {}
    if not track_metadata.get("track_name") or not track_metadata.get("artist_name"):
        return None

    recording: Recording = {"track_name": track_metadata["track_name"], "artist_name": track_metadata["artist_name"]}
    if track_metadata.get("release_name"):
        recording["release_name"] = track_metadata["release_name"]

    mapping = track_metadata.get("mbid_mapping") or {}
    if mapping.get("recording_mbid"):
        recording["mbid"] = mapping["recording_mbid"]
        recording["url"] = f"{_root_url()}/music/recording/{mapping['recording_mbid']}"
    if mapping.get("caa_id") and mapping.get("caa_release_mbid"):
        mbid = mapping["caa_release_mbid"]
        recording["album_art_url"] = f"https://archive.org/download/mbid-{mbid}/mbid-{mbid}-{mapping['caa_id']}_thumb250.jpg"
    return recording


def _publish(event_type: str, recipients: list, payload: dict, key: str) -> None:
    recipients = list(dict.fromkeys(str(r) for r in recipients if r))
    if not recipients:
        return

    start = time.monotonic()
    with _producer_pool.acquire(block=True, timeout=PUBLISH_TIMEOUT_SECONDS) as producer:
        for n, i in enumerate(range(0, len(recipients), MAX_RECIPIENTS_PER_EVENT)):
            producer.publish(
                orjson.dumps({
                    "tenant_id": TENANT_ID,
                    "event_type": event_type,
                    "recipients": recipients[i:i + MAX_RECIPIENTS_PER_EVENT],
                    "payload": payload,
                    # Each chunk is its own event, so each needs its own key.
                    "idempotency_key": key if n == 0 else f"{key}:{n}",
                }),
                exchange=EXCHANGE,
                routing_key=ROUTING_KEY,
                content_type="application/json",
                delivery_mode=2,
                # A blocked broker must not hold the request.
                timeout=PUBLISH_TIMEOUT_SECONDS,
                confirm_timeout=PUBLISH_TIMEOUT_SECONDS,
            )

    duration = time.monotonic() - start
    if duration > SLOW_PUBLISH_SECONDS:
        logger.warning("Slow Synapse publish of %s: %.2fs", event_type, duration)
