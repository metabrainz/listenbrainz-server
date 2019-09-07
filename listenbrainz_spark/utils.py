import os
import sys
import errno
import logging
import traceback
from py4j.protocol import Py4JJavaError

import listenbrainz_spark
from listenbrainz_spark import stats
from listenbrainz_spark import config
from listenbrainz_spark.stats import run_query
from listenbrainz_spark import hdfs_connection

from listenbrainz_spark.exceptions import FileNotSavedException
from pyspark.sql.utils import AnalysisException

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
        raise Py4JJavaError('Cannot register dataframe "{}": {}\n'.format(table_name, type(err).__name__),
            err.java_exception)

def read_files_from_HDFS(path):
    """ Loads the dataframe stored at the given path in HDFS.

        Args:
            path (str): An HDFS path.
    """
    try:
        df = listenbrainz_spark.sql_context.read.parquet(path)
        return df
    except AnalysisException as err:
      raise AnalysisException('Cannot read "{}" from HDFS: {}\n'.format(path, type(err).__name__),
            stackTrace=traceback.format_exc())
    except Py4JJavaError as err:
        raise Py4JJavaError('An error occurred while fetching "{}": {}\n'.format(path, type(err).__name__),
            err.java_exception)

def get_listens(from_date, to_date):
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
    try:
        if to_date < from_date:
            raise ValueError()
    except ValueError as err:
        logging.error('{}: Data generation window is negative i.e. from_date (date from which start fetching listens)' \
            ' is greater than to_date (date upto which fetch listens).\nAborting...'.format(type(err).__name__))
        sys.exit(-1)

    df = None
    while from_date <= to_date:
        try:
            month = read_files_from_HDFS('{}/data/listenbrainz/{}/{}.parquet'.format(config.HDFS_CLUSTER_URI, from_date.year, from_date.month))
            df = df.union(month) if df else month
        except AnalysisException as err:
            logging.error('{}\nTrying to fetch listens for next date.'.format(str(err)))
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
    hdfs_connection.client.delete(path, recursive=recursive)

def get_status(path):
    """ Checks the status of a directory in HDFS. The function throws HdfsError if the directory
        does not exist otherwise returns a JSON. May be used to check if a directory exists or not.

        Args:
            path (string): Path of the directory to check status for.

        Note: Caller is responsible for initializing HDFS connection.
    """
    status = hdfs_connection.client.status(path)
    return status
