import errno
import os
import pika
import pytz
import time

from datetime import datetime
from redis import Redis

INFLUX_TIME_FORMAT = "%Y-%m-%dT%H:%M:%SZ"
INFLUX_TIME_FORMAT_NANO = "%Y-%m-%dT%H:%M:%S"

def escape(value):
    """ Escapes backslashes, quotes and new lines present in the string value
    """
    return value.replace("\\", "\\\\").replace("\"", "\\\"").replace("\n", "\\n")


def quote(user_name):
    # we have to always quote the user name to get the measurement name which we pass to
    # influx write_points and replace the new line characters with \n because parse
    # errors are thrown if we don't.
    return "\"{0}\"".format(user_name.replace("\n", "\\n"))


def get_measurement_name(user_name):
    """ Function to return the measurement name that influx has saved for given user name"""

    # Note: there are we have to replace each \ with two backslashes because influxdb-python
    # adds an extra backslash for each backslash in the measurement name itself
    return '"{}"'.format(user_name.replace('\\', '\\\\').replace('\n', '\\\\n'))


def get_escaped_measurement_name(user_name):
    """ Function to return the string which can directly be passed into influx queries for a
        user's measurement
    """

    # Note: influxdb-python first replaces each backslash in the username with two backslashes
    # and because in influx queries, we have to escape each backslash, overall each backslash
    # must be replaced by 4 backslashes. Yes, this is hacky and ugly.
    return '"\\"{}\\""'.format(user_name.replace('\\', '\\\\\\\\').replace('"', '\\"').replace('\n', '\\\\\\\\n'))


def get_influx_query_timestamp(ts):
    """ Influx queries require timestamps in nanoseconds so convert ts into nanoseconds and return a string"""
    return "{}000000000".format(ts)


def convert_to_unix_timestamp(influx_row_time):
    """ Converts time retreived from influxdb into unix timestamp """
    dt = datetime.strptime(influx_row_time, INFLUX_TIME_FORMAT)
    return int(dt.strftime('%s'))

def convert_influx_to_datetime(influx_row_time):
    return datetime.strptime(influx_row_time, INFLUX_TIME_FORMAT)


def convert_timestamp_to_influx_row_format(ts):
    return datetime.fromtimestamp(ts).strftime(INFLUX_TIME_FORMAT)


def convert_influx_nano_to_python_time(influx_row_time):
    """ Converts time retreived from influxdb into python floating point time """
    date_bits = influx_row_time.split(".")
    dt = datetime.strptime(date_bits[0], INFLUX_TIME_FORMAT_NANO)
    fractional = int(date_bits[1][:-1])
    return float(dt.strftime('%s')) + (fractional / 100000000.0)


def convert_python_time_to_nano_int(t):
    return int(t * 100000000)


def create_path(path):
    """Creates a directory structure if it doesn't exist yet."""
    try:
        os.makedirs(path)
    except OSError as exception:
        if exception.errno != errno.EEXIST:
            raise Exception("Failed to create directory structure %s. Error: %s" %
                            (path, exception))


def log_ioerrors(logger, e):
    """ Logs IOErrors that occur in case we run out of disk space.
        This is used in data dumps and is a placeholder while Sentry support
        is added.
    """
    logger.error('IOError while creating dump: %s', str(e))


def connect_to_rabbitmq(username, password,
                        host, port, virtual_host,
                        connection_type=pika.BlockingConnection,
                        credentials_type=pika.PlainCredentials,
                        error_logger=print,
                        error_retry_delay=3,
                        heartbeat=None):
    """Connects to RabbitMQ

    Args:
        username, password, host, port, virtual_host
        error_logger: A function used to log failed connections.
        connection_type: A pika Connection class to instantiate.
        credentials_type: A pika Credentials class to use.
        error_retry_delay: How long to wait in seconds before retrying a connection.

    Returns:
        A connection, with type of connection_type.
    """
    while True:
        try:
            credentials = credentials_type(username, password)
            connection_parameters = pika.ConnectionParameters(
                host=host,
                port=port,
                virtual_host=virtual_host,
                credentials=credentials,
                heartbeat=heartbeat,
            )
            return connection_type(connection_parameters)
        except Exception as err:
            error_message = "Cannot connect to RabbitMQ: {error}, retrying in {delay} seconds."
            error_logger(error_message.format(error=str(err), delay=error_retry_delay))
            time.sleep(error_retry_delay)


def init_cache(host, port, namespace):
    """ Initializes brainzutils cache. """
    from brainzutils import cache
    cache.init(host=host, port=port, namespace=namespace)


def create_channel_to_consume(connection, exchange, queue, callback_function, no_ack=False):
    """ Returns a newly created channel that can consume from the specified queue.

    Args:
        connection: a RabbitMQ connection
        exchange (str): the name of the exchange
        queue (str): the name of the queue
        callback_function: the callback function to be called on message reception

    Returns:
        a RabbitMQ channel
    """
    ch = connection.channel()
    ch.exchange_declare(exchange=exchange, exchange_type='fanout')
    ch.queue_declare(queue, durable=True)
    ch.queue_bind(exchange=exchange, queue=queue)
    ch.basic_consume(callback_function, queue=queue, no_ack=no_ack)
    return ch


def connect_to_redis(host, port, log=print):
    """ Create a connection to redis and return it

    Note: This is a blocking function which keeps trying to connect to redis until
    it establishes a connection

    Args:
        host: the hostname of the redis server
        port: the port of the redis server
        log: the function to use for error logging

    Returns:
        Redis object
    """
    while True:
        try:
            redis = Redis(host=host, port=port)
            redis.ping()
            return redis
        except Exception as err:
            log("Cannot connect to redis: %s. Retrying in 3 seconds and trying again." % str(err))
            time.sleep(3)

def safely_import_config():
    """ 
        Safely import config.py. If config.py is not found, wait 2 seconds and try again.
    """

    while True:
        try:
            from listenbrainz import config
            break
        except ImportError:
            print("Cannot import config.py. Waiting and retrying...")
            time.sleep(2)


def unix_timestamp_to_datetime(timestamp):
    """ Converts expires_at timestamp received from Spotify to a datetime object

    Args:
        timestamp (int): the unix timestamp to be converted to datetime

    Returns:
        A datetime object with timezone UTC corresponding to the provided timestamp
    """
    return datetime.utcfromtimestamp(timestamp).replace(tzinfo=pytz.UTC)


