from py4j.protocol import Py4JJavaError

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
        raise Py4JJavaError('Cannot initialize Spark session "{}": {}\n'.format(app_name, type(err).__name__),
            err.java_exception)
