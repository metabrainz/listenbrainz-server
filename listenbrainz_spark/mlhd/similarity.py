from more_itertools import chunked

from listenbrainz_spark.mlhd.download import MLHD_PLUS_CHUNKS
from listenbrainz_spark.path import RECORDING_LENGTH_DATAFRAME, MLHD_PLUS_DATA_DIRECTORY
from listenbrainz_spark.stats import run_query
from listenbrainz_spark.utils import read_files_from_HDFS


DEFAULT_TRACK_LENGTH = 180


def build_partial_sessioned_index(listen_table, metadata_table, session, max_contribution, skip_threshold):
    return f"""
            WITH listens AS (
                 SELECT user_id
                      , BIGINT(listened_at)
                      , CAST(COALESCE(r.length / 1000, {DEFAULT_TRACK_LENGTH}) AS BIGINT) AS duration
                      , recording_mbid
                      , artist_credit_mbids
                   FROM {listen_table} l
              LEFT JOIN {metadata_table} r
                  USING (recording_mbid)
                  WHERE l.recording_mbid IS NOT NULL
                    AND l.recording_mbid != ''
            ), ordered AS (
                SELECT user_id
                     , listened_at
                     , listened_at - LAG(listened_at, 1) OVER w - LAG(duration, 1) OVER w AS difference
                     , recording_mbid
                     , artist_credit_mbids
                  FROM listens
                WINDOW w AS (PARTITION BY user_id ORDER BY listened_at)
            ), sessions AS (
                SELECT user_id
                     -- spark doesn't support window aggregate functions with FILTER clause
                     , COUNT_IF(difference > {session}) OVER w AS session_id
                     , LEAD(difference, 1) OVER w < {skip_threshold} AS skipped
                     , recording_mbid
                     , artist_credit_mbids
                  FROM ordered
                WINDOW w AS (PARTITION BY user_id ORDER BY listened_at)
            ), sessions_filtered AS (
                SELECT user_id
                     , session_id
                     , recording_mbid
                     , artist_credit_mbids
                  FROM sessions
                 WHERE NOT skipped    
            ), user_grouped_mbids AS (
                SELECT user_id
                     , IF(s1.recording_mbid < s2.recording_mbid, s1.recording_mbid, s2.recording_mbid) AS lexical_mbid0
                     , IF(s1.recording_mbid > s2.recording_mbid, s1.recording_mbid, s2.recording_mbid) AS lexical_mbid1
                  FROM sessions_filtered s1
                  JOIN sessions_filtered s2
                 USING (user_id, session_id)
                 WHERE s1.recording_mbid != s2.recording_mbid
                   AND NOT arrays_overlap(s1.artist_credit_mbids, s2.artist_credit_mbids)
            )
                SELECT user_id
                     , lexical_mbid0 AS mbid0
                     , lexical_mbid1 AS mbid1
                     , LEAST(COUNT(*), {max_contribution}) AS part_score
                  FROM user_grouped_mbids
              GROUP BY user_id
                     , lexical_mbid0
                     , lexical_mbid1
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

    read_files_from_HDFS(RECORDING_LENGTH_DATAFRAME).createOrReplaceTempView(metadata_table)
    mlhd_df = read_files_from_HDFS(MLHD_PLUS_DATA_DIRECTORY)

    first_batch = True

    for chunks in chunked(MLHD_PLUS_CHUNKS, 2):
        filter_clause = " OR ".join([f"user_id LIKE '{chunk}%'" for chunk in chunks])
        mlhd_df.filter(filter_clause).createOrReplaceTempView(table)
        query = build_partial_sessioned_index(table, metadata_table, session, contribution, skip_threshold)

        if first_batch:
            mode = "overwrite"
            first_batch = False
        else:
            mode = "append"

        run_query(query).write.mode(mode).parquet("/mlhd-session-output")

    algorithm = f"session_based_mlhd_session_{session}_contribution_{contribution}_threshold_{threshold}_limit_{limit}_skip_{skip}"

    return {
        "type": "similar_recordings_mlhd",
        "algorithm": algorithm
    }
