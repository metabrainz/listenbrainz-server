import pika
import logging
from listenbrainz_spark import config
import time
import json
import sys

class StatsWriter():
    def __init__(self):
        self.unique_ch = None
        self.ERROR_RETRY_DELAY = 3

    def connect_to_rabbitmq(self):
        """Creates a RabbitMQ connection object
        """
        username = config.RABBITMQ_USERNAME
        password = config.RABBITMQ_PASSWORD
        host = config.RABBITMQ_HOST
        port = config.RABBITMQ_PORT
        virtual_host = config.RABBITMQ_VHOST

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
            except pika.exceptions.AMQPChannelError as err:
                logging.error("Caught a channel error: %s / %s, stopping..." % (type(err).__name__, str(err)))
                break
            except Exception as err:
                error_message = "Cannot connect to RabbitMQ: {error}, retrying in {delay} seconds."
                print(error_message.format(error=str(err), delay=self.ERROR_RETRY_DELAY))
                time.sleep(self.ERROR_RETRY_DELAY)

    def write(self, data, exchange):
        """Publishes data to RabbitMQ
        """
        try:
            self.unique_ch.basic_publish(
                exchange=exchange,
                routing_key='',
                body=json.dumps(data),
                properties=pika.BasicProperties(delivery_mode = 2,),
            )
            return True
        except pika.exceptions.ConnectionClosed:
            logging.error("Connection to rabbitmq closed while trying to publish. Re-opening.", exc_info=True)
        except:
            return False

    def start(self, data, exchange, queue):
        """Establishes connection to RabbitMQ if not connected.
           If connected, attempts to write to the queue.
        """
        if not config.RABBITMQ_HOST:
            logging.critical("RabbitMQ service not defined. Sleeping {0} seconds and exiting.".format(self.ERROR_RETRY_DELAY))
            time.sleep(self.ERROR_RETRY_DELAY)
            sys.exit(-1)

        while True:
            if self.unique_ch:
                if self.write(data, exchange):
                    break
                else:
                    self.connection.close()
                    self.unique_ch = None
            else:
                self.connect_to_rabbitmq()
                self.unique_ch = self.connection.channel()
                self.unique_ch.exchange_declare(exchange=exchange, exchange_type='fanout')
                self.unique_ch.queue_declare(queue=queue, durable=True)
                self.unique_ch.queue_bind(exchange=exchange, queue=queue)
