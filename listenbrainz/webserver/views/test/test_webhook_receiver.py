import hmac
import hashlib
import json
import uuid
from unittest import mock

from listenbrainz.background.background_tasks import get_task
from listenbrainz.db import user as db_user

from listenbrainz.tests.integration import IntegrationTestCase


class WebhookReceiverTestCase(IntegrationTestCase):
    """Test cases for MetaBrainz webhook receiver."""

    def setUp(self):
        super().setUp()
        self.app.config["METABRAINZ_WEBHOOK_SECRET"] = "mebw_test_secret_1234567890"

    def _generate_signature(self, payload_bytes: bytes, secret: str) -> str:
        """Helper to generate HMAC-SHA256 signature."""
        signature = hmac.new(
            key=secret.encode("utf-8"),
            msg=payload_bytes,
            digestmod=hashlib.sha256
        ).hexdigest()
        return f"sha256={signature}"

    def _send_webhook(self, event_type: str, payload: dict, secret: str = None, delivery_id: str = None):
        """Helper to send a webhook request."""
        if secret is None:
            secret = self.app.config["METABRAINZ_WEBHOOK_SECRET"]

        if delivery_id is None:
            delivery_id = str(uuid.uuid4())

        payload_json = json.dumps(payload, separators=(",", ":"))
        payload_bytes = payload_json.encode("utf-8")
        signature = self._generate_signature(payload_bytes, secret)

        headers = {
            "Content-Type": "application/json; charset=utf-8",
            "User-Agent": "MetaBrainz-Webhooks/1.0",
            "X-MetaBrainz-Event": event_type,
            "X-MetaBrainz-Delivery": delivery_id,
            "X-MetaBrainz-Attempt": "1",
            "X-MetaBrainz-Signature-256": signature
        }

        response = self.client.post(
            "/webhooks/metabrainz/",
            data=payload_bytes,
            headers=headers
        )

        return response, delivery_id

    def test_user_created_webhook_success(self):
        """Test successful user.created webhook."""
        payload = {
            "user_id": 123,
            "name": "newuser",
        }

        response, delivery_id = self._send_webhook("user.created", payload)
        self.assert200(response)
        self.assertEqual(response.json["status"], "success")

        user = db_user.get_by_mb_row_id(self.db_conn, 123)
        self.assertEqual(user["musicbrainz_id"], "newuser")

    def test_invalid_signature(self):
        """Test webhook with invalid signature is rejected."""
        payload = {
            "user_id": 123,
            "name": "newuser",
        }

        response, delivery_id = self._send_webhook("user.created", payload, secret="wrong_secret_here")
        self.assert401(response)
        self.assertIn("Invalid signature", response.json["error"])

    def test_missing_headers(self):
        """Test webhook with missing required headers."""
        payload = {"user_id": 123}
        payload_bytes = json.dumps(payload).encode("utf-8")

        # Missing X-MetaBrainz-Event header
        headers = {
            "Content-Type": "application/json",
            "X-MetaBrainz-Delivery": str(uuid.uuid4()),
            "X-MetaBrainz-Signature-256": "sha256=invalid"
        }

        response = self.client.post(
            "/webhooks/metabrainz/",
            data=payload_bytes,
            headers=headers
        )
        self.assert400(response)
        self.assertIn("Missing required headers", response.json["error"])

    def test_invalid_json(self):
        """Test webhook with invalid JSON payload."""
        delivery_id = str(uuid.uuid4())
        payload_bytes = b"invalid json {{"
        secret = self.app.config["METABRAINZ_WEBHOOK_SECRET"]
        signature = self._generate_signature(payload_bytes, secret)

        headers = {
            "Content-Type": "application/json",
            "X-MetaBrainz-Event": "user.created",
            "X-MetaBrainz-Delivery": delivery_id,
            "X-MetaBrainz-Attempt": "1",
            "X-MetaBrainz-Signature-256": signature
        }

        response = self.client.post(
            "/webhooks/metabrainz/",
            data=payload_bytes,
            headers=headers
        )
        self.assert400(response)
        self.assertIn("Invalid JSON", response.json["error"])

    def test_unknown_event_type(self):
        """Test webhook with unknown event type."""
        payload = {"data": "test"}
        response, delivery_id = self._send_webhook("unknown.event", payload)
        self.assert400(response)
        self.assertIn("Unknown event type", response.json["error"])

    def test_webhook_without_secret_configured(self):
        """Test webhook when secret is not configured."""
        self.app.config["METABRAINZ_WEBHOOK_SECRET"] = None

        payload = {"user_id": 789}
        response, _ = self._send_webhook("user.created", payload, secret="mebw_ssss")

        self.assertEqual(response.status_code, 503)
        self.assertIn("not properly configured", response.json["error"])

    @mock.patch("listenbrainz.webserver.views.webhook_receiver.get_event_handler")
    def test_webhook_handler_exception(self, mock_get_handler):
        """Test webhook when handler raises an exception."""
        def failing_handler(payload, delivery_id):
            raise Exception("Handler error")

        mock_get_handler.return_value = failing_handler

        payload = {
            "user_id": 999,
            "name": "erroruser",
        }

        response, delivery_id = self._send_webhook("user.created", payload)
        self.assertEqual(response.status_code, 500)
        self.assertIn("Processing failed", response.json["error"])

    def test_signature_with_different_payload(self):
        """Test that signature verification fails when payload is tampered."""
        payload = {
            "user_id": 123,
            "name": "originaluser",
            "email": "original@example.com",
            "is_email_confirmed": False,
            "created_at": "2025-11-01T10:30:00.000000+00:00"
        }

        delivery_id = str(uuid.uuid4())
        secret = self.app.config["METABRAINZ_WEBHOOK_SECRET"]

        # Generate signature for original payload
        original_payload_bytes = json.dumps(payload, separators=(",", ":")).encode("utf-8")
        signature = self._generate_signature(original_payload_bytes, secret)

        # Tamper with payload
        tampered_payload = payload.copy()
        tampered_payload["user_id"] = 999
        tampered_payload_bytes = json.dumps(tampered_payload, separators=(",", ":")).encode("utf-8")

        headers = {
            "Content-Type": "application/json; charset=utf-8",
            "User-Agent": "MetaBrainz-Webhooks/1.0",
            "X-MetaBrainz-Event": "user.created",
            "X-MetaBrainz-Delivery": delivery_id,
            "X-MetaBrainz-Attempt": "1",
            "X-MetaBrainz-Signature-256": signature
        }

        response = self.client.post(
            "/webhooks/metabrainz/",
            data=tampered_payload_bytes,
            headers=headers
        )

        self.assert401(response)
        self.assertIn("Invalid signature", response.json["error"])

    def test_user_updated(self):
        payload = {
            "user_id": 456,
            "name": "oldusername",
        }
        response, _ = self._send_webhook("user.created", payload)
        self.assert200(response)

        update_payload = {
            "user_id": 456,
            "old": {"username": "oldusername"},
            "new": {"username": "newusername"}
        }
        response, _ = self._send_webhook("user.updated", update_payload)
        self.assert200(response)

        user = db_user.get_by_mb_row_id(self.db_conn, 456, fetch_email=True)
        self.assertEqual(user["musicbrainz_id"], "newusername")

        update_payload = {
            "user_id": 456,
            "old": {},
            "new": {"email": "new@example.com"}
        }
        response, _ = self._send_webhook("user.updated", update_payload)
        self.assert200(response)

        user = db_user.get_by_mb_row_id(self.db_conn, 456, fetch_email=True)
        self.assertEqual(user["musicbrainz_id"], "newusername")
        self.assertEqual(user["email"], "new@example.com")

        update_payload = {
            "user_id": 456,
            "old": {"username": "newusername", "email": "new@example.com"},
            "new": {"username": "user-456", "email": "user-456@example.com"}
        }
        response, _ = self._send_webhook("user.updated", update_payload)
        self.assert200(response)

        user = db_user.get_by_mb_row_id(self.db_conn, 456, fetch_email=True)
        self.assertEqual(user["musicbrainz_id"], "user-456")
        self.assertEqual(user["email"], "user-456@example.com")

        update_payload = {
            "user_id": 99999,
            "old": {"username": "nonexistent"},
            "new": {"username": "newname"}
        }
        response, _ = self._send_webhook("user.updated", update_payload)
        self.assert200(response)

        user = db_user.get_by_mb_row_id(self.db_conn, 99999, fetch_email=True)
        self.assertIsNone(user)

    def test_user_deleted(self):
        delete_payload = {"user_id": 99999}
        response, _ = self._send_webhook("user.deleted", delete_payload)
        self.assert200(response)

        with self.app.app_context():
            task = get_task()
        self.assertIsNone(task)

        payload = {
            "user_id": 789,
            "name": "deleteuser",
            "email": "delete@example.com",
            "is_email_confirmed": False,
            "created_at": "2025-11-01T10:30:00.000000+00:00"
        }
        response, _ = self._send_webhook("user.created", payload)
        self.assert200(response)

        user = db_user.get_by_mb_row_id(self.db_conn, 789, fetch_email=True)
        user_id = user["id"]

        delete_payload = {"user_id": 789}
        response, _ = self._send_webhook("user.deleted", delete_payload)
        self.assert200(response)

        with self.app.app_context():
            task = get_task()
        self.assertIsNotNone(task)
        self.assertEqual(task.user_id, user_id)
        self.assertEqual(task.task, "delete_user")
