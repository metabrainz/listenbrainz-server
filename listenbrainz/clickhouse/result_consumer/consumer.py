"""Consumes ClickHouse result messages and dispatches them to their handlers."""
import time

import orjson
import sentry_sdk
from flask import current_app
from kombu import Consumer
from kombu.mixins import ConsumerMixin

from listenbrainz.clickhouse import queues
from listenbrainz.clickhouse.result_consumer.handlers import get_handler
from listenbrainz.rabbitmq import create_rabbitmq_connection
from listenbrainz.webserver import create_app

PREFETCH_COUNT = 100


class ClickHouseResultConsumer(ConsumerMixin):
    """Consumer for ClickHouse result messages.

    Process messages in order because stats handlers depend on earlier results.
    """

    def __init__(self):
        self.connection = None

    def callback(self, message):
        """Handle incoming message from ClickHouse result queue."""
        try:
            response = orjson.loads(message.body)
            response_type = response.get("type")
        except Exception:
            current_app.logger.error("Error parsing message: %s", message.body, exc_info=True)
            message.ack()
            return

        if not response_type or not isinstance(response_type, str):
            current_app.logger.error("Missing or invalid type in message: %s", orjson.dumps(response, option=orjson.OPT_INDENT_2).decode())
            message.ack()
            return
        current_app.logger.info("Received ClickHouse message: %s", response_type)

        handler = get_handler(response_type)
        if not handler:
            current_app.logger.warning("Unknown ClickHouse message type: %s", response_type)
            message.ack()
            return

        try:
            handler(response)
        except Exception as e:
            current_app.logger.error(
                "Error in ClickHouse handler for '%s': %s",
                response_type, str(e), exc_info=True
            )
            sentry_sdk.capture_exception(e)
        message.ack()

    def get_consumers(self, _, channel):
        return [
            Consumer(
                channel,
                prefetch_count=PREFETCH_COUNT,
                queues=[queues.CLICKHOUSE_RESULT_QUEUE],
                on_message=self.callback,
            )
        ]

    def init_rabbitmq_connection(self):
        """Initialize RabbitMQ connection."""
        self.connection = create_rabbitmq_connection(current_app.config)

    def start(self):
        """Start the consumer."""
        while True:
            try:
                current_app.logger.info("ClickHouse result consumer starting...")
                self.init_rabbitmq_connection()
                self.run()
            except KeyboardInterrupt:
                current_app.logger.info("ClickHouse result consumer stopped by keyboard interrupt")
                break
            except Exception:
                current_app.logger.error("Error in ClickHouse result consumer:", exc_info=True)
                time.sleep(3)


def main():
    """Entry point for the ClickHouse result consumer."""
    with create_app().app_context():
        queues.init_queues(current_app.config)
        consumer = ClickHouseResultConsumer()
        consumer.start()


if __name__ == "__main__":
    main()
