import sys
from time import sleep
import pika
import pika_pool

_rabbitmq = None

def init_rabbitmq_connection(app):
    """Create a connection to the RabbitMQ server."""
    global _rabbitmq

    if "RABBITMQ_HOST" not in app.config:
        app.logger.error("RabbitMQ host:port not defined. Sleeping 2 seconds, and exiting.")
        sleep(2)
        sys.exit(-1)

    credentials = pika.PlainCredentials(app.config['RABBITMQ_USERNAME'], app.config['RABBITMQ_PASSWORD'])
    connection_parameters = pika.ConnectionParameters(
            host=app.config['RABBITMQ_HOST'],
            port=app.config['RABBITMQ_PORT'],
            virtual_host=app.config['RABBITMQ_VHOST'],
            credentials=credentials
        )

    while True:
        try:
            _rabbitmq = pika_pool.QueuedPool(
                    create=lambda: pika.BlockingConnection(connection_parameters),
                    max_size=100,
                    max_overflow=10,
                    timeout=10,
                    recycle=3600,
                    stale=45,
            )
            return
        except Exception as err:
            app.logger.error("Cannot connect to rabbitmq, sleeping 2 seconds")
            sleep(2)
            continue
