from listenbrainz_spark.listens.cache import *
from listenbrainz_spark.listens.metadata import *
from listenbrainz_spark import config, hdfs_connection
import listenbrainz_spark

config.HDFS_CLUSTER_URI = "hdfs://127.0.0.1:9000"
config.HDFS_HTTP_URI = "http://127.0.0.1:9870"
hdfs_connection.init_hdfs(config.HDFS_HTTP_URI)

listenbrainz_spark.session = spark
listenbrainz_spark.context = sc

listens_df = get_incremental_listens_df()
listens_df.createOrReplaceTempView("listens")

recording_artist_df = spark.read.parquet(f"{config.HDFS_CLUSTER_URI}/recording_artist")
recording_artist_df.createOrReplaceTempView("recording_artist")

range_type = "all_time"

# Determine time bucket expression
if range_type in ['week', 'last_week']:
    time_bucket_expr = "date_format(listened_at, 'EEEE')"
elif range_type in ['month', 'last_month']:
    time_bucket_expr = "date_format(listened_at, 'd')"
elif range_type in ['year', 'last_year']:
    time_bucket_expr = "date_format(listened_at, 'MMMM')"
elif range_type == 'all_time':
    time_bucket_expr = "year(listened_at)"
else:
    raise ValueError("Invalid range_type")

grouped_query = f"""
SELECT
  user_id,
  artist_mbid,
  artist_name,
  {time_bucket_expr} AS time_bucket,
  COUNT(*) AS listen_count
FROM (
  SELECT
    user_id,
    listened_at,
    artist_element['artist_mbid'] AS artist_mbid,
    artist_element['artist_credit_name'] AS artist_name
  FROM (
    SELECT user_id, listened_at, explode(artists) AS artist_element
    FROM (
      SELECT l.user_id, l.listened_at, ra.artists
      FROM listens l
      JOIN recording_artist ra
      ON l.recording_mbid = ra.recording_mbid
    ) AS joined_table
  ) AS exploded_artists
)
where user_id = 1
GROUP BY user_id, artist_mbid, artist_name, {time_bucket_expr}
ORDER BY user_id, artist_name, time_bucket
"""

result_df = spark.sql(grouped_query)
result_df.show()
