import listenbrainz_spark
from listenbrainz_spark import hdfs_connection
from listenbrainz_spark import config
from listenbrainz_spark.mlhd.schema import tsv_schema


def load_files():
    df = None
    root_path = '/data/mlhd'
    for path, dirs, files in hdfs_connection.client.walk(root_path):
        print('Here: ', path)
        listen_files = [filename for filename in files if filename.endswith('.txt')]
        for listen_file in listen_files:
            print('listen file: %s' % listen_file)
            file_path = config.HDFS_CLUSTER_URI + os.path.join(root_path, path, listen_file)
            file_df = listenbrainz_spark.read.csv(file_path, sep='\t', schema=tsv_schema)
            df = df.union(file_df) if df else file_df
    print(df.count())
    df.show()
    return df


def main(app_name):
    listenbrainz_spark.init_spark_session(app_name)
    hdfs_connection.init_hdfs(config.HDFS_HTTP_URI)
    dataframe = load_files()
    dataframe.write.format('parquet').save(config.HDFS_CLUSTER_URI + '/data/mlhd/entire_mlhd.parquet')
