from typing import Optional

from kombu import pools, producers, Exchange, Queue
from kombu.pools import ProducerPool

from listenbrainz.rabbitmq import create_rabbitmq_connection, get_incoming_exchange, get_incoming_queue

rabbitmq: Optional[ProducerPool] = None
INCOMING_EXCHANGE: Optional[Exchange] = None
INCOMING_QUEUE: Optional[Queue] = None
PLAYING_NOW_EXCHANGE: Optional[Exchange] = None

CONNECTION_RETRIES = 10
CONNECTION_LIMIT = 25


def init_rabbitmq_connection(app):
    """Initialize the webserver rabbitmq connection.

    This initializes ``rabbitmq`` as a connection pool from which new RabbitMQ
    producers can be acquired. ``confirm_publish`` is enabled on the connection so
    every publish waits for a broker acknowledgement; this lets ``publish_data_to_queue``
    retry/fail loudly instead of silently dropping listens. The incoming queue is no
    longer declared here at startup: producers declare it themselves on publish (see
    ``publish_data_to_queue``) so that every entry point writing listens (web, api_compat,
    spotify/lastfm importers, ...) guarantees the queue and its binding exist.
    """
    global rabbitmq, INCOMING_EXCHANGE, INCOMING_QUEUE, PLAYING_NOW_EXCHANGE

    if rabbitmq is not None:
        return

    # if RabbitMQ config values are not in the config file
    # raise an error. This is caught in create_app, so the app will continue running.
    # Consul will bring the values back into config once the RabbitMQ service comes up.
    if not app.config.get("RABBITMQ_HOSTS"):
        app.logger.critical("RabbitMQ hosts not defined, cannot create RabbitMQ connection...")
        raise ConnectionError("RabbitMQ service is not up!")

    connection = create_rabbitmq_connection(
        app.config,
        transport_options={"confirm_publish": True},
    ).ensure_connection(max_retries=CONNECTION_RETRIES)
    pools.set_limit(CONNECTION_LIMIT)

    INCOMING_EXCHANGE = get_incoming_exchange(app.config)
    INCOMING_QUEUE = get_incoming_queue(app.config)
    PLAYING_NOW_EXCHANGE = Exchange(app.config["PLAYING_NOW_EXCHANGE"], "fanout", durable=True)
    rabbitmq = producers[connection]
