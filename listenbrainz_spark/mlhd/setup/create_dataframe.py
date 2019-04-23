import listenbrainz_spark
import os


from listenbrainz_spark import config
from listenbrainz_spark import hdfs_connection
from listenbrainz_spark.mlhd.schema import tsv_schema


def load_files(root_path):
    df = listenbrainz_spark.sql_context.read.format('avro').load(config.HDFS_CLUSTER_URI+root_path+'/*.avro')
    df.show()
    return df


def main():
    listenbrainz_spark.init_spark_session('mlhd_create_dataframe')
    hdfs_connection.init_hdfs(config.HDFS_HTTP_URI)
    print("Creating dataframe...")
    dataframe = load_files('/data/mlhd')
    print("Dataframe created!")
    print("Saving dataframe...")
    dataframe.write.format('parquet').save(config.HDFS_CLUSTER_URI + '/data/mlhd/entire_mlhd.parquet')
    print("Saved!")
