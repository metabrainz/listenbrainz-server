from urllib.parse import quote

from kombu import Connection

from listenbrainz.utils import get_fallback_connection_name


def _get_config_value(config, key, default=None):
    return config.get(key, default)


def _rabbitmq_url(host, port, config):
    username = quote(str(_get_config_value(config, "RABBITMQ_USERNAME", "")), safe="")
    password = quote(str(_get_config_value(config, "RABBITMQ_PASSWORD", "")), safe="")
    vhost = quote(str(_get_config_value(config, "RABBITMQ_VHOST", "/")), safe="")
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
