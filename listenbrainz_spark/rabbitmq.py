from kombu import Connection


def _rabbitmq_url(host, port, config):
    username = config.RABBITMQ_USERNAME
    password = config.RABBITMQ_PASSWORD
    vhost = config.RABBITMQ_VHOST
    return f"amqp://{username}:{password}@{host}:{port}/{vhost}"


def get_rabbitmq_urls(config):
    hosts = getattr(config, "RABBITMQ_HOSTS", None)
    if not hosts:
        raise ConnectionError("RabbitMQ hosts not defined, cannot create RabbitMQ connection...")

    return [_rabbitmq_url(host, port, config) for host, port in hosts]


def create_rabbitmq_connection(config, connection_name, **kwargs):
    transport_options = kwargs.pop("transport_options", {})
    client_properties = transport_options.setdefault("client_properties", {})
    client_properties.setdefault("connection_name", connection_name)

    return Connection(
        hostname=get_rabbitmq_urls(config),
        transport_options=transport_options,
        **kwargs,
    )
