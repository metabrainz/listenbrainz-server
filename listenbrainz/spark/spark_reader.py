#!/usr/bin/env python3
import time

from kombu import Connection, Message, Consumer, Exchange, Queue
from kombu.mixins import ConsumerMixin

from listenbrainz.spark.background import BackgroundJobProcessor
from listenbrainz.utils import get_fallback_connection_name
from listenbrainz.webserver import create_app

PREFETCH_COUNT = 1000


class SparkReader(ConsumerMixin):

    def __init__(self, app):
        self.app = app
        self.connection: Connection | None = None
        self.spark_result_exchange = Exchange(app.config["SPARK_RESULT_EXCHANGE"], "fanout", durable=False)
        self.spark_result_queue = Queue(app.config["SPARK_RESULT_QUEUE"], exchange=self.spark_result_exchange,
                                        durable=True)
        self.response_handlers = {}
        self.processor: BackgroundJobProcessor | None = None

    def callback(self, message: Message):
        """ Handle the data received from the queue and insert into the database accordingly. """
        self.app.logger.debug("Received a message, adding to internal processing queue...")
        self.processor.enqueue(message)

    def on_iteration(self):
        """ Executed periodically in the main consumption loop by kombu, we check for completed messages here
         and acknowledge them. """
        for message in self.processor.pending_acks():
            message.ack()

    def get_consumers(self, _, channel):
        return [Consumer(
            channel,
            prefetch_count=PREFETCH_COUNT,
            queues=[self.spark_result_queue],
            on_message=lambda msg: self.callback(msg)
        )]

    def init_rabbitmq_connection(self):
        self.connection = Connection(
            hostname=self.app.config["RABBITMQ_HOST"],
            userid=self.app.config["RABBITMQ_USERNAME"],
            port=self.app.config["RABBITMQ_PORT"],
            password=self.app.config["RABBITMQ_PASSWORD"],
            virtual_host=self.app.config["RABBITMQ_VHOST"],
            transport_options={"client_properties": {"connection_name": get_fallback_connection_name()}}
        )

    def start(self):
        """ initiates RabbitMQ connection and starts consuming from the queue """
        while True:
            try:
                self.app.logger.info("Spark consumer has started!")
                self.init_rabbitmq_connection()

                self.processor = BackgroundJobProcessor(self.app)
                self.processor.start()

                self.run()
                self.processor.terminate()
            except KeyboardInterrupt:
                self.app.logger.error("Keyboard interrupt!")
                if self.processor is not None:
                    self.processor.terminate()
                break
            except Exception:
                self.app.logger.error("Error in SparkReader:", exc_info=True)
                if self.processor is not None:
                    self.processor.terminate()
                time.sleep(3)


if __name__ == '__main__':
    sr = SparkReader(create_app())
    sr.start()
