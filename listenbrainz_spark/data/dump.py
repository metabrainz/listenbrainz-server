import json
import os
import subprocess
import tarfile
import tempfile
import hdfs

import listenbrainz_spark.config as config

from datetime import datetime
from hdfs.util import HdfsError
from listenbrainz_spark import spark, sc, hdfs_connection
from listenbrainz_spark.constants import LAST_FM_FOUNDING_YEAR
from listenbrainz_spark.schema import convert_listen_to_row, listen_schema
from pyspark.sql.functions import year

FORCE = True

def _is_listens_file(filename):
    """ Check if passed filename is a file which contains listens

    Args:
        filename (str): the name of the file

    Returns:
        bool: True if the file contains listens, False otherwise
    """
    return filename.endswith('.listens')


def copy_to_hdfs(archive, threads=4):
    """ Create Spark Dataframes from a listens dump and save it to HDFS.

    Args:
        archive (str): the path to the listens dump
        threads (int): the number of threads to use for decompression of the archive
    """
    pxz_command = ['pxz', '--decompress', '--stdout', archive, '-T{}'.format(threads)]
    pxz = subprocess.Popen(pxz_command, stdout=subprocess.PIPE)
    destination_path = os.path.join('/', 'data', 'listenbrainz')
    if FORCE:
        print('Removing data directory if present...')
        hdfs_connection.client.delete(destination_path, recursive=True)
        print('Done!')

    print('Creating Listens RDD...')
    listens_rdd = sc.parallelize([])
    with tarfile.open(fileobj=pxz.stdout, mode='r|') as tar:
        for member in tar:
            if member.isfile() and _is_listens_file(member.name):
                print('Loading %s...' % member.name)
                tar.extract(member)
                listens_rdd = listens_rdd.union(sc.textFile(member.name).map(json.loads))
                listens_rdd.cache().count()
                print("Done!")
                os.remove(member.name)
    print("Done!")

    print("Creating Listens Dataframe...")
    all_listens_df = spark.createDataFrame(listens_rdd.map(convert_listen_to_row), listen_schema)
    print("Done!")

    for need_year in range(LAST_FM_FOUNDING_YEAR, datetime.today().year + 1):
        print("Creating dataframe for year %d..." % need_year)
        year_listens_df = all_listens_df.filter(year(all_listens_df['listened_at']) == need_year)
        print("Done!")

        path = config.HDFS_CLUSTER_URI + os.path.join(destination_path, '%d.parquet' % need_year)
        print("Writing dataframe for year %d to HDFS: %s" % (need_year, path))
        year_listens_df.write.format('parquet').save(path)
        print("Done!")

    print("Creating dataframe for invalid listens...")
    invalid_listens_df = all_listens_df.filter(year(all_listens_df['listened_at']) < LAST_FM_FOUNDING_YEAR)
    print("Done!")
    path = config.HDFS_CLUSTER_URI + os.path.join(destination_path, 'invalid.parquet')
    print("Writing dataframe for invalid listens to HDFS: %s" % path)
    invalid_listens_df.write.format('parquet').save(path)
    print("Done!")


def main(archive):
    hdfs_connection.init_hdfs(config.HDFS_HTTP_URI)
    print('Copying extracted dump to HDFS...')
    copy_to_hdfs(archive)
    print('Done!')
