import logging

from pyspark import SparkContext
from pyspark.sql import SparkSession, SQLContext


session = None
context = None
sql_context = None

def init_spark_session(app_name):
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
    except AttributeError as err:
        raise AttributeError('Cannot initialize Spark session "{}": {} \n {}.'.format(app_name, type(err).__name__,
            str(err)))
    except Exception as err:
        raise Exception('An error occurred while initializing Spark session "{}": {} \n {}.'.format(app_name,
            type(err).__name__, str(err)))
