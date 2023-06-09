import listenbrainz_spark
from listenbrainz_spark import config


def _save_db_table_to_hdfs(url, user, password, query, path):
    listenbrainz_spark\
        .sql_context\
        .read\
        .format("jdbc")\
        .option("url", url)\
        .option("query", query)\
        .option("user", user)\
        .option("password", password)\
        .load()\
        .write\
        .format('parquet')\
        .save(config.HDFS_CLUSTER_URI + path, mode="overwrite")


def save_pg_table_to_hdfs(query, path):
    """ Load data from Postgres using the given SQL query and save the dataframe to given path in HDFS """
    _save_db_table_to_hdfs(config.PG_JDBC_URI, config.PG_USER, config.PG_PASSWORD, query, path)


def save_ts_table_to_hdfs(query, path):
    """ Load data from Timescale using the given SQL query and save the dataframe to given path in HDFS """
    _save_db_table_to_hdfs(config.TS_JDBC_URI, config.TS_USER, config.TS_PASSWORD, query, path)


def save_lb_table_to_hdfs(query, path):
    """ Load data from Timescale using the given SQL query and save the dataframe to given path in HDFS """
    _save_db_table_to_hdfs(config.LB_JDBC_URI, config.LB_USER, config.LB_PASSWORD, query, path)
