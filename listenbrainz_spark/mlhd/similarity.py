import logging

from more_itertools import chunked

import listenbrainz_spark
from listenbrainz_spark import hdfs_connection, config
from listenbrainz_spark.mlhd.download import MLHD_PLUS_CHUNKS
from listenbrainz_spark.path import MLHD_PLUS_DATA_DIRECTORY, RECORDING_LENGTH_DATAFRAME
from listenbrainz_spark.stats import run_query
from listenbrainz_spark.utils import read_files_from_HDFS


RECORDINGS_PER_MESSAGE = 10000
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


def build_full_sessioned_index(chunks_table, metadata_table, threshold, limit):
    return f"""
        WITH thresholded_mbids AS (
            SELECT id0
                 , id1
                 , SUM(score) AS total_score
              FROM {chunks_table}
          GROUP BY id0
                 , id1
            HAVING total_score > {threshold}
        ), ranked_mbids AS (
            SELECT id0
                 , id1
                 , total_score
                 , rank() OVER w AS rank
              FROM thresholded_mbids
            WINDOW w AS (PARTITION BY id0 ORDER BY total_score DESC)
        )   SELECT r0.recording_mbid AS mbid0
                 , r1.recording_mbid AS mbid1
                 , total_score AS score
              FROM ranked_mbids
              JOIN {metadata_table} r0
                ON id0 = r0.recording_id
              JOIN {metadata_table} r1
                ON id1 = r1.recording_id
             WHERE rank <= {limit}
               AND NOT r0.is_redirect
               AND NOT r1.is_redirect
          ORDER BY mbid0
                 , score DESC
    """


def stage1(metadata_table, output_dir, session, contribution, skip):
    skip_threshold = -skip
    mlhd_df = read_files_from_HDFS(MLHD_PLUS_DATA_DIRECTORY)
    table = "mlhd_recording_similarity_listens"

    for chunk in MLHD_PLUS_CHUNKS:
        logger.info("Processing chunk: %s", chunk)
        mlhd_df.filter(f"user_id LIKE '{chunk}%'").createOrReplaceTempView(table)
        query = build_partial_sessioned_index(table, metadata_table, session, contribution, skip_threshold)
        run_query(query).write.mode("overwrite").parquet(f"{output_dir}/{chunk}")


def stage2(metadata_table, stage1_output_dir, threshold, limit):
    chunks = hdfs_connection.client.list(stage1_output_dir)
    chunks_path = [f"{config.HDFS_CLUSTER_URI}{stage1_output_dir}/{chunk}" for chunk in chunks]
    chunks_table = "mlhd_partial_agg_chunks"
    listenbrainz_spark.session.read.parquet(*chunks_path).createOrReplaceTempView(chunks_table)

    query = build_full_sessioned_index(chunks_table, metadata_table, threshold, limit)
    return run_query(query)


def main(session, contribution, threshold, limit, skip, only_stage2, is_production_dataset):
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
        only_stage2: use existing mlhd processed intermediate chunks
        is_production_dataset: only determines how the dataset is stored in ListenBrainz database.
    """
    metadata_table = "recording_length"
    read_files_from_HDFS(RECORDING_LENGTH_DATAFRAME).createOrReplaceTempView(metadata_table)

    stage1_output_dir = "/mlhd-session-output"
    if not only_stage2:
        run_query("SET spark.sql.shuffle.partitions = 2000").collect()
        stage1(metadata_table, stage1_output_dir, session, contribution, skip)
    data = stage2(metadata_table, stage1_output_dir, threshold, limit)

    algorithm = f"session_based_mlhd_session_{session}_contribution_{contribution}_threshold_{threshold}_limit_{limit}_skip_{skip}"

    if is_production_dataset:
        yield {
            "type": "mlhd_similarity_recording_start",
            "algorithm": algorithm,
            "is_production_dataset": is_production_dataset
        }

    for entries in chunked(data, RECORDINGS_PER_MESSAGE):
        items = [row.asDict() for row in entries]
        yield {
            "type": "mlhd_similarity_recording",
            "algorithm": algorithm,
            "data": items,
            "is_production_dataset": is_production_dataset
        }

    if is_production_dataset:
        yield {
            "type": "mlhd_similarity_recording_end",
            "algorithm": algorithm,
            "is_production_dataset": is_production_dataset
        }

