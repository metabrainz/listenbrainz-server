# listenbrainz-labs
#
# Copyright (C) 2019 Param Singh <iliekcomputers@gmail.com>
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.

import json
import socket
import time
import logging

from kombu import Exchange, Queue, Message, Connection, Consumer
from kombu.entity import PERSISTENT_DELIVERY_MODE
from kombu.mixins import ConsumerProducerMixin

import listenbrainz_spark
import listenbrainz_spark.query_map
from listenbrainz_spark import config, hdfs_connection


RABBITMQ_HEARTBEAT_TIME = 2 * 60 * 60  # 2 hours -- a full dump import takes 40 minutes right now

logger = logging.getLogger(__name__)


class RequestConsumer(ConsumerProducerMixin):

    def __init__(self):
        self.connection = None

        self.spark_result_exchange = Exchange(config.SPARK_RESULT_EXCHANGE, "fanout", durable=False)
        self.spark_result_queue = Queue(config.SPARK_REQUEST_QUEUE, exchange=self.spark_result_exchange, durable=True)
        self.spark_request_exchange = Exchange(config.SPARK_REQUEST_EXCHANGE, "fanout", durable=False)
        self.spark_request_queue = Queue(config.SPARK_REQUEST_QUEUE, exchange=self.spark_request_exchange, durable=True)

    def get_result(self, request):
        try:
            query = request['query']
            params = request.get('params', {})
        except Exception:
            logger.error('Bad query sent to spark request consumer: %s', json.dumps(request), exc_info=True)
            return None

        logger.info('Query: %s', query)
        logger.info('Params: %s', str(params))

        try:
            query_handler = listenbrainz_spark.query_map.get_query_handler(query)
        except KeyError:
            logger.error("Bad query sent to spark request consumer: %s", query, exc_info=True)
            return None
        except Exception as e:
            logger.error("Error while mapping query to function: %s", str(e), exc_info=True)
            return None

        try:
            # initialize connection to HDFS, the request consumer is a long running process
            # so we try to create a connection everytime before executing a query to avoid
            # affecting subsequent queries in case there's an intermittent connection issue
            hdfs_connection.init_hdfs(config.HDFS_HTTP_URI)
            return query_handler(**params)
        except TypeError as e:
            logger.error(
                "TypeError in the query handler for query '%s', maybe bad params. Error: %s", query, str(e), exc_info=True)
            return None
        except Exception as e:
            logger.error("Error in the query handler for query '%s': %s", query, str(e), exc_info=True)
            return None

    def push_to_result_queue(self, messages):
        logger.debug("Pushing result to RabbitMQ...")
        num_of_messages = 0
        avg_size_of_message = 0
        for message in messages:
            num_of_messages += 1
            body = json.dumps(message)
            avg_size_of_message += len(body)
            self.producer.publish(
                exchange=self.spark_result_exchange,
                routing_key='',
                body=body,
                properties=PERSISTENT_DELIVERY_MODE,
            )

        if num_of_messages:
            avg_size_of_message //= num_of_messages
            logger.info(f"Number of messages sent: {num_of_messages}")
            logger.info(f"Average size of message: {avg_size_of_message} bytes")
        else:
            logger.info("No messages calculated")

    def callback(self, message: Message):
        try:
            request = json.loads(message.body)
            logger.info('Received a request!')
            messages = self.get_result(request)
            if messages:
                self.push_to_result_queue(messages)
            logger.info('Request done!')
        except Exception as e:
            logger.error("Error while processing request: %s", str(e), exc_info=True)

    def get_consumers(self, _, channel):
        return [
            Consumer(channel, queues=[self.spark_request_queue], no_ack=True, on_message=lambda x: self.callback(x))
        ]

    def init_rabbitmq_connection(self):
        connection_name = "spark-request-consumer-" + socket.gethostname()
        self.connection = Connection(
            hostname=config.RABBITMQ_HOST,
            userid=config.RABBITMQ_USERNAME,
            port=config.RABBITMQ_PORT,
            password=config.RABBITMQ_PASSWORD,
            virtual_host=config.RABBITMQ_VHOST,
            transport_options={"client_properties": {"connection_name": connection_name}}
        )

    def start(self, app_name):
        while True:
            try:
                logger.info("Request consumer started!")
                listenbrainz_spark.init_spark_session(app_name)
                self.init_rabbitmq_connection()
                self.run()
            except Exception as e:
                logger.critical("Error in spark-request-consumer: %s", str(e), exc_info=True)
                time.sleep(2)
