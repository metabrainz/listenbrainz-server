from kombu import Connection, Exchange, Queue

from listenbrainz.utils import get_fallback_connection_name

QUORUM_QUEUE_ARGUMENTS = {"x-queue-type": "quorum"}


def get_incoming_exchange(config):
    return Exchange(config["INCOMING_EXCHANGE"], "fanout", durable=True)


def get_incoming_queue(config):
    return Queue(
        config["INCOMING_QUEUE"],
        exchange=get_incoming_exchange(config),
        durable=True,
        queue_arguments=QUORUM_QUEUE_ARGUMENTS,
    )


def _get_config_value(config, key, default=None):
    return config.get(key, default)


def _rabbitmq_url(host, port, config):
    username = _get_config_value(config, "RABBITMQ_USERNAME", "")
    password = _get_config_value(config, "RABBITMQ_PASSWORD", "")
    vhost = _get_config_value(config, "RABBITMQ_VHOST", "/")
    return f"amqp://{username}:{password}@{host}:{port}/{vhost}"


def get_rabbitmq_urls(config):
    """Return one or more RabbitMQ broker URLs from RABBITMQ_HOSTS."""
    hosts = _get_config_value(config, "RABBITMQ_HOSTS")
    if not hosts:
        raise ConnectionError("RabbitMQ hosts not defined, cannot create RabbitMQ connection...")

    return [_rabbitmq_url(host, port, config) for host, port in hosts]


def create_rabbitmq_connection(config, connection_name=None, **kwargs):
    transport_options = kwargs.pop("transport_options", {})
    client_properties = transport_options.setdefault("client_properties", {})
    client_properties.setdefault("connection_name", connection_name or get_fallback_connection_name())

    return Connection(
        hostname=get_rabbitmq_urls(config),
        transport_options=transport_options,
        **kwargs,
    )
