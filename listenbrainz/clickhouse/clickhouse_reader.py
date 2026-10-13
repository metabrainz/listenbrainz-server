"""Consumes ClickHouse result messages and dispatches them to their handlers."""
import json
import logging
import time

import orjson
import sentry_sdk
from kombu import Consumer, Exchange, Queue
from kombu.mixins import ConsumerMixin
from requests import ConnectionError, HTTPError, Timeout

from listenbrainz.clickhouse.handlers import get_handler
from listenbrainz.db.couchdb import CouchDBConnection
from listenbrainz.rabbitmq import create_rabbitmq_connection
from listenbrainz.webserver import create_app

logger = logging.getLogger(__name__)

PREFETCH_COUNT = 100

# Delays in seconds between the attempts at handling a message failing with a transient error.
RETRY_DELAYS = (5, 10, 20, 40, 80)

# Seconds to wait for the ClickHouse reader CouchDB instance to connect and to respond.
COUCHDB_TIMEOUT = (10, 300)


class TransientHandlerError(Exception):
    """A handler kept failing with a transient error, the message should be redelivered later."""


def is_retryable(error: Exception) -> bool:
    """Whether a handler error is a transient CouchDB failure worth retrying the message for."""
    if isinstance(error, HTTPError):
        return error.response is not None and (
            error.response.status_code >= 500 or error.response.status_code == 429
        )
    return isinstance(error, (ConnectionError, Timeout))


def create_clickhouse_reader_couchdb(config) -> CouchDBConnection:
    """Create the connection to the CouchDB instance the ClickHouse stats are written to."""
    return CouchDBConnection(
        config["CLICKHOUSE_READER_COUCHDB_USER"],
        config["CLICKHOUSE_READER_COUCHDB_ADMIN_KEY"],
        config["CLICKHOUSE_READER_COUCHDB_HOST"],
        config["CLICKHOUSE_READER_COUCHDB_PORT"],
        config["COUCHDB_DATABASE_PREFIX"],
        timeout=COUCHDB_TIMEOUT,
    )


class ClickHouseReader(ConsumerMixin):
    """Consumer for ClickHouse result messages.

    Messages are handled in the order they arrive, as the handlers of a stats run depend on
    the ones before. So a message failing with a transient error is retried in place, and if
    it keeps failing the consumer restarts without acking it, to get it redelivered first.
    """

    def __init__(self, app):
        self.app = app
        self.retry_delays = RETRY_DELAYS
        self.couchdb = create_clickhouse_reader_couchdb(app.config)
        app.logger.info(
            "Initialized ClickHouse reader CouchDB connection: %s:%s",
            self.couchdb.host, self.couchdb.port,
        )
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

    def run_handler(self, handler, response, response_type):
        """Run the handler, retrying it in place while it fails with a transient error."""
        for delay in (*self.retry_delays, None):
            try:
                with self.app.app_context():
                    handler(response, self.couchdb)
                return
            except Exception as e:
                if not is_retryable(e):
                    raise
                if delay is None:
                    raise TransientHandlerError(f"ClickHouse handler for '{response_type}' kept failing") from e
                self.app.logger.warning(
                    "Transient error in ClickHouse handler for '%s', retrying in %d seconds: %s",
                    response_type, delay, str(e),
                )
                time.sleep(delay)

    def callback(self, message):
        """Handle incoming message from ClickHouse result queue."""
        try:
            response = orjson.loads(message.body)
            response_type = response.get("type")
        except Exception:
            self.app.logger.error("Error parsing message: %s", message.body, exc_info=True)
            message.ack()
            return

        if not response_type:
            self.app.logger.error("No type in message: %s", json.dumps(response, indent=2))
            message.ack()
            return
        self.app.logger.info("Received ClickHouse message: %s", response_type)

        handler = get_handler(response_type)
        if not handler:
            self.app.logger.warning("Unknown ClickHouse message type: %s", response_type)
            message.ack()
            return

        try:
            self.run_handler(handler, response, response_type)
        except TransientHandlerError as e:
            sentry_sdk.capture_exception(e)
            # leave the message unacked, the broker requeues it in place when the consumer's
            # connection closes on the way to restarting
            raise
        except Exception as e:
            self.app.logger.error(
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
                queues=[self.clickhouse_result_queue],
                on_message=self.callback,
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
