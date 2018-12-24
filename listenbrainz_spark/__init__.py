from pyspark import SparkContext
from pyspark.sql import SparkSession

spark = SparkSession \
        .builder \
        .appName("LB Spark Cluster") \
        .config("spark.hadoop.dfs.client.use.datanode.hostname", "true") \
        .config("spark.driver.memory", "20g") \
        .config("spark.executor.memory", "20g") \
        .getOrCreate()

sc = spark.sparkContext
