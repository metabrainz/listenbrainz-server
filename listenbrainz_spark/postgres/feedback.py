from listenbrainz_spark.path import RECORDING_FEEDBACK_DATAFRAME
from listenbrainz_spark.postgres.utils import save_lb_table_to_hdfs


def create_feedback_cache():
    query = """
        SELECT user_id
             , recording_mbid
             , score AS feedback
          FROM recording_feedback   
    """
    save_lb_table_to_hdfs(query, RECORDING_FEEDBACK_DATAFRAME)
