import sys
import queue
from time import sleep
import pika
import listenbrainz.utils as utils

_rabbitmq = None

def init_rabbitmq_connection(app):
    """Initialize the webserver rabbitmq connection.

    This initializes _rabbitmq as a connection pool from which new RabbitMQ
    connections can be acquired.
    """
    global _rabbitmq

    if "RABBITMQ_HOST" not in app.config:
        app.logger.error("RabbitMQ host:port not defined. Sleeping 2 seconds, and exiting.")
        sleep(2)
        sys.exit(-1)

    connection_parameters = pika.ConnectionParameters(
        host=app.config['RABBITMQ_HOST'],
        port=app.config['RABBITMQ_PORT'],
        virtual_host=app.config['RABBITMQ_VHOST'],
        credentials=pika.PlainCredentials(app.config['RABBITMQ_USERNAME'], app.config['RABBITMQ_PASSWORD']),
    )

    _rabbitmq = RabbitMQConnectionPool(connection_parameters, 10)
    _rabbitmq.add()
    app.logger.error('Connection to RabbitMQ established!')


class RabbitMQConnectionPool:
    def __init__(self, connection_parameters, max_size):
        self.connection_parameters = connection_parameters
        self.max_size = max_size
        self.queue = queue.Queue(maxsize=max_size)

    def add(self):
        self.queue.put_nowait(self.create())

    def get(self):
        while True:
            try:
                connection, channel = self.queue.get_nowait()
                if connection.is_open:
                    return connection, channel
                else:
                    return self.create()
            except queue.Empty:
                self.add()

    def release(self, connection, channel):
        try:
            if connection.is_open:
                self.queue.put_nowait((connection, channel))
        except queue.Full:
            connection.close()

    def create(self):
        connection = pika.BlockingConnection(self.connection_parameters)
        channel = connection.channel()
        return connection, channel
