import pika
import logging
from listenbrainz_spark import config
import time
import json
import sys

class SparkReader():
    def __init__(self):
        self.unique_ch = None
        self.ERROR_RETRY_DELAY = 3

    def connect_to_rabbitmq(self):
        """Creates a RabbitMQ connection object
        """
        username = config.RABBITMQ['RABBITMQ_USERNAME']
        password = config.RABBITMQ['RABBITMQ_PASSWORD']
        host = config.RABBITMQ['RABBITMQ_HOST']
        port = config.RABBITMQ['RABBITMQ_PORT']
        virtual_host = config.RABBITMQ['RABBITMQ_VHOST']

        while True:
            try:
                credentials = pika.PlainCredentials(username, password)
                connection_parameters = pika.ConnectionParameters(
                    host=host,
                    port=port,
                    virtual_host=virtual_host,
                    credentials=credentials,
                )
                self.connection =  pika.BlockingConnection(connection_parameters)
                break
            except Exception as err:
                error_message = "Cannot connect to RabbitMQ: {error}, retrying in {delay} seconds."
                print(error_message.format(error=str(err), delay=self.ERROR_RETRY_DELAY))
                time.sleep(self.ERROR_RETRY_DELAY)

    def start(self, data):
        """Publish data to RabbitMQ
        """
        if "RABBITMQ_HOST" not in config.RABBITMQ:
            logging.critical("RabbitMQ service not defined. Sleeping {0} seconds and exiting.".format(self.ERROR_RETRY_DELAY))
            time.sleep(self.ERROR_RETRY_DELAY)
            sys.exit(-1)

        try:
            self.connect_to_rabbitmq()
            self.unique_ch = self.connection.channel()
            self.unique_ch.exchange_declare(exchange=config.RABBITMQ['SPARK_EXCHANGE'], exchange_type='fanout')
            self.unique_ch.queue_declare(queue=config.RABBITMQ['SPARK_QUEUE'], durable=True)
            self.unique_ch.queue_bind(exchange=config.RABBITMQ['SPARK_EXCHANGE'], queue=config.RABBITMQ['SPARK_QUEUE'])
            self.unique_ch.basic_publish(
                exchange=config.RABBITMQ['SPARK_EXCHANGE'],
                routing_key='',
                body=json.dumps(data),
                properties=pika.BasicProperties(delivery_mode = 2,),
            )
        except pika.exceptions.ConnectionClosed as e:
            logging.error("Connection to rabbitmq closed while trying to publish: %s" % str(e), exc_info=True)
        except Exception as e:
            logging.error("Cannot publish to rabbitmq channel: %s / %s" % (type(e).__name__, str(e)), exc_info=True)
