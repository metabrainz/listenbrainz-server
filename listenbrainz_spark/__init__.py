from pyspark import SparkContext
from pyspark.sql import SparkSession, SQLContext


session = None
context = None
sql_context = None

def init_spark_session(app_name):
    global session, context, sql_context
    session = SparkSession \
            .builder \
            .appName(app_name) \
            .config("spark.hadoop.dfs.client.use.datanode.hostname", "true") \
            .config("spark.hadoop.dfs.datanode.use.datanode.hostname", "true") \
            .config("spark.jars.packages", "org.apache.spark:spark-avro_2.12:2.4.1") \
            .getOrCreate()
    context = session.sparkContext
    context.setLogLevel("ERROR")
    sql_context = SQLContext(context)
