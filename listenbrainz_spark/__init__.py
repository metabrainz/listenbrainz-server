from py4j.protocol import Py4JJavaError

from listenbrainz_spark.exceptions import SparkSessionNotInitializedException

from pyspark import SparkContext
from pyspark.sql import SparkSession, SQLContext

session = None
context = None
sql_context = None

def init_spark_session(app_name):
    """ Initializes a Spark Session with the given application name.

        Args:
            app_name (str): Name of the Spark application. This will also occur in the Spark UI.
    """
    global session, context, sql_context
    try:
        session = SparkSession \
                .builder \
                .appName(app_name) \
                .config("spark.hadoop.dfs.client.use.datanode.hostname", "true") \
                .config("spark.hadoop.dfs.datanode.use.datanode.hostname", "true") \
                .getOrCreate()
        context = session.sparkContext
        context.setLogLevel("ERROR")
        sql_context = SQLContext(context)
    except Py4JJavaError as err:
        raise SparkSessionNotInitializedException(app_name, err.java_exception)


def init_test_session(app_name):
    global session, context, sql_context
    try:
        session = SparkSession \
                .builder \
                .master('local') \
                .appName(app_name) \
                .config("spark.hadoop.dfs.client.use.datanode.hostname", "true") \
                .config("spark.hadoop.dfs.datanode.use.datanode.hostname", "true") \
                .getOrCreate()
        context = session.sparkContext
        context.setLogLevel("ERROR")
        sql_context = SQLContext(context)
    except Py4JJavaError as err:
        raise SparkSessionNotInitializedException(app_name, err.java_exception)
