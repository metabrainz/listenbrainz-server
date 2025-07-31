import logging

_handler = logging.StreamHandler()
_handler.setLevel(logging.INFO)
_formatter = logging.Formatter("%(asctime)s %(name)-20s %(levelname)-8s %(message)s")
_handler.setFormatter(_formatter)

_logger = logging.getLogger(__name__)
_logger.setLevel(logging.INFO)
_logger.addHandler(_handler)

import sentry_sdk

from py4j.protocol import Py4JJavaError
from pyspark.sql import SparkSession

from listenbrainz_spark.exceptions import SparkSessionNotInitializedException
from listenbrainz_spark import config

session = None
context = None


def init_spark_session(app_name):
    """ Initializes a Spark Session with the given application name.

        Args:
            app_name (str): Name of the Spark application. This will also occur in the Spark UI.
    """
    if hasattr(config, "LOG_SENTRY"):  # attempt to initialize sentry_sdk only if configuration available
        sentry_sdk.init(**config.LOG_SENTRY)
    global session, context
    try:
        # readSideCharPadding enabled causes OOM when importing artist_country_code cache data
        session = SparkSession \
                .builder \
                .appName(app_name) \
                .config("spark.sql.readSideCharPadding", "false") \
                .getOrCreate()
        context = session.sparkContext
        context.setLogLevel("ERROR")
    except Py4JJavaError as err:
        raise SparkSessionNotInitializedException(app_name, err.java_exception)


def init_test_session(app_name):
    """Create a spark session suitable for running tests.
    This sets some config items in order to make tests faster,
    the list of settings is taken from
    https://github.com/malexer/pytest-spark#overriding-default-parameters-of-the-spark_session-fixture
    Set spark.driver.host to avoid tests from hanging (get_listens_from_dump hangs when taking union
    of full dump and incremental dump listens), see https://issues.apache.org/jira/browse/SPARK-16087
    """
    global session, context
    try:
        session = SparkSession \
                .builder \
                .master("local") \
                .appName(app_name) \
                .config("spark.sql.shuffle.partitions", "1") \
                .config("spark.default.parallelism", "1") \
                .config("spark.executor.cores", "1") \
                .config("spark.executor.instances", "1") \
                .config("spark.shuffle.compress", "false") \
                .config("spark.rdd.compress", "false") \
                .config("spark.dynamicAllocation.enabled", "false") \
                .config("spark.io.compression.codec", "lz4") \
                .config("spark.driver.host", "localhost") \
                .getOrCreate()
        context = session.sparkContext
        context.setLogLevel("ERROR")
    except Py4JJavaError as err:
        raise SparkSessionNotInitializedException(app_name, err.java_exception)
