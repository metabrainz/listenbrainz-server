import sys
from time import sleep
import pika
import pika_pool
import listenbrainz.utils as utils

_rabbitmq = None

def init_rabbitmq_connection(app):
    """Initialize the webserver rabbitmq connection.

    This initializes _rabbitmq as a connection pool from which new RabbitMQ
    connections can be acquired.
    """
    global _rabbitmq

    if "RABBITMQ_HOST" not in app.config:
        raise ConnectionError("Cannot connect to RabbitMQ: host and port not defined")

    connection_parameters = pika.ConnectionParameters(
        host=app.config['RABBITMQ_HOST'],
        port=app.config['RABBITMQ_PORT'],
        virtual_host=app.config['RABBITMQ_VHOST'],
        credentials=pika.PlainCredentials(app.config['RABBITMQ_USERNAME'], app.config['RABBITMQ_PASSWORD']),
    )

    _rabbitmq = pika_pool.QueuedPool(
        create=lambda: pika.BlockingConnection(connection_parameters),
        max_size=100,
        max_overflow=10,
        timeout=10,
        recycle=3600,
        stale=45,
    )
