import errno
import logging
import os
from time import sleep

import pika
from py4j.protocol import Py4JJavaError
from pyspark.sql.utils import AnalysisException

import listenbrainz_spark
from hdfs.util import HdfsError
from listenbrainz_spark import config, hdfs_connection, path, stats
from listenbrainz_spark.exceptions import (DataFrameNotAppendedException,
                                           DataFrameNotCreatedException,
                                           FileNotFetchedException,
                                           FileNotSavedException,
                                           HDFSDirectoryNotDeletedException,
                                           HDFSException,
                                           PathNotFoundException,
                                           ViewNotRegisteredException)


logger = logging.getLogger(__name__)

# A typical listen is of the form:
# {
#   "artist_mbids": [],
#   "artist_msid": "6276299c-57e9-4014-9fdd-ab9ed800f61d",
#   "artist_name": "Cake",
#   "listened_at": "2005-02-28T20:39:08Z",
#   "recording_msid": "c559b2f8-41ff-4b55-ab3c-0b57d9b85d11",
#   "recording_mbid": "1750f8ca-410e-4bdc-bf90-b0146cb5ee35",
#   "release_mbid": "",
#   "release_msid": null,
#   "release_name": null,
#   "tags": [],
#   "track_name": "Tougher Than It Is"
#   "user_name": "vansika",
# }
# All the keys in the dict are column/field names in a Spark dataframe.


def append(df, dest_path):
    """ Append a dataframe to existing dataframe in HDFS or write a new one
        if dataframe does not exist.

        Args:
            df (dataframe): Dataframe to append.
            dest_path (string): Path where the existing dataframe is found or
                                where a new dataframe should be created.
    """
    try:
        df.write.mode('append').parquet(config.HDFS_CLUSTER_URI + dest_path)
    except Py4JJavaError as err:
        raise DataFrameNotAppendedException(err.java_exception, df.schema)


def init_rabbitmq(username, password, host, port, vhost, log=logger.error, heartbeat=None):
    while True:
        try:
            credentials = pika.PlainCredentials(username, password)
            connection_parameters = pika.ConnectionParameters(
                host=host,
                port=port,
                virtual_host=vhost,
                credentials=credentials,
                heartbeat=heartbeat,
            )
            return pika.BlockingConnection(connection_parameters)
        except Exception as e:
            log('Error while connecting to RabbitMQ', exc_info=True)
            sleep(1)


def create_dataframe(row, schema):
    """ Create a dataframe containing a single row.

        Args:
            row (pyspark.sql.Row object): A Spark SQL row.
            schema: Dataframe schema.

        Returns:
            df (dataframe): Newly created dataframe.
    """
    try:
        df = listenbrainz_spark.session.createDataFrame([row], schema=schema)
        return df
    except Py4JJavaError as err:
        raise DataFrameNotCreatedException(err.java_exception, row)


def create_path(path):
    try:
        os.makedirs(path)
    except OSError as e:
        if e.errno != errno.EEXIST:
            raise


def register_dataframe(df, table_name):
    """ Creates a view to be used for Spark SQL, etc. Replaces the view if a view with the
        same name exists.

        Args:
            df (dataframe): Dataframe to register.
            table_name (str): Name of the view.
    """
    try:
        df.createOrReplaceTempView(table_name)
    except Py4JJavaError as err:
        raise ViewNotRegisteredException(err.java_exception, table_name)


def read_files_from_HDFS(path):
    """ Loads the dataframe stored at the given path in HDFS.

        Args:
            path (str): An HDFS path.
    """
    try:
        df = listenbrainz_spark.sql_context.read.parquet(config.HDFS_CLUSTER_URI + path)
        return df
    except AnalysisException as err:
        raise PathNotFoundException(str(err), path)
    except Py4JJavaError as err:
        raise FileNotFetchedException(err.java_exception, path)


def get_listens(from_date, to_date, dest_path):
    """ Prepare dataframe of months falling between from_date and to_date (both inclusive).

        Args:
            from_date (datetime): Date from which start fetching listens.
            to_date (datetime): Date upto which fetch listens.
            dest_path (str): HDFS path to fetch listens from.

        Returns:
            df: Dataframe of listens.
    """
    if to_date < from_date:
        raise ValueError('{}: Data generation window is negative i.e. from_date (date from which start fetching listens)'
                         ' is greater than to_date (date upto which fetch listens).'.format(type(ValueError).__name__))
    df = None
    while from_date <= to_date:
        try:
            month = read_files_from_HDFS('{}/{}/{}.parquet'.format(dest_path, from_date.year, from_date.month))
            df = df.union(month) if df else month
        except PathNotFoundException as err:
            logger.debug('{}\nFetching file for next date...'.format(err))
        # go to the next month of from_date
        from_date = stats.offset_months(date=from_date, months=1, shift_backwards=False)
        # shift to the first of the month
        from_date = stats.replace_days(from_date, 1)
    if not df:
        logger.error('Listening history missing form HDFS')
        raise HDFSException("Listening history missing from HDFS")
    return df


