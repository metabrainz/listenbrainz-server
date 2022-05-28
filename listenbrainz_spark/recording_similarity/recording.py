from datetime import datetime, date, time, timedelta

import listenbrainz_spark
from listenbrainz_spark import config, path
from listenbrainz_spark.schema import recording_similarity_schema
from listenbrainz_spark.stats import run_query
from listenbrainz_spark.utils import get_listens_from_new_dump


def get_complete_index_query(table, threshold):
    return f"""
        WITH symmetric_index AS (
            SELECT CASE WHEN mbid0 < mbid1 THEN mbid0 ELSE mbid1 END AS lexical_mbid0
                 , CASE WHEN mbid0 > mbid1 THEN mbid0 ELSE mbid1 END AS lexical_mbid1
                 , partial_similarity
              FROM {table}
        )
        SELECT lexical_mbid0 AS mbid0
             , lexical_mbid1 AS mbid1
             , INT(SUM(partial_similarity)) AS similarity
          FROM symmetric_index
      GROUP BY lexical_mbid0, lexical_mbid1
        HAVING similarity >= {threshold}
    """


def get_partial_index_query(table, lookahead, session, weight):
    return f"""
        WITH mbid_similarity AS (
            SELECT recording_mbid AS mbid0
                 , LEAD(recording_mbid, {lookahead}) OVER window AS mbid1
                 , unix_timestamp(listened_at) AS ts0
                 , unix_timestamp(LEAD(listened_at, {lookahead}) OVER window) AS ts1
              FROM {table}
             WHERE recording_mbid IS NOT NULL
            WINDOW window AS (PARTITION BY user_id ORDER BY listened_at)
        ), symmetric_index AS (
            SELECT CASE WHEN mbid0 < mbid1 THEN mbid0 ELSE mbid1 END AS lexical_mbid0
                 , CASE WHEN mbid0 > mbid1 THEN mbid0 ELSE mbid1 END AS lexical_mbid1
              FROM mbid_similarity
             WHERE mbid0 IS NOT NULL
               AND mbid1 IS NOT NULL
               AND mbid0 != mbid1
               AND ts1 - ts0 <= {session}
        )
        SELECT lexical_mbid0 AS mbid0
             , lexical_mbid1 AS mbid1
             , COUNT(*) * {weight} AS partial_similarity
          FROM symmetric_index
      GROUP BY lexical_mbid0, lexical_mbid1
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
        query = get_partial_index_query(table, step, session, weight)
        similarity_df = similarity_df.union(run_query(query))
        weight -= decrement

    partial_index_table = "partial_similarity_index"
    similarity_df.createOrReplaceTempView(partial_index_table)

    save_path = f"{path.RECORDING_SIMILARITY}/steps_{steps}_days_{days}_session_{session}_threshold_{threshold}"
    combined_index_query = get_complete_index_query(partial_index_table, threshold)
    run_query(combined_index_query) \
        .write \
        .format('parquet') \
        .save(config.HDFS_CLUSTER_URI + save_path, mode="overwrite")
