from data.postgres.feedback import get_feedback_cache_query
from listenbrainz_spark.path import RECORDING_FEEDBACK_DATAFRAME
from listenbrainz_spark.postgres.utils import save_lb_table_to_hdfs


def create_feedback_cache():
    query = get_feedback_cache_query()
    save_lb_table_to_hdfs(query, RECORDING_FEEDBACK_DATAFRAME)
