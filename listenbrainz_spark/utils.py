import os
import errno

import listenbrainz_spark
from listenbrainz_spark.stats import run_query

from pyspark.sql.utils import AnalysisException

def create_path(path):
    try:
        os.makedirs(path)
    except OSError as e:
        if e.errno != errno.EEXIST:
            raise

def register_dataframe(df, table_name):
    try:
        df.createOrReplaceTempView(table_name)
    except AnalysisException as err:
        raise AnalysisException('Cannot register dataframe "{}": {} \n{}.'.format(table_name, type(err).__name__,
            str(err)), stackTrace=True)
    except Exception as err:
        raise Exception('An error occured while registering dataframe "{}": {} \n{}.'.format(table_name,
            type(err).__name__, str(err)))

def read_files_from_HDFS(path):
    try:
        df = listenbrainz_spark.sql_context.read.parquet(path)
        return df
    except AnalysisException as err:
        raise AnalysisException('Cannot read "{}" from HDFS: {} \n{}.'.format(path, type(err).__name__, str(err)),
            stackTrace=True)
    except Exception as err:
        raise Exception('An error occured while fetching "{}": {} \n{}.'.format(path, type(err).__name__, str(err)))
