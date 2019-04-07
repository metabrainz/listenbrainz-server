import listenbrainz_spark
import os


from listenbrainz_spark import config
from listenbrainz_spark import hdfs_connection
from listenbrainz_spark.mlhd.schema import tsv_schema


def load_files():
    df = None
    root_path = '/data/mlhd'
    file_no = 1
    count = 0
    for path, dirs, files in hdfs_connection.client.walk(root_path):
        print('Here: ', path)
        listen_files = [filename for filename in files if filename.endswith('.txt')]
        for listen_file in listen_files:
            file_path = config.HDFS_CLUSTER_URI + os.path.join(path, listen_file)
            file_df = listenbrainz_spark.session.read.csv(file_path, sep='\t', schema=tsv_schema, timestampFormat='s')
            count += file_df.count()
            df = df.union(file_df) if df else file_df
            print(file_no, '\t', count)
            file_no += 1
    return df


def main():
    listenbrainz_spark.init_spark_session('mlhd_create_dataframe')
    hdfs_connection.init_hdfs(config.HDFS_HTTP_URI)
    dataframe = load_files()
    dataframe.write.format('parquet').save(config.HDFS_CLUSTER_URI + '/data/mlhd/entire_mlhd.parquet')