def save_parquet(df, path, mode='overwrite'):
    """ Save dataframe as parquet to given path in HDFS.

        Args:
            df (dataframe): Dataframe to save.
            path (str): Path in HDFS to save the dataframe.
            mode (str): The mode with which to write the paquet.
    """
    try:
        df.write.format('parquet').save(config.HDFS_CLUSTER_URI + path, mode=mode)
    except Py4JJavaError as err:
        raise FileNotSavedException(err.java_exception, path)


def create_dir(path):
    """ Creates a directory in HDFS.

        Args:
            path (string): Path of the directory to be created.

        Note: >> Caller is responsibe for initializing HDFS connection.
              >> The function does not throw an error if the directory path already exists.
    """
    hdfs_connection.client.makedirs(path)


def delete_dir(path, recursive=False):
    """ Deletes a directory recursively from HDFS.

        Args:
            path (string): Path of the directory to be deleted.

        Note: >> Caller is responsible for initializing HDFS connection.
              >> Raises HdfsError if trying to delete a non-empty directory.
                 For non-empty directory set recursive to 'True'.
    """
    deleted = hdfs_connection.client.delete(path, recursive=recursive)
    if not deleted:
        raise HDFSDirectoryNotDeletedException('', path)


def path_exists(path):
    """ Checks if the path exists in HDFS. The function returns False if the path
        does not exist otherwise returns True.

        Args:
            path (string): Path to check status for.

        Note: Caller is responsible for initializing HDFS connection.
    """
    path_found = hdfs_connection.client.status(path, strict=False)
    if path_found:
        return True
    return False


def hdfs_walk(path, depth=0):
    """ Depth-first walk of HDFS filesystem.

        Args:
            path (str): Path to start DFS.
            depth (int): Maximum depth to explore files/folders. 0 for no limit.

        Returns:
            walk: a generator yeilding tuples (path, dirs, files).
    """
    try:
        walk = hdfs_connection.client.walk(hdfs_path=path, depth=depth)
        return walk
    except HdfsError as err:
        raise PathNotFoundException(str(err), path)


def read_json(hdfs_path, schema):
    """ Upload JSON file to HDFS as parquet.

        Args:
            hdfs_path (str): HDFS path to upload JSON.
            schema: Blueprint of parquet.

        Returns:
            df (parquet): Dataframe.
    """
    df = listenbrainz_spark.session.read.json(config.HDFS_CLUSTER_URI + hdfs_path, schema=schema)
    return df


def upload_to_HDFS(hdfs_path, local_path):
    """ Upload local file to HDFS.

        Args:
            hdfs_path (str): HDFS path to upload local file.
            local_path (str): Local path of file to be uploaded.
    """
    hdfs_connection.client.upload(hdfs_path=hdfs_path, local_path=local_path)


def rename(hdfs_src_path: str, hdfs_dst_path: str):
    """ Move a file or folder in HDFS

        Args:
            hdfs_src_path – Source path.
            hdfs_dst_path – Destination path. If the path already exists and is a directory, the source will be moved into it.
    """
    hdfs_connection.client.rename(hdfs_src_path, hdfs_dst_path)


def copy(hdfs_src_path: str, hdfs_dst_path: str, overwrite: bool = False):
    """ Copy a file or folder in HDFS

        Args:
            hdfs_src_path – Source path.
            hdfs_dst_path – Destination path. If the path already exists and is a directory, the source will be copied into it.
            overwrite - Wether to overwrite the path if it already exists.
    """
    walk = hdfs_walk(hdfs_src_path)

    for (root, dirs, files) in walk:
        for _file in files:
            src_file_path = os.path.join(root, _file)
            dst_file_path = os.path.join(hdfs_dst_path, os.path.relpath(src_file_path, hdfs_src_path))
            with hdfs_connection.client.read(src_file_path) as reader:
                with hdfs_connection.client.write(dst_file_path, overwrite=overwrite) as writer:
                    writer.write(reader.read())
