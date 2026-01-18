"""
ClickHouse Result Reader

Consumes result messages from the ClickHouse stats consumer via RabbitMQ
and dispatches them to the appropriate handlers.
"""
import json
import logging
import time

import orjson
import sentry_sdk
from kombu import Connection, Consumer, Exchange, Queue
from kombu.mixins import ConsumerMixin

from listenbrainz.clickhouse.handlers import get_handler
from listenbrainz.utils import get_fallback_connection_name
from listenbrainz.webserver import create_app, db_conn

logger = logging.getLogger(__name__)

PREFETCH_COUNT = 100


class ClickHouseReader(ConsumerMixin):
    """Consumer for ClickHouse result messages."""

    def __init__(self, app):
        self.app = app
        self.connection = None
        self.clickhouse_result_exchange = Exchange(
            app.config["CLICKHOUSE_RESULT_EXCHANGE"],
            "fanout",
            durable=False
        )
        self.clickhouse_result_queue = Queue(
            app.config["CLICKHOUSE_RESULT_QUEUE"],
            exchange=self.clickhouse_result_exchange,
            durable=True
        )

    def callback(self, message):
        """Handle incoming message from ClickHouse result queue."""
        try:
            response = orjson.loads(message.body)
        except Exception:
            self.app.logger.error("Error parsing message: %s", message.body, exc_info=True)
            message.ack()
            return

        try:
            response_type = response.get("type")
            if not response_type:
                self.app.logger.error("No type in message: %s", json.dumps(response, indent=2))
                message.ack()
                return

            self.app.logger.info("Received ClickHouse message: %s", response_type)
        except Exception:
            self.app.logger.error("Error processing message: %s", json.dumps(response, indent=2), exc_info=True)
            message.ack()
            return

        handler = get_handler(response_type)
        if not handler:
            self.app.logger.warning("Unknown ClickHouse message type: %s", response_type)
            message.ack()
            return

        try:
            with self.app.app_context():
                handler(response)
        except Exception as e:
            self.app.logger.error(
                "Error in ClickHouse handler for '%s': %s",
                response_type, str(e), exc_info=True
            )
            sentry_sdk.capture_exception(e)
        finally:
            db_conn.rollback()
            message.ack()

    def get_consumers(self, _, channel):
        return [
            Consumer(
                channel,
                prefetch_count=PREFETCH_COUNT,
                queues=[self.clickhouse_result_queue],
                on_message=lambda msg: self.callback(msg)
            )
        ]

    def init_rabbitmq_connection(self):
        """Initialize RabbitMQ connection."""
        self.connection = Connection(
            hostname=self.app.config["RABBITMQ_HOST"],
            userid=self.app.config["RABBITMQ_USERNAME"],
            port=self.app.config["RABBITMQ_PORT"],
            password=self.app.config["RABBITMQ_PASSWORD"],
            virtual_host=self.app.config["RABBITMQ_VHOST"],
            transport_options={"client_properties": {"connection_name": get_fallback_connection_name()}}
        )

    def start(self):
        """Start the consumer."""
        while True:
            try:
                self.app.logger.info("ClickHouse result reader starting...")
                self.init_rabbitmq_connection()
                self.run()
            except KeyboardInterrupt:
                self.app.logger.info("ClickHouse result reader stopped by keyboard interrupt")
                break
            except Exception:
                self.app.logger.error("Error in ClickHouse result reader:", exc_info=True)
                time.sleep(3)


def main():
    """Entry point for the ClickHouse result reader."""
    app = create_app()
    reader = ClickHouseReader(app)
    reader.start()


if __name__ == "__main__":
    main()
