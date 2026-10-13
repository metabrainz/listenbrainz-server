#!/usr/bin/env python3
"""Worker consuming requests from CLICKHOUSE_EXCHANGE and running their handlers.

Results are published to CLICKHOUSE_RESULT_EXCHANGE for ListenBrainz.
"""

import json
import logging
import socket
import time
from collections.abc import Iterable

import orjson
import sentry_sdk
from amqp.exceptions import ChannelError, MessageNacked
from kombu import Connection, Exchange, Queue
from kombu.entity import PERSISTENT_DELIVERY_MODE

from clickhouse import config, query_map


logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(name)s - %(message)s'
)
logger = logging.getLogger(__name__)

POLL_INTERVAL = 5
PUBLISH_TIMEOUT = 60
PUBLISH_RETRY_POLICY = {
    "max_retries": 10,
    "interval_start": 1,
    "interval_step": 5,
    "interval_max": 30,
}


class PublishError(Exception):
    """Publishing a result failed even after reconnecting to the broker."""


def _rabbitmq_url(host, port):
    return (
        f"amqp://{config.RABBITMQ_USERNAME}:{config.RABBITMQ_PASSWORD}"
        f"@{host}:{port}/{config.RABBITMQ_VHOST}"
    )


def get_rabbitmq_urls():
    """Return one or more RabbitMQ broker URLs from RABBITMQ_HOSTS."""
    if not config.RABBITMQ_HOSTS:
        raise ConnectionError(
            "RabbitMQ hosts not defined, cannot create RabbitMQ connection..."
        )

    return [_rabbitmq_url(host, port) for host, port in config.RABBITMQ_HOSTS]


def create_rabbitmq_connection(connection_name):
    """Create a connection to RabbitMQ whose publishes wait for the broker's confirmation."""
    return Connection(
        hostname=get_rabbitmq_urls(),
        transport_options={
            "client_properties": {"connection_name": connection_name},
            "confirm_publish": True,
        },
    )


