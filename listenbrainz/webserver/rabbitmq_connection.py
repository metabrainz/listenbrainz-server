import queue
from time import sleep
import pika
from listenbrainz.utils import get_fallback_connection_name
from flask import current_app

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

    connection_parameters = pika.ConnectionParameters(
        host=app.config['RABBITMQ_HOST'],
        port=app.config['RABBITMQ_PORT'],
        virtual_host=app.config['RABBITMQ_VHOST'],
        credentials=pika.PlainCredentials(app.config['RABBITMQ_USERNAME'], app.config['RABBITMQ_PASSWORD']),
        client_properties={"connection_name": get_fallback_connection_name()}
    )

    _rabbitmq = RabbitMQConnectionPool(
            app.logger,
            connection_parameters,
            app.config['MAXIMUM_RABBITMQ_CONNECTIONS'],
            app.config['INCOMING_EXCHANGE'],
        )


class RabbitMQConnectionPool:
    """ The RabbitMQ connection pool used by the api and api_compat to publish messages to
    the incoming queue."""
    def __init__(self, logger, connection_parameters, max_size, exchange):
        self.log = logger
        self.connection_parameters = connection_parameters
        self.max_size = max_size
        self.queue = queue.Queue(maxsize=max_size)
        self.exchange = exchange

    def add(self):
        try:
            self.queue.put_nowait(self.create())
        except queue.Full:
            self.log.error('Tried to add a new connection into a full queue...', exc_info=True)

    def get(self):
        while True:
            try:
                connection = self.queue.get_nowait()
                if connection.is_open:
                    return connection
            except queue.Empty:
                self.add()

    def release(self, connection):
        try:
            # If we're running in the dev server, close connections since threads exit after the request
            if current_app.debug:
                connection.close()
                return

            if connection.is_open:
                self.queue.put_nowait(connection)
        except queue.Full:
            self.log.error('Tried to put a connection into a full queue...', exc_info=True)
            connection.close()

    def create(self):
        for attempt in range(CONNECTION_RETRIES):
            try:
                connection = pika.BlockingConnection(self.connection_parameters)
                return RabbitMQConnection(connection, self)
            except (pika.exceptions.ConnectionClosed, pika.exceptions.ChannelClosed) as e:
                sleep(TIME_BEFORE_RETRIES)
                if attempt == CONNECTION_RETRIES - 1: # if this is the last attempt
                    self.log.critical('Unable to create a RabbitMQ connection: %s', str(e), exc_info=True)
                    raise


class RabbitMQConnection:
    def __init__(self, connection, pool):
        self.connection = connection
        self.channel = connection.channel()
        self.pool = pool

    def __enter__(self):
        if not self.is_channel_open:
            self.recreate_channel()
        return self

    def __exit__(self, type, value, traceback):
        self.pool.release(self)

    @property
    def is_channel_open(self):
        """ Checks if current channel is open or not.

        Note: We cannot use channel.is_open because this is a BlockingChannel where the is_open
        property is not trustworthy (https://github.com/pika/pika/issues/877)

        So we check if an exchange exists each time, to check if the channel is ok. This exchange
        is the exchange which houses incoming listens.

        Returns:
            bool: True if channel is open, False otherwise
        """
        try:
            self.channel.exchange_declare(exchange=self.pool.exchange, exchange_type='fanout', passive=True)
            return True
        except (pika.exceptions.ConnectionClosed, pika.exceptions.ChannelClosed, FileNotFoundError, OSError) as e:
            return False

    @property
    def is_open(self):
        """ Checks if current connection is open or not.

        Note: We're using process_data_events here instead of the is_open property because of
        https://github.com/pika/pika/issues/877
        """
        try:
            self.connection.process_data_events()
            return True
        except (pika.exceptions.ConnectionClosed, FileNotFoundError, OSError) as e:
            return False

    def recreate_channel(self):
        self.channel = self.connection.channel()

    def close(self):
        if self.connection.is_open:
            self.connection.close()
