import os
import listenbrainz_spark
import logging
import sys

from datetime import datetime
from listenbrainz_spark import config
from listenbrainz_spark.mlhd import MLHD_DATA_PATH
from py4j.protocol import Py4JJavaError
from pyspark.sql.utils import AnalysisException, QueryExecutionException


def main():
    listenbrainz_spark.init_spark_session('artist_popularity')
    mlhd_df_path = config.HDFS_CLUSTER_URI + os.path.join(MLHD_DATA_PATH, '*.avro')
    try:
        print('Loading MLHD Dataframe...')
        mlhd_df = listenbrainz_spark.sql_context.read.format('avro').load(mlhd_df_path)
        print("Loaded!")
    except AnalysisException as e:
        logging.critical("Error while reading MLHD avro files: %s", str(e))
        raise

    print("Number of rows: %d" % mlhd_df.count())
    try:
        mlhd_df.registerTempTable('mlhd')
    except AnalysisException as e:
        logging.critical("Error while registering dataframe mlhd: %s", str(e))
        raise

    for _ in range(5):
        try:
            print("Running SQL...")
            artist_popularity_df = listenbrainz_spark.sql_context.sql("""
                    SELECT artist_mbid, COUNT(artist_mbid) as cnt
                      FROM mlhd
                  GROUP BY artist_mbid
                  ORDER BY cnt DESC
            """)
            break
        except Py4JJavaError as e:
            logging.error("error while running the query: %s", str(e))
    else:
        logging.critical("Could not run query. Exiting...")
        sys.exit(-1)

    print("number of rows: ", artist_popularity_df.count())
    artist_popularity_df.show()
    print("Saving...")
    file_name = 'mlhd-artist-popularity-%s.csv' % datetime.now.strftime('%Y%m%d-%H%M%S')
    csv_path = config.HDFS_CLUSTER_URI + os.path.join(MLHD_DATA_PATH, 'csv', file_name)
    for _ in range(10):
        try:
            artist_popularity_df.write.csv(csv_path)
            break
        except Exception as e:
            logging.error("Couldn't write result to CSV, trying again, error: %s", str(e))
    else:
        logging.critical("Could not write results to HDFS, exiting...")
        sys.exit(-1)

    print("Saved to %s!" % csv_path)
