import sys
from time import sleep
import pika
import pika_pool
import listenbrainz.utils as utils

_rabbitmq = None

def init_rabbitmq_connection(app):
    """Create a connection to the RabbitMQ server."""
    global _rabbitmq

    if "RABBITMQ_HOST" not in app.config:
        app.logger.error("RabbitMQ host:port not defined. Sleeping 2 seconds, and exiting.")
        sleep(2)
        sys.exit(-1)

    connection_config = {
        'username': app.config['RABBITMQ_USERNAME'],
        'password': app.config['RABBITMQ_PASSWORD'],
        'host': app.config['RABBITMQ_HOST'],
        'port': app.config['RABBITMQ_PORT'],
        'virtual_host': app.config['RABBITMQ_VHOST']
    }

    connection = utils.connect_to_rabbitmq(**connection_config,
                                           error_logger=app.logger.error,
                                           error_retry_delay=2)

    _rabbitmq = pika_pool.QueuedPool(
        create=lambda: connection,
        max_size=100,
        max_overflow=10,
        timeout=10,
        recycle=3600,
        stale=45,
    )
