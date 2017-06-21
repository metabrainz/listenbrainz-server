import sys
from time import sleep
from flask import Flask
from flask.ext.pika import Pika as FPika

_rabbitmq = None

def init_rabbitmq_connection(app):
    """Create a connection to the RabbitMQ server."""
    global _rabbitmq

    if "RABBITMQ_HOST" not in app.config:
        app.logger.error("RabbitMQ host:port not defined. Sleeping 2 seconds, and exiting.")
        sleep(2)
        sys.exit(-1)

    FLASK_PIKA_PARAMS = {
        'host':app.config['RABBITMQ_HOST'],
        'port': app.config['RABBITMQ_PORT'],
        'username': 'guest',
        'password': 'guest',
    }

    FLASK_PIKA_POOL_PARAMS = {
        'pool_size': 100,
        'pool_recycle': 600
    }

    app.config['FLASK_PIKA_PARAMS'] = FLASK_PIKA_PARAMS
    app.config['FLASK_PIKA_POOL_PARAMS'] = FLASK_PIKA_POOL_PARAMS

    while True:
        try:
            _rabbitmq = FPika(app)
            return
        except Exception as err:
            app.logger.error("Cannot connect to rabbitmq, sleeping 2 seconds")
            sleep(2)
            continue
