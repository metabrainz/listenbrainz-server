#!/usr/bin/env python3
"""
ClickHouse Request Consumer

Consumes stats/management requests from the CLICKHOUSE_EXCHANGE queue
and invokes the appropriate handlers. Results are pushed to the
CLICKHOUSE_RESULT_EXCHANGE for processing by the ListenBrainz side.
"""

import json
import logging
import socket
import time

from kombu import Connection, Consumer, Exchange, Queue
from kombu.entity import PERSISTENT_DELIVERY_MODE
from kombu.mixins import ConsumerMixin

import config
import query_map

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(name)s - %(message)s'
)
logger = logging.getLogger(__name__)


class ClickHouseRequestConsumer(ConsumerMixin):
    """Consumer for ClickHouse stats and management requests."""

    def __init__(self):
        self.connection = None
        self.producer = None

        # ClickHouse request exchange and queue
        self.clickhouse_exchange = Exchange(
            config.CLICKHOUSE_EXCHANGE,
            "fanout",
            durable=False
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
            durable=False
        )

    def get_result(self, request: dict) -> list[dict] | None:
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

    def push_to_result_queue(self, messages):
        """Push result messages to the result exchange."""
        if not messages:
            return

        logger.debug("Pushing %d results to result queue...", len(messages))
        for message in messages:
            body = json.dumps(message)
            self.producer.publish(
                exchange=self.clickhouse_result_exchange,
                routing_key='',
                body=body,
                properties=PERSISTENT_DELIVERY_MODE,
            )
        logger.debug("Results pushed to queue")

    def callback(self, body, message):
        """Handle incoming message."""
        try:
            request = json.loads(body)
            logger.info('Received a request!')
            results = self.get_result(request)
            if results:
                self.push_to_result_queue(results)
                for result in results:
                    logger.info('Result: %s', json.dumps(result))
            logger.info('Request done!')
        except Exception as e:
            logger.error("Error while processing request: %s", str(e), exc_info=True)
        finally:
            message.ack()

    def get_consumers(self, Consumer, channel):
        return [
            Consumer(
                queues=[self.clickhouse_queue],
                on_message=lambda x: self.callback(x.body, x),
                prefetch_count=1,
            )
        ]

    def init_rabbitmq_connection(self):
        """Initialize RabbitMQ connection and producer."""
        connection_name = "clickhouse-request-consumer-" + socket.gethostname()
        self.connection = Connection(
            hostname=config.RABBITMQ_HOST,
            userid=config.RABBITMQ_USERNAME,
            port=config.RABBITMQ_PORT,
            password=config.RABBITMQ_PASSWORD,
            virtual_host=config.RABBITMQ_VHOST,
            transport_options={"client_properties": {"connection_name": connection_name}}
        )
        # Create producer for pushing results
        self.producer = self.connection.Producer()

    def start(self):
        """Start the consumer."""
        while True:
            try:
                logger.info("ClickHouse request consumer starting...")
                self.init_rabbitmq_connection()
                self.run()
            except Exception as e:
                logger.critical("Error in ClickHouse request consumer: %s", str(e), exc_info=True)
                time.sleep(2)


def main():
    """Entry point for the consumer."""
    consumer = ClickHouseRequestConsumer()
    consumer.start()


if __name__ == '__main__':
    main()
