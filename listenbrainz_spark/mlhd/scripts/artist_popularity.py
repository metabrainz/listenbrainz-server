import os
import listenbrainz_spark

from listenbrainz_spark import config


def main():
    listenbrainz_spark.init_spark_session('artist_popularity')
    mlhd_df_path = config.HDFS_CLUSTER_URI + os.path.join('/data', 'mlhd', '*.avro')
    print('Loading MLHD Dataframe...')
    mlhd_df = listenbrainz_spark.sql_context.read.format('avro').load(mlhd_df_path)
    print("Loaded!")
    print("Number of rows: %d" % mlhd_df.count())
    mlhd_df.registerTempTable('mlhd')
    print("Running SQL...")
    artist_popularity_df = listenbrainz_spark.sql_context.sql("""
            SELECT artist_mbid, COUNT(artist_mbid) as cnt
              FROM mlhd
          GROUP BY artist_mbid
          ORDER BY cnt DESC
    """)
    print("number of rows: ", artist_popularity_df.count())
    artist_popularity_df.show()
    print("Saving...")
    csv_path = config.HDFS_CLUSTER_URI + os.path.join('/data', 'mlhd', 'artist_popularity-1.csv')
    artist_popularity_df.write.csv(csv_path)
    print("Saved to %s!" % csv_path)
