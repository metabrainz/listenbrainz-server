import logging

_handler = logging.StreamHandler()
_handler.setLevel(logging.DEBUG)
_formatter = logging.Formatter("%(asctime)s %(name)-20s %(levelname)-8s %(message)s")
_handler.setFormatter(_formatter)

_logger = logging.getLogger("listenbrainz_spark")
_logger.setLevel(logging.DEBUG)
_logger.addHandler(_handler)

logging.getLogger("pika").setLevel(logging.DEBUG)

import sentry_sdk

from py4j.protocol import Py4JJavaError
from pyspark.sql import SparkSession, SQLContext

from listenbrainz_spark.exceptions import SparkSessionNotInitializedException
from listenbrainz_spark import config

session = None
context = None
sql_context = None


def init_spark_session(app_name):
    """ Initializes a Spark Session with the given application name.

        Args:
            app_name (str): Name of the Spark application. This will also occur in the Spark UI.
    """
    if hasattr(config, 'LOG_SENTRY'):  # attempt to initialize sentry_sdk only if configuration available
        sentry_sdk.init(**config.LOG_SENTRY)
    global session, context, sql_context
    try:
        session = SparkSession \
                .builder \
                .appName(app_name) \
                .getOrCreate()
        context = session.sparkContext
        context.setLogLevel("ERROR")
        sql_context = SQLContext(context)
    except Py4JJavaError as err:
        raise SparkSessionNotInitializedException(app_name, err.java_exception)


def init_test_session(app_name):
    """Create a spark session suitable for running tests.
    This sets some config items in order to make tests faster,
    the list of settings is taken from
    https://github.com/malexer/pytest-spark#overriding-default-parameters-of-the-spark_session-fixture
    """
    global session, context, sql_context
    try:
        session = SparkSession \
                .builder \
                .master('local') \
                .appName(app_name) \
                .config("spark.sql.shuffle.partitions", "1") \
                .config("spark.default.parallelism", "1") \
                .config("spark.executor.cores", "1") \
                .config("spark.executor.instances", "1") \
                .config("spark.shuffle.compress", "false") \
                .config("spark.rdd.compress", "false") \
                .config("spark.dynamicAllocation.enabled", "false") \
                .config("spark.io.compression.codec", "lz4") \
                .getOrCreate()
        context = session.sparkContext
        context.setLogLevel("ERROR")
        sql_context = SQLContext(context)
    except Py4JJavaError as err:
        raise SparkSessionNotInitializedException(app_name, err.java_exception)
