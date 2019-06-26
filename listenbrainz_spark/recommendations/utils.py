import os
import logging

from listenbrainz_spark.stats import run_query

import listenbrainz_spark
from pyspark.sql.utils import AnalysisException
from jinja2 import Environment, FileSystemLoader

def save_html(filename, context, template):
    path = os.path.dirname(os.path.abspath(__file__))
    template_environment = Environment(
    loader=FileSystemLoader(os.path.join(path, 'templates')))
    outputfile = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'html_files', filename)
    with open(outputfile, 'w') as f:
        html = template_environment.get_template(template).render(context)
        f.write(html)

def initialize_spark_session(app_name):
    try:
        listenbrainz_spark.init_spark_session(app_name)
        return True
    except AttributeError as err:
        logging.error('Cannot initialize Spark session "{}": {} \n {}.'.format(app_name, type(err).__name__,
            str(err)), exc_info=True)
        return False
    except Exception as err:
        logging.error('An error occurred while initializing Spark session "{}": {} \n {}.'.format(app_name,
            type(err)  .__name__,str(err)), exc_info=True)
        return False

def register_dataframe(df, table_name):
    try:
        df.createOrReplaceTempView(table_name)
        return True
    except AnalysisException as err:
        logging.error('Cannot register dataframe "{}": {} \n {}.'.format(table_name, type(err).__name__, str(err)))
        return False
    except Exception as err:
        logging.error('An error occured while registering dataframe "{}": {} \n {}.'.format(table_name,
            type(err).__name__, str(err)), exc_info=True)
        return False

def read_files_from_HDFS(path):
    try:
        df = listenbrainz_spark.sql_context.read.parquet(path)
        return df
    except AnalysisException as err:
        logging.error('Cannot read "{}" from HDFS: {} \n {}. '.format(path, type(err).__name__, str(err)))
        return None
    except Exception as err:
        logging.error('An error occured while fetching "{}": {} \n {}. '.format(path, type(err).__name__,
            str(err)), exc_info=True)
        return None
