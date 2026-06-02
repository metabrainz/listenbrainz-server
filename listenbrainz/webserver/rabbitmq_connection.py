from typing import Optional

from kombu import pools, producers, Exchange
from kombu.pools import ProducerPool

from listenbrainz.rabbitmq import create_rabbitmq_connection, get_incoming_exchange, get_incoming_queue

rabbitmq: Optional[ProducerPool] = None
INCOMING_EXCHANGE: Optional[Exchange] = None
PLAYING_NOW_EXCHANGE: Optional[Exchange] = None
incoming_queue_declared = False

CONNECTION_RETRIES = 10
CONNECTION_LIMIT = 25


def _declare_incoming_queue(app, channel):
    global incoming_queue_declared

    if incoming_queue_declared:
        return

    get_incoming_queue(app.config).declare(channel=channel)
    incoming_queue_declared = True


def init_rabbitmq_connection(app, declare_incoming_queue=False):
    """Initialize the webserver rabbitmq connection.

    This initializes _rabbitmq as a connection pool from which new RabbitMQ
    connections can be acquired.
    """
    global rabbitmq, INCOMING_EXCHANGE, PLAYING_NOW_EXCHANGE

    if rabbitmq is not None:
        if declare_incoming_queue:
            with rabbitmq.acquire(block=True, timeout=60) as producer:
                _declare_incoming_queue(app, producer.channel)
        return

    # if RabbitMQ config values are not in the config file
    # raise an error. This is caught in create_app, so the app will continue running.
    # Consul will bring the values back into config once the RabbitMQ service comes up.
    if not app.config.get("RABBITMQ_HOSTS"):
        app.logger.critical("RabbitMQ hosts not defined, cannot create RabbitMQ connection...")
        raise ConnectionError("RabbitMQ service is not up!")

    connection = create_rabbitmq_connection(app.config).ensure_connection(max_retries=CONNECTION_RETRIES)
    pools.set_limit(CONNECTION_LIMIT)

    INCOMING_EXCHANGE = get_incoming_exchange(app.config)
    PLAYING_NOW_EXCHANGE = Exchange(app.config["PLAYING_NOW_EXCHANGE"], "fanout", durable=True)
    if declare_incoming_queue:
        _declare_incoming_queue(app, connection.channel())
    rabbitmq = producers[connection]
