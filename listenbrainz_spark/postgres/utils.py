import listenbrainz_spark
from listenbrainz_spark import config


def save_pg_table_to_hdfs(query, path):
    """ Load data from Postgres using the given SQL query and save the dataframe to given path in HDFS """
    listenbrainz_spark\
        .sql_context\
        .read\
        .format("jdbc")\
        .option("url", config.PG_JDBC_URI)\
        .option("query", query)\
        .option("user", config.PG_USER)\
        .option("password", config.PG_PASSWORD)\
        .load()\
        .write\
        .format('parquet')\
        .save(config.HDFS_CLUSTER_URI + path, mode="overwrite")
