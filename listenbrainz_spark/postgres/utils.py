from pyspark.sql.functions import from_json

import listenbrainz_spark
from listenbrainz_spark import config
from listenbrainz_spark.schema import artists_column_schema


def load_from_db(url, user, password, query):
    return listenbrainz_spark\
        .session\
        .read\
        .format("jdbc")\
        .option("url", url)\
        .option("query", query)\
        .option("user", user)\
        .option("password", password)\
        .load()


def _save_db_table_to_hdfs(url, user, password, query, path, process_artists_column=False):
    df = load_from_db(url, user, password, query)

    # artists column is generated as jsonb aggregation in multiple queries importing data from postgres
    # before storing this data in parquet, we change the string into a proper schema, otherwise we will
    # need to an extra load json step in stats generation to avoid double encoding this column in final results
    if process_artists_column:
        df = df.withColumn('artists', from_json('artists', artists_column_schema))

    df\
        .write\
        .format('parquet')\
        .save(config.HDFS_CLUSTER_URI + path, mode="overwrite")


def save_pg_table_to_hdfs(query, path, process_artists_column=False):
    """ Load data from Postgres using the given SQL query and save the dataframe to given path in HDFS """
    _save_db_table_to_hdfs(config.PG_JDBC_URI, config.PG_USER, config.PG_PASSWORD, query, path, process_artists_column)


def save_ts_table_to_hdfs(query, path):
    """ Load data from Timescale using the given SQL query and save the dataframe to given path in HDFS """
    _save_db_table_to_hdfs(config.TS_JDBC_URI, config.TS_USER, config.TS_PASSWORD, query, path)


def save_lb_table_to_hdfs(query, path):
    """ Load data from Timescale using the given SQL query and save the dataframe to given path in HDFS """
    _save_db_table_to_hdfs(config.LB_JDBC_URI, config.LB_USER, config.LB_PASSWORD, query, path)
