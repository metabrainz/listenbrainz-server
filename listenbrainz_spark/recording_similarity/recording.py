from datetime import datetime, date, time, timedelta

import listenbrainz_spark
from listenbrainz_spark import config, path
from listenbrainz_spark.stats import run_query
from listenbrainz_spark.utils import get_listens_from_new_dump


def build_sessioned_index(listen_table, mbc_table, from_ts, to_ts, session):
    # TODO: Handle case of unmatched recordings breaking sessions!
    return f"""
        WITH listens AS (
                 SELECT user_id
                      , listened_at
                      , COALESCE((recording_data.length / 1000)::BIGINT, 180) AS duration
                      , recording_mbid
                   FROM {listen_table} l
              LEFT JOIN {mbc_table} mbc
                  USING (recording_mbid)
                  WHERE l.recording_mbid IS NOT NULL
                    AND listened_at > {from_ts}
                    AND listened_at < {to_ts}
            ), ordered AS (
                SELECT user_id
                     , listened_at
                     , listened_at - LAG(listened_at, 1) OVER w - LAG(duration, 1) OVER w AS difference
                     , recording_mbid
                  FROM listens
                WINDOW w AS (PARTITION BY user_id ORDER BY listened_at)
            ), sessions AS (
                SELECT user_id
                     , COUNT(*) FILTER ( WHERE difference > {session} ) OVER w AS session_id
                     , recording_mbid
                  FROM ordered
                WINDOW w AS (PARTITION BY user_id ORDER BY listened_at)
            ), grouped_mbids AS (
                SELECT CASE WHEN s1.recording_mbid < s2.recording_mbid THEN s1.recording_mbid ELSE s2.recording_mbid END AS lexical_mbid0
                     , CASE WHEN s1.recording_mbid > s2.recording_mbid THEN s1.recording_mbid ELSE s2.recording_mbid END AS lexical_mbid1
                  FROM sessions s1
                  JOIN sessions s2
                 USING (user_id, session_id) 
                 WHERE s1.recording_mbid != s2.recording_mbid
            ) SELECT lexical_mbid0 AS mbid0
                   , lexical_mbid1 AS mbid1
                   , COUNT(*) AS score
                FROM grouped_mbids
            GROUP BY lexical_mbid0
                   , lexical_mbid1
    """


def main(days, session):
    to_date = datetime.combine(date.today(), time.min)
    from_date = to_date + timedelta(days=-days)

    table = "recording_similarity_listens"
    metadata_table = "mb_metadata_cache"

    get_listens_from_new_dump(from_date, to_date).createOrReplaceTempView(table)

    metadata_df = listenbrainz_spark.sql_context.read.json(config.HDFS_CLUSTER_URI + "/mb_metadata_cache.jsonl")
    metadata_df.createOrReplaceTempView(metadata_table)

    save_path = f"{path.RECORDING_SIMILARITY}/session_based_days_{days}_session_{session}"

    query = build_sessioned_index(table, metadata_table, int(from_date.timestamp()), int(to_date.timestamp()), session)

    run_query(query) \
        .write \
        .format('parquet') \
        .save(config.HDFS_CLUSTER_URI + save_path, mode="overwrite")
