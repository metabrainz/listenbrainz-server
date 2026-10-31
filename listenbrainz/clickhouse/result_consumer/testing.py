import uuid

import orjson
from kombu.entity import PERSISTENT_DELIVERY_MODE

from listenbrainz.clickhouse import queues
from listenbrainz.clickhouse.result_consumer import handlers
from listenbrainz.clickhouse.result_consumer.consumer import ClickHouseResultConsumer
from listenbrainz.rabbitmq import create_rabbitmq_connection
from listenbrainz.webserver import create_app
from listenbrainz.webserver.testing import ServerTestCase


class ClickHouseResultConsumerTestCase(ServerTestCase):
    """Test the reader with its application context.

    Each test uses a separate RabbitMQ exchange and queue.
    """

    @classmethod
    def create_app(cls):
        app = create_app()
        app.config["TESTING"] = True
        return app

    def setUp(self):
        super().setUp()
        self.ctx = self.app.app_context()
        self.ctx.push()
        suffix = uuid.uuid4().hex
        self.app.config["CLICKHOUSE_RESULT_EXCHANGE"] = f"test_clickhouse_result_{suffix}"
        self.app.config["CLICKHOUSE_RESULT_QUEUE"] = f"test_clickhouse_result_{suffix}"
        queues.init_queues(self.app.config)

        self.reader = ClickHouseResultConsumer()

        self.connection = create_rabbitmq_connection(self.app.config, "clickhouse-result-consumer-test")
        self.addCleanup(self.connection.release)
        self.result_queue = queues.CLICKHOUSE_RESULT_QUEUE(self.connection.default_channel)
        self.result_queue.declare()
        self.addCleanup(self.delete_result_queue)

    def tearDown(self):
        self.ctx.pop()
        super().tearDown()

    def delete_result_queue(self):
        self.result_queue.delete()
        queues.CLICKHOUSE_RESULT_EXCHANGE(self.connection.default_channel).delete()

    def publish_result(self, message: dict):
        """Publish a result to the reader's exchange."""
        self.connection.Producer().publish(
            exchange=queues.CLICKHOUSE_RESULT_EXCHANGE,
            routing_key="",
            body=orjson.dumps(message),
            delivery_mode=PERSISTENT_DELIVERY_MODE,
        )

    def queued_result_count(self) -> int:
        """Number of messages ready in the result queue."""
        return self.result_queue.queue_declare(passive=True).message_count

    def register_handler(self, message_type, handler):
        """Register a handler for this test."""
        handlers.RESPONSE_HANDLERS[message_type] = handler
        self.addCleanup(handlers.RESPONSE_HANDLERS.pop, message_type, None)
