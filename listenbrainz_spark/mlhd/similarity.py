import logging

from listenbrainz_spark.mlhd.download import MLHD_PLUS_CHUNKS
from listenbrainz_spark.path import MLHD_PLUS_DATA_DIRECTORY, RECORDING_LENGTH_WITH_ID_DATAFRAME
from listenbrainz_spark.stats import run_query
from listenbrainz_spark.utils import read_files_from_HDFS


DEFAULT_TRACK_LENGTH = 180

logger = logging.getLogger(__name__)


def build_partial_sessioned_index(listen_table, metadata_table, session, max_contribution, skip_threshold):
    return f"""
            WITH listens AS (
                 SELECT user_id
                      , BIGINT(listened_at)
                      , CAST(COALESCE(r.length / 1000, {DEFAULT_TRACK_LENGTH}) AS BIGINT) AS duration
                      , recording_id
                      , artist_credit_mbids
                   FROM {listen_table} l
                   JOIN {metadata_table} r
                  USING (recording_mbid)
                  WHERE l.recording_mbid IS NOT NULL
                    AND l.recording_mbid != ''
            ), ordered AS (
                SELECT user_id
                     , listened_at
                     , listened_at - LAG(listened_at, 1) OVER w - LAG(duration, 1) OVER w AS difference
                     , recording_id
                     , artist_credit_mbids
                  FROM listens
                WINDOW w AS (PARTITION BY user_id ORDER BY listened_at)
            ), sessions AS (
                SELECT user_id
                     -- spark doesn't support window aggregate functions with FILTER clause
                     , COUNT_IF(difference > {session}) OVER w AS session_id
                     , LEAD(difference, 1) OVER w < {skip_threshold} AS skipped
                     , recording_id
                     , artist_credit_mbids
                  FROM ordered
                WINDOW w AS (PARTITION BY user_id ORDER BY listened_at)
            ), sessions_filtered AS (
                SELECT user_id
                     , session_id
                     , recording_id
                     , artist_credit_mbids
                  FROM sessions
                 WHERE NOT skipped
            ), user_grouped_mbids AS (
                SELECT s1.user_id
                     , s1.recording_id AS id0
                     , s2.recording_id AS id1
                     , COUNT(*) AS part_score
                  FROM sessions_filtered s1
                  JOIN sessions_filtered s2
                    ON s1.user_id = s2.user_id
                   AND s1.session_id = s2.session_id
                   AND s1.recording_id < s2.recording_id
                 WHERE NOT arrays_overlap(s1.artist_credit_mbids, s2.artist_credit_mbids)
              GROUP BY s1.user_id
                     , s1.recording_id
                     , s2.recording_id   
            )
                SELECT id0
                     , id1
                     , SUM(LEAST(part_score, {max_contribution})) AS score
                  FROM user_grouped_mbids
              GROUP BY id0
                     , id1
    """


def main(session, contribution, threshold, limit, skip):
    """ Generate similar recordings based on MLHD listening sessions.

    Args:
        session: the max time difference between two listens in a listening session
        contribution: the max contribution a user's listens can make to a recording pair's similarity score
        threshold: the minimum similarity score for two recordings to be considered similar
        limit: the maximum number of similar recordings to request for a given recording
            (this limit is instructive only, upto 2x number of recordings may be returned)
        skip: the minimum threshold in seconds to mark a listen as skipped. we cannot just mark a negative difference
            as skip because there may be a difference in track length in MB and music services and also issues in
            timestamping listens.
    """
    table = "mlhd_recording_similarity_listens"
    metadata_table = "recording_length"
    skip_threshold = -skip

    run_query("SET spark.sql.shuffle.partitions = 2000").collect()

    read_files_from_HDFS(RECORDING_LENGTH_WITH_ID_DATAFRAME).createOrReplaceTempView(metadata_table)
    mlhd_df = read_files_from_HDFS(MLHD_PLUS_DATA_DIRECTORY)
    mlhd_df.createOrReplaceTempView(table)

    for chunk in MLHD_PLUS_CHUNKS:
        logger.info("Processsing chunk: %s", chunk)
        filter_clause = f"user_id LIKE '{chunk}%'"
        mlhd_df.filter(filter_clause).createOrReplaceTempView(table)
        query = build_partial_sessioned_index(table, metadata_table, session, contribution, skip_threshold)
        run_query(query) \
            .repartition(128, "id0") \
            .write \
            .mode("overwrite") \
            .parquet(f"/mlhd-session-output/{chunk}", compression="zstd")

    algorithm = f"session_based_mlhd_session_{session}_contribution_{contribution}_threshold_{threshold}_limit_{limit}_skip_{skip}"

    return {
        "type": "similar_recordings_mlhd",
        "algorithm": algorithm
    }
