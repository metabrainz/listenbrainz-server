from datetime import datetime, date, time, timedelta

import listenbrainz_spark
from listenbrainz_spark import config, path
from listenbrainz_spark.schema import recording_similarity_schema
from listenbrainz_spark.stats import run_query
from listenbrainz_spark.utils import get_listens_from_new_dump


def build_sessioned_index(listen_table, mbc_table, from_ts, to_ts, threshold):
    # TODO: Handle case of unmatched recordings breaking sessions!
    return f"""
        WITH listens AS (
                 SELECT user_id
                      , listened_at
                      , COALESCE((recording_data->>'length')::INT / 1000, 180) AS duration
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
                     , COUNT(*) FILTER ( WHERE difference > {threshold} ) OVER w AS session_id
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


def main(steps, days, session, threshold):
    to_date = datetime.combine(date.today(), time.min)
    from_date = to_date + timedelta(days=-days)

    table = "recording_similarity_listens"

    get_listens_from_new_dump(from_date, to_date).createOrReplaceTempView(table)

    weight = 1.0
    decrement = 1.0 / steps

    similarity_df = listenbrainz_spark.session.createDataFrame([], schema=recording_similarity_schema)
    for step in range(1, steps + 1, 1):
        query = (table, step, session, weight)
        similarity_df = similarity_df.union(run_query(query))
        weight -= decrement

    partial_index_table = "partial_similarity_index"
    similarity_df.createOrReplaceTempView(partial_index_table)

    save_path = f"{path.RECORDING_SIMILARITY}/steps_{steps}_days_{days}_session_{session}_threshold_{threshold}"
    # combined_index_query = get_complete_index_query(partial_index_table, threshold)
    # run_query(combined_index_query) \
    #     .write \
    #     .format('parquet') \
    #     .save(config.HDFS_CLUSTER_URI + save_path, mode="overwrite")
