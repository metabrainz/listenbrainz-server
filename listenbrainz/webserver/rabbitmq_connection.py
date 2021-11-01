from listenbrainz.utils import get_fallback_connection_name
from kombu import Connection


_rabbitmq = None
CONNECTION_RETRIES = 10
TIME_BEFORE_RETRIES = 2

def init_rabbitmq_connection(app):
    """Initialize the webserver rabbitmq connection.

    This initializes _rabbitmq as a connection pool from which new RabbitMQ
    connections can be acquired.
    """
    global _rabbitmq

    if _rabbitmq is not None:
        return

    # if RabbitMQ config values are not in the config file
    # raise an error. This is caught in create_app, so the app will continue running.
    # Consul will bring the values back into config once the RabbitMQ service comes up.
    if "RABBITMQ_HOST" not in app.config:
        app.logger.critical("RabbitMQ host:port not defined, cannot create RabbitMQ connection...")
        raise ConnectionError("RabbitMQ service is not up!")

    _rabbitmq = Connection(
        hostname=app.config["RABBITMQ_HOST"],
        userid=app.config["RABBITMQ_USERNAME"],
        port=app.config["RABBITMQ_PORT"],
        password=app.config["RABBITMQ_PASSWORD"],
        virtual_host=app.config["RABBITMQ_VHOST"],
        client_properties={"connection_name": get_fallback_connection_name()}
    )
