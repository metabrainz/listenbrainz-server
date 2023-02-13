from listenbrainz_spark.path import RECORDING_LENGTH_DATAFRAME
from listenbrainz_spark.postgres.utils import save_pg_table_to_hdfs


def create_recording_length_cache():
    """ Import artist country from postgres to HDFS for use in artist map stats calculation. """
    query = """
        SELECT r.gid AS recording_mbid
             , r.length
          FROM musicbrainz.recording r   
    """

    save_pg_table_to_hdfs(query, RECORDING_LENGTH_DATAFRAME)
