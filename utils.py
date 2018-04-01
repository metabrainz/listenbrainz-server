import os
from setup import spark, sc
from pyspark.sql import SQLContext

def load_df(directory, df):
    sql_context = SQLContext(sc)
    return sql_context.read.format('parquet').load(os.path.join(directory, '%s.parquet' % df))

def load_listens_df(directory):
    return load_df(directory, 'listen')

def load_playcounts_df(directory):
    return load_df(directory, 'playcount')

def load_users_df(directory):
    return load_df(directory, 'user')

def load_recordings_df(directory):
    return load_df(directory, 'recording')
