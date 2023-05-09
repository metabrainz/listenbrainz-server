from listenbrainz_spark.path import RECORDING_LENGTH_DATAFRAME, MLHD_PLUS_DATA_DIRECTORY
from listenbrainz_spark.similarity.recording import build_sessioned_index
from listenbrainz_spark.stats import run_query
from listenbrainz_spark.utils import read_files_from_HDFS


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

    read_files_from_HDFS(MLHD_PLUS_DATA_DIRECTORY).createOrReplaceTempView(table)
    read_files_from_HDFS(RECORDING_LENGTH_DATAFRAME).createOrReplaceTempView(metadata_table)

    skip_threshold = -skip
    query = build_sessioned_index(table, metadata_table, session, contribution, threshold, limit, skip_threshold)
    run_query(query).write.mode("overwrite").parquet("/mlhd-session-output")

    algorithm = f"session_based_mlhd_session_{session}_contribution_{contribution}_threshold_{threshold}_limit_{limit}_skip_{skip}"

    return {
        "type": "similar_recordings_mlhd",
        "algorithm": algorithm
    }
