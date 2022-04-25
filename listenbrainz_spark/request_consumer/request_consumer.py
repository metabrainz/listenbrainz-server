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

import pika
import json
import time
import logging

import listenbrainz_spark
import listenbrainz_spark.query_map
from listenbrainz_spark import config, hdfs_connection
from listenbrainz_spark.utils import init_rabbitmq

from py4j.protocol import Py4JJavaError

RABBITMQ_HEARTBEAT_TIME = 2 * 60 * 60  # 2 hours -- a full dump import takes 40 minutes right now

rc = None
logger = logging.getLogger(__name__)


class RequestConsumer:

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
            body = message
            avg_size_of_message += len(body)
            while message is not None:
                try:
                    self.result_channel.basic_publish(
                        exchange=config.SPARK_RESULT_EXCHANGE,
                        routing_key='',
                        body=body,
                        properties=pika.BasicProperties(delivery_mode=2,),
                    )
                    break
                except (pika.exceptions.ConnectionClosed, pika.exceptions.ChannelClosed) as e:
                    logger.error('RabbitMQ Connection error while publishing results: %s', str(e), exc_info=True)
                    time.sleep(1)
                    self.rabbitmq.close()
                    self.connect_to_rabbitmq()
                    self.init_rabbitmq_channels()

        try:
            avg_size_of_message //= num_of_messages
        except ZeroDivisionError:
            avg_size_of_message = 0
            logger.warning("No messages calculated", exc_info=True)

        logger.info("Done!")
        logger.info("Number of messages sent: {}".format(num_of_messages))
        logger.info("Average size of message: {} bytes".format(avg_size_of_message))

    def callback(self, channel, method, properties, body):
        request = json.loads(body.decode('utf-8'))
        logger.info('Received a request!')
        while True:
            try:
                self.request_channel.basic_ack(delivery_tag=method.delivery_tag)
                break
            except (pika.exceptions.ConnectionClosed, pika.exceptions.ChannelClosed) as e:
                if str(e).find("is larger than configured max size") >= 0:
                    logger.error("Spark attempted to send a message larger than the allowed maximum message size.")
                else:
                    logger.error('RabbitMQ Connection error when acknowledging request: %s', str(e), exc_info=True)
                time.sleep(1)
                self.rabbitmq.close()
                self.connect_to_rabbitmq()
                self.init_rabbitmq_channels()

        messages = self.get_result(request)
        if messages:
            self.push_to_result_queue(messages)

        logger.info('Request done!')

    def connect_to_rabbitmq(self):
        self.rabbitmq = init_rabbitmq(
            username=config.RABBITMQ_USERNAME,
            password=config.RABBITMQ_PASSWORD,
            host=config.RABBITMQ_HOST,
            port=config.RABBITMQ_PORT,
            vhost=config.RABBITMQ_VHOST,
            log=logger.critical,
            heartbeat=RABBITMQ_HEARTBEAT_TIME,
        )

    def init_rabbitmq_channels(self):
        self.request_channel = self.rabbitmq.channel()
        self.request_channel.exchange_declare(exchange=config.SPARK_REQUEST_EXCHANGE, exchange_type='fanout')
        self.request_channel.queue_declare(config.SPARK_REQUEST_QUEUE, durable=True)
        self.request_channel.queue_bind(
            exchange=config.SPARK_REQUEST_EXCHANGE,
            queue=config.SPARK_REQUEST_QUEUE
        )
        self.request_channel.basic_consume(queue=config.SPARK_REQUEST_QUEUE, on_message_callback=self.callback)

        self.result_channel = self.rabbitmq.channel()
        self.result_channel.exchange_declare(exchange=config.SPARK_RESULT_EXCHANGE, exchange_type='fanout')

    def run(self):
        while True:
            try:
                self.connect_to_rabbitmq()
                self.init_rabbitmq_channels()
                logger.info('Request consumer started!')

                try:
                    self.request_channel.start_consuming()
                except pika.exceptions.ConnectionClosed as e:
                    logger.error('connection to rabbitmq closed: %s', str(e), exc_info=True)
                    self.rabbitmq.close()
                    continue
                self.rabbitmq.close()
            except Py4JJavaError as e:
                logger.critical("Critical: JAVA error in spark-request consumer: %s, message: %s",
                                            str(e), str(e.java_exception), exc_info=True)
                time.sleep(2)
            except Exception as e:
                logger.critical("Error in spark-request-consumer: %s", str(e), exc_info=True)
                time.sleep(2)

    def ping(self):
        """ Sends a heartbeat to rabbitmq to avoid closing the connection during long processes """
        self.rabbitmq.process_data_events(0)


def main(app_name):
    listenbrainz_spark.init_spark_session(app_name)
    global rc
    rc = RequestConsumer()
    rc.run()


if __name__ == '__main__':
    main('spark-writer')
