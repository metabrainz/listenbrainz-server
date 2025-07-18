import errno
import os
import socket
from datetime import datetime, timezone


def create_path(path):
    """Creates a directory structure if it doesn't exist yet."""
    try:
        os.makedirs(path)
    except OSError as exception:
        if exception.errno != errno.EEXIST:
            raise Exception("Failed to create directory structure %s. Error: %s" %
                            (path, exception))


def init_cache(host, port, namespace):
    """ Initializes brainzutils cache. """
    from brainzutils import cache
    cache.init(host=host, port=port, namespace=namespace)


def create_channel_to_consume(connection, exchange: str, queue: str, callback_function, auto_ack: bool = False):
    """ Returns a newly created channel that can consume from the specified queue.

    Args:
        connection: a RabbitMQ connection
        exchange: the name of the exchange
        queue: the name of the queue
        callback_function: the callback function to be called on message reception
        auto_ack: should messages be automatically ack'ed when received

    Returns:
        a RabbitMQ channel
    """
    ch = connection.channel()
    ch.exchange_declare(exchange=exchange, exchange_type='fanout')
    ch.queue_declare(queue, durable=True)
    ch.queue_bind(exchange=exchange, queue=queue)
    ch.basic_qos(prefetch_count=1)
    ch.basic_consume(queue=queue, on_message_callback=callback_function, auto_ack=auto_ack)
    return ch


def get_fallback_connection_name():
    """ Get a connection name friendlier than docker gateway ip during connecting
    to services like redis, rabbitmq etc."""
    # We use CONTAINER_NAME environment variable, this is always set in production.
    # Finally, we fall back to the host name, not as informative as the container name
    # but something is better than nothing.
    client_name = os.getenv("CONTAINER_NAME", None)
    if client_name is None:
        client_name = socket.gethostname()
    return client_name
