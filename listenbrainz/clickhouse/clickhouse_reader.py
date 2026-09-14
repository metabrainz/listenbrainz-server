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
from kombu import Consumer, Exchange, Queue
from kombu.mixins import ConsumerMixin

from listenbrainz.clickhouse.handlers import get_handler
from listenbrainz.db import couchdb
from listenbrainz.rabbitmq import create_rabbitmq_connection
from listenbrainz.webserver import create_app, db_conn

logger = logging.getLogger(__name__)

PREFETCH_COUNT = 100


def init_clickhouse_reader_couchdb(app):
    """Initialize CouchDB for the ClickHouse result reader.

    The reader writes to the ClickHouse stats CouchDB instance (same database names as
    the Spark stats, different instance), so it overrides the default couchdb connection
    set up by create_app.
    """
    host = app.config["CLICKHOUSE_READER_COUCHDB_HOST"]
    if not host or str(host).startswith(("KEYDOESNOTEXIST", "SERVICEDOESNOTEXIST")):
        raise RuntimeError(
            f"CLICKHOUSE_READER_COUCHDB_HOST is not configured ({host!r}), cannot start ClickHouse reader"
        )
    couchdb.init(
        app.config["CLICKHOUSE_READER_COUCHDB_USER"],
        app.config["CLICKHOUSE_READER_COUCHDB_ADMIN_KEY"],
        host,
        app.config["CLICKHOUSE_READER_COUCHDB_PORT"],
        app.config.get("COUCHDB_DATABASE_PREFIX", ""),
    )
    app.logger.info(
        "Initialized ClickHouse reader CouchDB connection: %s:%s",
        host, app.config["CLICKHOUSE_READER_COUCHDB_PORT"],
    )


class ClickHouseReader(ConsumerMixin):
    """Consumer for ClickHouse result messages."""

    def __init__(self, app):
        self.app = app
        init_clickhouse_reader_couchdb(app)
        self.connection = None
        self.clickhouse_result_exchange = Exchange(
            app.config["CLICKHOUSE_RESULT_EXCHANGE"],
            "fanout",
            durable=True
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
                try:
                    handler(response)
                except Exception as e:
                    self.app.logger.error(
                        "Error in ClickHouse handler for '%s': %s",
                        response_type, str(e), exc_info=True
                    )
                    sentry_sdk.capture_exception(e)
                finally:
                    db_conn.rollback()
        finally:
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
        self.connection = create_rabbitmq_connection(self.app.config)

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
