import json
import os
import shutil
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
import pyspark.sql.functions as sql_functions

FORCE = True

def _is_listens_file(filename):
    """ Check if passed filename is a file which contains listens

    Args:
        filename (str): the name of the file

    Returns:
        bool: True if the file contains listens, False otherwise
    """
    return filename.endswith('.listens')


def _process_listens_file(dataframes, invalid_df, filename):
    """ Process a file containing listens from the ListenBrainz dump and add listens to
    appropriate dataframes.

    Args:
        dataframes (dict(list)): a dict with key being years and value being a list containing
                                dataframes for each month of the year
        invalid_df (dataframe): a dataframe containing invalid listens from the dump
        filename (str): the file to be processed

    Returns: (dataframes, invalid_df)
            dataframes: a dict with the same format as the dataframes arg but containing listens from the
                        new file
            invalid_df (dataframe): dataframe containing invalid listens from the dump.
    """

    def listened_in_month(listened_at, year, month):
        """ Filter to filter listen dataframes according to month and year.

        Args:
            listened_at: the listened_at column from a listens dataframe
            year (int): the year needed
            month (int): the month needed.
        """
        return (sql_functions.year(listened_at) == year) & (sql_functions.month(listened_at) == month)

    def invalid(listened_at):
        return sql_functions.year(listened_at) < LAST_FM_FOUNDING_YEAR

    file_rdd = sc.textFile(filename).map(json.loads)
    file_df = spark.createDataFrame(file_rdd.map(convert_listen_to_row), listen_schema).cache()
    print("Listens in file: %d" % file_df.count())
    processed_dfs = {}
    for year in range(LAST_FM_FOUNDING_YEAR, datetime.today().year + 1):
        if year not in processed_dfs:
            processed_dfs[year] = [spark.createDataFrame(sc.emptyRDD(), listen_schema) for month in range(12)]

        for month_index in range(12):
            month = month_index + 1
            month_df = file_df.filter(listened_in_month(file_df['listened_at'], year=year, month=month))
            try:
                current_df = dataframes[year][month_index]
            except KeyError:
                current_df = spark.createDataFrame(sc.emptyRDD(), listen_schema)

            processed_dfs[year][month_index] = current_df.union(month_df)

    file_invalid_df = file_df.filter(invalid(file_df['listened_at']))
    processed_invalid_df = invalid_df.union(file_invalid_df)
    return processed_dfs, processed_invalid_df


def copy_to_hdfs(archive, threads=4):
    """ Create Spark Dataframes from a listens dump and save it to HDFS.

    Args:
        archive (str): the path to the listens dump
        threads (int): the number of threads to use for decompression of the archive
    """
    tmp_dump_dir = tempfile.mkdtemp()
    pxz_command = ['pxz', '--decompress', '--stdout', archive, '-T{}'.format(threads)]
    pxz = subprocess.Popen(pxz_command, stdout=subprocess.PIPE)
    destination_path = os.path.join('/', 'data', 'listenbrainz')
    if FORCE:
        print('Removing data directory if present...')
        hdfs_connection.client.delete(destination_path, recursive=True)
        print('Done!')

    print('Creating Listen dataframes...')
    dataframes = {}
    invalid_df = spark.createDataFrame(sc.emptyRDD(), listen_schema)
    with tarfile.open(fileobj=pxz.stdout, mode='r|') as tar:
        for member in tar:
            if member.isfile() and _is_listens_file(member.name):
                print('Loading %s...' % member.name)
                tar.extract(member)
                hdfs_tmp_path = os.path.join(tmp_dump_dir, member.name)
                hdfs_connection.client.upload(hdfs_path=hdfs_tmp_path, local_path=member.name)
                dataframes, invalid_df = _process_listens_file(dataframes, invalid_df, config.HDFS_CLUSTER_URI + hdfs_tmp_path)
                os.remove(member.name)
                hdfs_connection.client.delete(hdfs_tmp_path)
                print("Done!")
    print("Dataframes created!")

    print("Writing dataframes...")
    for year in range(LAST_FM_FOUNDING_YEAR, datetime.today().year + 1):
        for month_index in range(12):
            print("Writing dataframe for %d/%d..." % (month_index + 1, year))
            path = config.HDFS_CLUSTER_URI + os.path.join(destination_path, str(year), str(month_index + 1) + '.parquet')
            dataframes[year][month_index].write.format('parquet').save(path)
            print("Done!")
            print("Wrote %d listens!" % dataframes[year][month_index].count())
    print("Dataframes written!")

    path = config.HDFS_CLUSTER_URI + os.path.join(destination_path, 'invalid.parquet')
    print("Writing dataframe for invalid listens to HDFS: %s" % path)
    invalid_df.write.format('parquet').save(path)
    print("Wrote %d listens!" % invalid_df.count())
    print("Done!")

    print("Deleting temporary directories...")
    shutil.rmtree(tmp_dump_dir)


def main(archive):
    hdfs_connection.init_hdfs(config.HDFS_HTTP_URI)
    print('Copying extracted dump to HDFS...')
    copy_to_hdfs(archive)
    print('Done!')
