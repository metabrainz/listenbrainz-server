from pyspark import SparkContext
from pyspark.sql import SparkSession

spark = SparkSession \
        .builder \
        .appName("LB recommender") \
        .getOrCreate()

sc = spark.sparkContext
