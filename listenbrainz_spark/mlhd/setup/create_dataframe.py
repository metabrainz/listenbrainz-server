import listenbrainz_spark
import os


from listenbrainz_spark import config
from listenbrainz_spark import hdfs_connection
from listenbrainz_spark.mlhd.schema import tsv_schema


def load_files(root_path):
    df = None
    for path in hdfs_connection.client.list(root_path):
        files_path = config.HDFS_CLUSTER_URI + os.path.join(root_path, path, '*.txt')
        print('New files: ', files_path)
        files_df = listenbrainz_spark.session.read.csv(files_path, sep='\t', schema=tsv_schema, timestampFormat='s')
        files_df.show()
        df = df.union(files_df) if df else files_df
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
