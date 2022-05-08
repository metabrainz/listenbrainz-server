from datetime import datetime

from listenbrainz_spark import config, path
from listenbrainz_spark.constants import LAST_FM_FOUNDING_YEAR
from listenbrainz_spark.stats import run_query
from listenbrainz_spark.utils import get_latest_listen_ts, get_listens_from_new_dump


def get_recording_discovery():
    to_date = get_latest_listen_ts()
    from_date = datetime(LAST_FM_FOUNDING_YEAR, 1, 1)
    get_listens_from_new_dump(from_date, to_date) \
        .createOrReplaceTempView("recording_discovery")

    run_query("""
        SELECT user_id
             , recording_mbid
             , last(listened_at) AS latest_listened_at
          FROM recording_discovery
         WHERE recording_mbid IS NOT NULL
      GROUP BY user_id
             , recording_mbid
    """) \
        .write \
        .format('parquet') \
        .save(config.HDFS_CLUSTER_URI + path.RECORDING_DISCOVERY, mode="overwrite")
