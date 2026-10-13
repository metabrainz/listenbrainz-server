#!/usr/bin/env python3
"""
ClickHouse Bulk Request Consumer

Consumes bulk/management requests from the CLICKHOUSE_EXCHANGE queue and
invokes the appropriate handlers. Handles long-running operations such as:
- Stats computation (hourly, full refresh)
- Listen dump loading (full, incremental)
- Listen deletion import

Results are pushed to CLICKHOUSE_RESULT_EXCHANGE for the ListenBrainz side.
"""

import json
import logging
import socket
import time
from collections.abc import Iterable

from kombu import Connection, Exchange, Queue
from kombu.entity import PERSISTENT_DELIVERY_MODE

from clickhouse import config, query_map


logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(name)s - %(message)s'
)
logger = logging.getLogger(__name__)

# RabbitMQ default max_message_size. Anything larger is rejected with a channel
# error (406 PRECONDITION_FAILED) that tears down the channel mid-batch.
RABBITMQ_MAX_MESSAGE_BYTES = 16 * 1024 * 1024

# Seconds to wait before polling an empty request queue again.
POLL_INTERVAL = 5


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
    return Connection(
        hostname=get_rabbitmq_urls(),
        transport_options={"client_properties": {"connection_name": connection_name}},
    )


class ClickHouseRequestConsumer:
    """Consumer for ClickHouse stats and management requests.

    Requests are fetched one at a time with basic.get rather than pushed by a broker
    consumer, so the requests queued behind a running one (dump imports take hours)
    stay in the broker and survive a restart. Each request is acked before it runs:
    acking after it would hold the delivery unacknowledged for longer than RabbitMQ's
    consumer timeout.
    """

    def __init__(self):
        self.connection = None
        self.producer = None

        # ClickHouse bulk request exchange and queue (stats, cache refresh, dump loading)
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

        # Result exchange for sending results back to ListenBrainz
        self.clickhouse_result_exchange = Exchange(
            config.CLICKHOUSE_RESULT_EXCHANGE,
            "fanout",
            durable=True,
        )

    def get_result(self, request: dict) -> Iterable[dict] | None:
        """Process a request and return the result."""
        try:
            query = request['query']
            params = request.get('params', {})
        except Exception:
            logger.error('Bad query sent to ClickHouse request consumer: %s',
                        json.dumps(request), exc_info=True)
            return None

        logger.info('Query: %s', query)
        logger.info('Params: %s', str(params))

        try:
            query_handler = query_map.get_query_handler(query)
        except KeyError:
            logger.error("Unknown query: %s", query, exc_info=True)
            return None
        except Exception as e:
            logger.error("Error while mapping query to function: %s", str(e), exc_info=True)
            return None

        try:
            return query_handler(**params)
        except TypeError as e:
            logger.error(
                "TypeError in handler for query '%s', maybe bad params. Error: %s",
                query, str(e), exc_info=True
            )
            return None
        except Exception as e:
            logger.error("Error in handler for query '%s': %s", query, str(e), exc_info=True)
            return None

    def push_to_result_queue(self, messages: Iterable[dict]) -> int:
        """Push result messages to the result exchange."""
        if not messages:
            return 0

        message_count = 0
        total_size = 0
        for message in messages:
            body = json.dumps(message)
            if len(body) > RABBITMQ_MAX_MESSAGE_BYTES:
                logger.error(
                    "Dropping ClickHouse result message of type %s: size %d bytes exceeds "
                    "RabbitMQ max message size %d",
                    message.get("type"), len(body), RABBITMQ_MAX_MESSAGE_BYTES,
                )
                continue
            total_size += len(body)
            self.producer.publish(
                exchange=self.clickhouse_result_exchange,
                routing_key="",
                body=body,
                delivery_mode=PERSISTENT_DELIVERY_MODE,
                declare=[self.clickhouse_result_exchange],
            )
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
        except self._broker_errors() as e:
            # A channel/connection error (e.g. 406 PRECONDITION_FAILED from an
            # oversized publish) closes the channel the producer shares with the
            # request queue. Re-raise so start() reconnects.
            logger.error("Broker error while processing request, restarting consumer: %s",
                         str(e), exc_info=True)
            raise
        except Exception as e:
            logger.error("Error while processing request: %s", str(e), exc_info=True)

    def _broker_errors(self) -> tuple:
        if self.connection is None:
            return ()
        return tuple(self.connection.connection_errors) + tuple(self.connection.channel_errors)

    def consume(self):
        """Process requests from the queue, one at a time, until a broker error."""
        queue = self.clickhouse_queue(self.connection.default_channel)
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
        # Create producer for pushing results
        self.producer = self.connection.Producer()

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
    consumer = ClickHouseRequestConsumer()
    consumer.start()


if __name__ == '__main__':
    main()