class ClickHouseRequestConsumer:
    """Consumer for ClickHouse requests.

    Requests are fetched one at a time with basic.get, so the ones queued behind a long
    running request stay in the broker. Each is acked before it runs, as dump imports
    outlast RabbitMQ's consumer timeout. Its results are published with confirms and
    republished after reconnecting, so a broker hiccup doesn't lose them. A result the
    broker rejects (e.g. one over RabbitMQ's max message size) is dropped and reported.

    The config is only read at startup, and consul doesn't restart the worker when it
    re-renders it (so as not to kill a running request): restart the worker by hand to
    apply a config change, e.g. a new RabbitMQ host or password.
    """

    def __init__(self):
        self.connection = None
        self.producer = None
        self.publish_retry_policy = PUBLISH_RETRY_POLICY

        self.clickhouse_exchange = Exchange(
            config.CLICKHOUSE_EXCHANGE,
            "fanout",
            durable=True,
        )
        self.clickhouse_queue = Queue(
            config.CLICKHOUSE_QUEUE,
            exchange=self.clickhouse_exchange,
            durable=True
        )

        self.clickhouse_result_exchange = Exchange(
            config.CLICKHOUSE_RESULT_EXCHANGE,
            "fanout",
            durable=True,
        )
        self.clickhouse_result_queue = Queue(
            config.CLICKHOUSE_RESULT_QUEUE,
            exchange=self.clickhouse_result_exchange,
            durable=True,
        )

    def get_result(self, request: dict) -> Iterable[dict] | None:
        """Process a request and return the result."""
        if not isinstance(request, dict) or 'query' not in request:
            logger.error('Bad query sent to ClickHouse request consumer: %s', json.dumps(request))
            return None
        query = request['query']
        params = request.get('params', {})
        logger.info('Query: %s, params: %s', query, params)

        query_handler = query_map.functions.get(query)
        if query_handler is None:
            logger.error("Unknown query: %s", query)
            return None

        return query_handler(**params)

    def publish(self, body: bytes) -> bool:
        """Publish a result body, reconnecting and retrying on broker errors.

        Returns whether the broker accepted it. A rejected body is dropped. Unless the broker
        just nacked it, it also closed the producer's channel, so the producer moves to a new one.
        """
        try:
            self.producer.publish(
                exchange=self.clickhouse_result_exchange,
                routing_key="",
                body=body,
                delivery_mode=PERSISTENT_DELIVERY_MODE,
                timeout=PUBLISH_TIMEOUT,
                retry=True,
                retry_policy=self.publish_retry_policy,
            )
            return True
        except (ChannelError, MessageNacked) as e:
            logger.error("RabbitMQ rejected a ClickHouse result message of %d bytes, dropping it: %s",
                         len(body), str(e), exc_info=True)
            sentry_sdk.capture_exception(e)
            if isinstance(e, ChannelError):
                self.producer.revive(self.connection.channel())
            return False
        except Exception as e:
            raise PublishError("Failed to publish ClickHouse result") from e

    def push_to_result_queue(self, messages: Iterable[dict]) -> int:
        """Push result messages to the result exchange.

        A message that cannot be serialized or that the broker rejects is skipped. Errors
        raised by the handler while generating messages propagate, as do PublishErrors.
        """
        if not messages:
            return 0

        message_count = 0
        total_size = 0
        for message in messages:
            try:
                body = orjson.dumps(message, option=orjson.OPT_NON_STR_KEYS)
            except TypeError as e:
                logger.error("Skipping ClickHouse result message of type %s that cannot be serialized: %s",
                             message.get("type"), str(e), exc_info=True)
                sentry_sdk.capture_exception(e)
                continue
            if self.publish(body):
                total_size += len(body)
                message_count += 1
        if message_count:
            logger.info(
                "Pushed %d ClickHouse result messages, average size %d bytes",
                message_count,
                total_size // message_count,
            )
        else:
            logger.info("No ClickHouse result messages generated")
        return message_count

    def callback(self, body):
        """Handle incoming message."""
        try:
            request = json.loads(body)
            logger.info('Received a request!')
            results = self.get_result(request)
            if results:
                self.push_to_result_queue(results)
            logger.info('Request done!')
        except PublishError as e:
            logger.critical("Broker error while publishing results, restarting consumer: %s",
                            str(e.__cause__), exc_info=True)
            sentry_sdk.capture_exception(e)
            raise
        except Exception as e:
            logger.error("Error while processing request: %s", str(e), exc_info=True)
            sentry_sdk.capture_exception(e)

    def consume(self):
        """Process requests from the queue, one at a time, until a broker error."""
        channel = self.connection.default_channel
        self.clickhouse_result_queue(channel).declare()
        queue = self.clickhouse_queue(channel)
        queue.declare()
        while True:
            message = queue.get(no_ack=False)
            if message is None:
                time.sleep(POLL_INTERVAL)
                continue
            message.ack()
            self.callback(message.body)

    def init_rabbitmq_connection(self):
        """Initialize RabbitMQ connection and producer."""
        connection_name = "clickhouse-request-consumer-" + socket.gethostname()
        self.connection = create_rabbitmq_connection(connection_name)
        # a channel of its own, as the broker closes it over a rejected message
        self.producer = self.connection.Producer(channel=self.connection.channel())

    def start(self):
        """Start the consumer."""
        while True:
            try:
                logger.info("ClickHouse request consumer starting...")
                self.init_rabbitmq_connection()
                self.consume()
            except Exception as e:
                logger.critical("Error in ClickHouse request consumer: %s", str(e), exc_info=True)
                if self.connection is not None:
                    self.connection.release()
                time.sleep(2)


def main():
    """Entry point for the consumer."""
    sentry_sdk.init(**config.LOG_SENTRY)
    consumer = ClickHouseRequestConsumer()
    consumer.start()


if __name__ == '__main__':
    main()
