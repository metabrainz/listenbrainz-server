import sys
import listenbrainz_spark
import time
from datetime import datetime  


def top_artist(user_name):
	playcounts_df = listenbrainz_spark.sql_context.sql("""
            SELECT artist_name, count(track_name) as cnt
              FROM listen
             WHERE user_name = '%s'
          GROUP BY artist_name
          ORDER BY cnt DESC
             LIMIT 20
        """ % user_name)
	playcounts_df.show()

def top_recording(user_name):
	playcounts_df = listenbrainz_spark.sql_context.sql("""
            SELECT track_name, count(track_name) as cnt
              FROM listen
             WHERE user_name = '%s'
          GROUP BY track_name
          ORDER BY cnt DESC
             LIMIT 20
        """ % user_name)
	playcounts_df.show()

def top_release(user_name):
	playcounts_df = listenbrainz_spark.sql_context.sql("""
            SELECT release_name, count(release_name) as cnt
              FROM listen
             WHERE user_name = '%s'
          GROUP BY release_name
          ORDER BY cnt DESC
             LIMIT 20
        """ % user_name)
	playcounts_df.show()

def run_queries(user_name):
	top_artist(user_name)
	top_recording(user_name)
	top_release(user_name)

def main(app_name, user_name):
	t0 = time.time()
	listenbrainz_spark.init_spark_session(app_name)
	prev_month = datetime.now().month - 1
	try:
		df = listenbrainz_spark.sql_context.read.parquet('hdfs://hadoop-master:9000/data/listenbrainz/2019/{}.parquet'.format(prev_month))
		print("Loading dataframe...")
	except:
		print ("No Listens for last month")
		sys.exit(-1)
	df.printSchema()
	print(df.columns)
	print(df.count())
	df.registerTempTable('listen')
	print("Running Query...")
	query_t0 = time.time()
	print("DataFrame loaded in %.2f s" % (time.time() - query_t0))
	run_queries(user_name)
