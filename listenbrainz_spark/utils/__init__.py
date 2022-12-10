import errno
import logging
import os
from datetime import datetime
from typing import List

from py4j.protocol import Py4JJavaError
from pyspark.sql import DataFrame, functions
from pyspark.sql.utils import AnalysisException

import listenbrainz_spark
from hdfs.util import HdfsError
from listenbrainz_spark import config, hdfs_connection, path
from listenbrainz_spark.schema import listens_new_schema
from listenbrainz_spark.exceptions import (DataFrameNotAppendedException,
                                           DataFrameNotCreatedException,
                                           FileNotFetchedException,
                                           FileNotSavedException,
                                           HDFSDirectoryNotDeletedException,
                                           PathNotFoundException,
                                           ViewNotRegisteredException)

logger = logging.getLogger(__name__)

# A typical listen is of the form:
# {
#   "artist_mbids": [],
#   "artist_name": "Cake",
#   "listened_at": "2005-02-28T20:39:08Z",
#   "recording_msid": "c559b2f8-41ff-4b55-ab3c-0b57d9b85d11",
#   "recording_mbid": "1750f8ca-410e-4bdc-bf90-b0146cb5ee35",
#   "release_mbid": "",
#   "release_name": null,
#   "tags": [],
#   "track_name": "Tougher Than It Is"
#   "user_id": 5,
# }
# All the keys in the dict are column/field names in a Spark dataframe.


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

    
def get_latest_listen_ts() -> datetime:
    """" Get the listened_at time of the latest listen present
     in the imported dumps
     """
    latest_listen_file = get_listen_files_list()[0]
    df = read_files_from_HDFS(
        os.path.join(path.LISTENBRAINZ_NEW_DATA_DIRECTORY, latest_listen_file)
    )
    return df \
        .select('listened_at') \
        .agg(functions.max('listened_at').alias('latest_listen_ts'))\
        .collect()[0]['latest_listen_ts']
