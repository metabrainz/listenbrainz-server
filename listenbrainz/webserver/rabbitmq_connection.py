import sys
from time import sleep
import pika

_rabbitmq = None

def init_rabbitmq_connection(app):
    """Create a connection to the RabbitMQ server."""
    global _rabbitmq

    app.logger.info("Call to init_rabbit_mq_connection")
    if "RABBITMQ_HOST" not in app.config:
        app.logger.error("RabbitMQ host:port not defined. Sleeping 2 seconds, and exiting.")
        sleep(2)
        sys.exit(-1)

    while True:
        try:
            _rabbitmq = pika.BlockingConnection(pika.ConnectionParameters(host=app.config['RABBITMQ_HOST'], port=app.config['RABBITMQ_PORT']))
            app.logger.info("Connected connect to rabbitmq!")
            return
        except pika.exceptions.ConnectionClosed:
            app.logger.error("Cannot connect to rabbitmq, sleeping 2 seconds")
            sleep(2)
            continue
