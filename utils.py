import os
from setup import spark, sc
from pyspark.sql import SQLContext


def load_listens_df(directory):

    sql_context = SQLContext(sc)
    listens_df = sql_context.read.format("parquet").load(os.path.join(directory, "listen.parquet"))
    return listens_df
