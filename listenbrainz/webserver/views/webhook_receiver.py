import hashlib
import hmac

import orjson
from flask import Blueprint, request, jsonify, current_app

from listenbrainz.db.webhook_handlers import get_event_handler

webhook_bp = Blueprint("webhook_receiver", __name__)


def verify_webhook_signature(secret: str, payload_bytes: bytes, signature_header: str) -> bool:
    """
    Verify the webhook signature using HMAC-SHA256.

    Args:
        secret: The webhook secret key
        payload_bytes: Raw request body as bytes
        signature_header: Value of X-MetaBrainz-Signature-256 header

    Returns:
        True if signature is valid, False otherwise
    """
    if not signature_header or not signature_header.startswith("sha256="):
        current_app.logger.warning("Invalid signature header format")
        return False

    try:
        expected_signature = hmac.new(
            key=secret.encode("utf-8"),
            msg=payload_bytes,
            digestmod=hashlib.sha256
        ).hexdigest()
        provided_signature = signature_header[7:]
        return hmac.compare_digest(expected_signature, provided_signature)
    except Exception:
        current_app.logger.error("Error during signature verification:", exc_info=True)
        return False


@webhook_bp.route("/metabrainz", methods=["POST"])
def receive_metabrainz_webhook():
    """
    Receive and process MetaBrainz webhook events.

    This endpoint verifies the HMAC-SHA256 signature and routes
    events to appropriate handlers.

    Expected headers:
        - X-MetaBrainz-Event: Event type (e.g., "user.created")
        - X-MetaBrainz-Delivery: Unique delivery ID (UUID)
        - X-MetaBrainz-Attempt: Attempt number (1-6)
        - X-MetaBrainz-Signature-256: HMAC signature (sha256=<hex>)
        - User-Agent: MetaBrainz-Webhooks/1.0
    """
    event_type = request.headers.get("X-MetaBrainz-Event")
    delivery_id = request.headers.get("X-MetaBrainz-Delivery")
    attempt = request.headers.get("X-MetaBrainz-Attempt")
    signature = request.headers.get("X-MetaBrainz-Signature-256")
    user_agent = request.headers.get("User-Agent")

    current_app.logger.info(
        f"Webhook received: event={event_type}, delivery={delivery_id}, "
        f"attempt={attempt}, user_agent={user_agent}"
    )

    if not all([event_type, delivery_id, signature]):
        current_app.logger.warning(f"Missing required headers in webhook delivery {delivery_id}")
        return jsonify({
            "error": "Missing required headers",
            "required": ["X-MetaBrainz-Event", "X-MetaBrainz-Delivery", "X-MetaBrainz-Signature-256"]
        }), 400

    webhook_secret = current_app.config.get("METABRAINZ_WEBHOOK_SECRET")
    if not webhook_secret:
        current_app.logger.error("METABRAINZ_WEBHOOK_SECRET not configured")
        return jsonify({"error": "Webhook receiver not properly configured"}), 503

    payload_bytes = request.get_data()

    if not verify_webhook_signature(webhook_secret, payload_bytes, signature):
        current_app.logger.warning(f"Invalid signature for delivery {delivery_id}.")
        return jsonify({"error": "Invalid signature"}), 401

    try:
        payload = orjson.loads(payload_bytes)
    except orjson.JSONDecodeError as e:
        current_app.logger.error(f"Invalid JSON in delivery {delivery_id}: {str(e)}")
        return jsonify({"error": "Invalid JSON payload"}), 400

    handler = get_event_handler(event_type)
    if not handler:
        current_app.logger.warning(f"Unknown event type: {event_type}")
        return jsonify({"error": f"Unknown event type: {event_type}"}), 400

    try:
        handler(payload, delivery_id)
        current_app.logger.info(f"Webhook processed successfully: event={event_type}, delivery={delivery_id}")
        return jsonify({"status": "success"}), 200
    except Exception:
        current_app.logger.error(
            f"Error processing webhook: event={event_type}, delivery={delivery_id}:",
            exc_info=True
        )
        return jsonify({
            "error": "Processing failed",
            "message": "An error occurred while processing the webhook."
        }), 500
