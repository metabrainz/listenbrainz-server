import queue
from time import sleep
import pika
import listenbrainz.utils as utils

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
    )

    _rabbitmq = RabbitMQConnectionPool(app.logger, connection_parameters, app.config['MAXIMUM_RABBITMQ_CONNECTIONS'])
    _rabbitmq.add()
    app.logger.info('Connection to RabbitMQ established!')


class RabbitMQConnectionPool:
    def __init__(self, logger, connection_parameters, max_size):
        self.log = logger
        self.connection_parameters = connection_parameters
        self.max_size = max_size
        self.queue = queue.Queue(maxsize=max_size)

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
            if connection.is_open:
                self.queue.put_nowait(connection)
        except queue.Full:
            self.log.error('Tried to put a connection into a full queue...', exc_info=True)
            connection.close()

    def create(self):
        for attempt in range(CONNECTION_RETRIES):
            try:
                connection = pika.BlockingConnection(self.connection_parameters)
                channel = connection.channel()
                return RabbitMQConnection(connection, channel, self)
            except (pika.exceptions.ConnectionClosed, pika.exceptions.ChannelClosed) as e:
                sleep(TIME_BEFORE_RETRIES)
                if attempt == CONNECTION_RETRIES - 1: # if this is the last attempt
                    self.log.critical('Unable to create a RabbitMQ connection: %s', str(e), exc_info=True)
                    raise


class RabbitMQConnection:
    def __init__(self, connection, channel, pool):
        self.connection = connection
        self.channel = channel
        self.pool = pool

    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        self.pool.release(self)

    @property
    def is_open(self):
        try:
            self.connection.process_data_events()
            return True
        except (pika.exceptions.ConnectionClosed, FileNotFoundError, OSError) as e:
            return False

    def close(self):
        if self.connection.is_open:
            self.connection.close()
