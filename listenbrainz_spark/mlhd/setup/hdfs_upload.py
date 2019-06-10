import listenbrainz_spark.config as config
import os

from listenbrainz_spark import hdfs_connection
from listenbrainz_spark.mlhd import MLHD_DATA_PATH


def main(mlhd_dir):
    hdfs_connection.init_hdfs(config.HDFS_HTTP_URI)
    for mlhd_file in os.listdir(mlhd_dir):
        if mlhd_file.endswith('.avro'):
            print('Uploading ', mlhd_file)
            hdfs_connection.client.upload(hdfs_path=os.path.join(MLHD_DATA_PATH, mlhd_file), local_path=os.path.join(mlhd_dir, mlhd_file))
            print('Done')
