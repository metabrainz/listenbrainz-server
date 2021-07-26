import functools
import json
import logging
import threading
import time
from queue import Queue, Empty

import pika

from listenbrainz_spark import config
from listenbrainz_spark.utils import init_rabbitmq

logger = logging.getLogger(__name__)


class ResultPublisher(threading.Thread):

    def __init__(self):
        super().__init__()
        self.queue = Queue(maxsize=2)
        self.connection = None
        self.result_channel = None
        self.done = False

    def add_query(self, connection, channel, delivery_tag, query):
        logger.info("Added a task to internal queue")
        self.queue.put((connection, channel, delivery_tag, query))

    def init_connection(self):
        self.connection = init_rabbitmq(
            username=config.RABBITMQ_USERNAME,
            password=config.RABBITMQ_PASSWORD,
            host=config.RABBITMQ_HOST,
            port=config.RABBITMQ_PORT,
            vhost=config.RABBITMQ_VHOST,
            connection_name="listenbrainz-spark-result-publisher"
        )

    def init_channel(self):
        self.result_channel = self.connection.channel()
        self.result_channel.exchange_declare(
            exchange=config.SPARK_RESULT_EXCHANGE,
            exchange_type='fanout'
        )

    def get_results(self, query_handler, params):
        try:
            return query_handler(**params)
        except TypeError:
            logger.error("TypeError in the query handler for query '%s', "
                         "maybe bad params: ", query_handler, exc_info=True)
            return None
        except Exception:
            logger.error("Error in the query handler for query '%s':",
                         query_handler, exc_info=True)
            return None

    def invoke_query(self, query_handler, params):
        t0 = time.monotonic()
        messages = self.get_results(query_handler, params)
        if messages is None:
            return

        logger.info("Pushing result to RabbitMQ...")
        num_of_messages = 0
        avg_size_of_message = 0

        for message in messages:
            num_of_messages += 1
            body = json.dumps(message)
            avg_size_of_message += len(body)
            while message is not None:
                try:
                    self.result_channel.basic_publish(
                        exchange=config.SPARK_RESULT_EXCHANGE,
                        routing_key='',
                        body=body,
                        properties=pika.BasicProperties(delivery_mode=2, ),
                    )
                    break
                # we do not catch ConnectionClosed exception here because when
                # a connection closes so do all of the channels on it. so if the
                # connection is closed, we have lost the request channel. hence,
                # we'll be unable to ack the request later and receive it again
                # for processing anyways.
                except (pika.exceptions.ChannelClosed, pika.exceptions.ConnectionClosed):
                    logger.error('RabbitMQ Connection error while publishing results:', exc_info=True)
                    time.sleep(1)
                    self.connection.close()
                    self.init_connection()
                    self.init_channel()

        try:
            avg_size_of_message //= num_of_messages
        except ZeroDivisionError:
            avg_size_of_message = 0
            logger.warning("No messages calculated", exc_info=True)

        logger.info("Done!")
        logger.info("Number of messages sent: {}".format(num_of_messages))
        logger.info("Average size of message: {} bytes".format(avg_size_of_message))

        logger.info("Time Taken: %d s", time.monotonic() - t0)
        logger.info('Request done!')

    def run(self):
        logger.info("Starting result publisher")
        self.init_connection()
        self.init_channel()
        while not self.done:
            try:
                connection, channel, delivery_tag, query = self.queue.get(timeout=600)
                self.invoke_query(*query)
                self.queue.task_done()
                callback = functools.partial(channel.basic_ack, delivery_tag)
                connection.add_callback_threadsafe(callback)
            except Empty:
                logger.info("No query received in last 10 minutes")
            except Exception:
                logger.error("Error in result publisher:", exc_info=True)
                self.queue.task_done()
        logger.info("Stopping result publisher")

    def shutdown(self):
        self.done = True
        if self.queue.empty():
            self.queue.put(None)
