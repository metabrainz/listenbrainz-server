import time
import uuid
from unittest import mock

import orjson
from kombu.entity import PERSISTENT_DELIVERY_MODE

from listenbrainz.clickhouse import handlers
from listenbrainz.clickhouse.clickhouse_reader import ClickHouseReader
from listenbrainz.rabbitmq import create_rabbitmq_connection
from listenbrainz.webserver import create_app
from listenbrainz.webserver.testing import ServerTestCase


class ClickHouseReaderTestCase(ServerTestCase):
    """ TestCase for the ClickHouse result reader, using the app the reader runs with in production.

    Each test gets its own result exchange and queue on the test RabbitMQ, and a reader
    connected to them and to the ClickHouse reader CouchDB instance.
    """

    @classmethod
    def create_app(cls):
        app = create_app()
        app.config["TESTING"] = True
        return app

    def setUp(self):
        super().setUp()
        suffix = uuid.uuid4().hex
        self.app.config["CLICKHOUSE_RESULT_EXCHANGE"] = f"test_clickhouse_result_{suffix}"
        self.app.config["CLICKHOUSE_RESULT_QUEUE"] = f"test_clickhouse_result_{suffix}"

        self.reader = ClickHouseReader(self.app)
        capture_exception = mock.patch("listenbrainz.clickhouse.clickhouse_reader.sentry_sdk.capture_exception")
        self.capture_exception = capture_exception.start()
        self.addCleanup(capture_exception.stop)

        self.connection = create_rabbitmq_connection(self.app.config, "clickhouse-reader-test")
        self.addCleanup(self.connection.release)
        self.result_queue = self.reader.clickhouse_result_queue(self.connection.default_channel)
        self.result_queue.declare()
        self.addCleanup(self.delete_result_queue)

    def delete_result_queue(self):
        self.result_queue.delete()
        self.reader.clickhouse_result_exchange(self.connection.default_channel).delete()

    def publish_result(self, message: dict):
        """Publish a result message to the reader's result exchange, like the request consumer does."""
        self.connection.Producer().publish(
            exchange=self.reader.clickhouse_result_exchange,
            routing_key="",
            body=orjson.dumps(message),
            delivery_mode=PERSISTENT_DELIVERY_MODE,
        )

    def get_result_message(self, timeout=2):
        """Fetch the next message from the result queue, unacked.

        Waits up to timeout seconds for one, as a requeue isn't confirmed by the broker.
        """
        deadline = time.monotonic() + timeout
        while (message := self.result_queue.get(no_ack=False)) is None and time.monotonic() < deadline:
            time.sleep(0.05)
        return message

    def queued_result_count(self) -> int:
        """Number of messages ready in the result queue."""
        return self.result_queue.queue_declare(passive=True).message_count

    def register_handler(self, message_type, handler):
        """Handle messages of the given type with handler for the rest of the test."""
        handlers.RESPONSE_HANDLERS[message_type] = handler
        self.addCleanup(handlers.RESPONSE_HANDLERS.pop, message_type, None)

    def reported_exceptions(self) -> list[str]:
        """Names of the types of the exceptions reported to Sentry so far."""
        return [type(call.args[0]).__name__ for call in self.capture_exception.call_args_list]
