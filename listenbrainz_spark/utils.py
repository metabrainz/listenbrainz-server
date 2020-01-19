import os
import sys
import errno
import logging
import traceback
import pika
from py4j.protocol import Py4JJavaError

import listenbrainz_spark
from listenbrainz_spark.stats import run_query
from listenbrainz_spark import stats, config, path, schema
from listenbrainz_spark import hdfs_connection
from listenbrainz_spark.exceptions import FileNotSavedException, ViewNotRegisteredException, PathNotFoundException, \
    FileNotFetchedException, DataFrameNotCreatedException, DataFrameNotAppendedException, HDFSDirectoryNotDeletedException
from flask import current_app
from hdfs.util import HdfsError
from brainzutils.flask import CustomFlask
from pyspark.sql.utils import AnalysisException
from time import sleep

def append(df, dest_path):
    """ Append a dataframe to existing dataframe in HDFS or write a new one
        if dataframe does not exist.

        Args:
            df (dataframe): Dataframe to append.
            dest_path (string): Path where the existing dataframe is found or where a new dataframe should be created.
    """
    try:
        df.write.mode('append').parquet(dest_path)
    except Py4JJavaError as err:
        raise DataFrameNotAppendedException(err.java_exception, df.schema)

def create_app(debug=None):
    """ Uses brainzutils (https://github.com/metabrainz/brainzutils-python) to log exceptions to sentry.
    """
    # create flask application
    app = CustomFlask(import_name=__name__)
    # load config
    config_file = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'config.py')

    # config must exist to link the file with our flask app.
    if os.path.exists(config_file):
        app.config.from_pyfile(config_file)
    else:
        raise FileNotFoundError(errno.ENOENT, os.strerror(errno.ENOENT), config_file)

    if debug is not None:
        app.debug = debug

    # attach app logs to sentry.
    app.init_loggers(
        sentry_config=app.config.get('LOG_SENTRY')
    )
    return app


def init_rabbitmq(username, password, host, port, vhost, log=logging.error):
    while True:
        try:
            credentials = pika.PlainCredentials(username, password)
            connection_parameters = pika.ConnectionParameters(
                host=host,
                port=port,
                virtual_host=vhost,
                credentials=credentials,
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
        df = listenbrainz_spark.sql_context.read.parquet(path)
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

        Returns:
            df (dataframe): Columns can be depicted as:
                [
                    'artist_mbids', 'artist_msid', 'artist_name', 'listened_at', 'recording_mbid'
                    'recording_msid', 'release_mbid', 'release_msid', 'release_name', 'tags',
                    'track_name', 'user_name'
                ]
    """
    if to_date < from_date:
        raise ValueError('{}: Data generation window is negative i.e. from_date (date from which start fetching listens)' \
            ' is greater than to_date (date upto which fetch listens).\nAborting...'.format(type(err).__name__))
    df = None
    while from_date <= to_date:
        try:
            month = read_files_from_HDFS('{}/{}/{}.parquet'.format(dest_path, from_date.year, from_date.month))
            df = df.union(month) if df else month
        except PathNotFoundException as err:
            current_app.logger.warning('{}\nFetching file for next date...'.format(err))
        # go to the next month of from_date
        from_date = stats.adjust_days(from_date, config.STEPS_TO_REACH_NEXT_MONTH, shift_backwards=False)
        # shift to the first of the month
        from_date = stats.replace_days(from_date, 1)
    return df

def save_parquet(df, path):
    """ Save dataframe as parquet to given path in HDFS.

        Args:
            df (dataframe): Dataframe to save.
            path (str): Path in HDFS to save the dataframe.
    """
    try:
        df.write.format('parquet').save(path, mode='overwrite')
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
    try:
        deleted = hdfs_connection.client.delete(path, recursive=recursive)
        if not deleted:
            raise HDFSDirectoryNotDeletedException('', path)
        return deleted
    except HdfsError as err:
        raise HDFSDirectoryNotDeletedException(str(err), path)

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
