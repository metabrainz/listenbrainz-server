from pyspark import SparkContext
from pyspark.sql import SparkSession

spark = SparkSession \
        .builder \
        .appName("LB Spark Cluster") \
        .config("spark.hadoop.dfs.client.use.datanode.hostname", "true") \
        .getOrCreate()

sc = spark.sparkContext
