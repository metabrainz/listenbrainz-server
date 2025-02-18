from listenbrainz_spark import config
from listenbrainz_spark.path import DELETED_LISTENS_SAVE_PATH
from listenbrainz_spark.postgres.utils import load_from_db


def main():
    """ Import deleted listens from  """
    query = "SELECT id, user_id, listened_at, recording_msid, listen_created AS created FROM listen_delete_metadata WHERE deleted"
    listens_to_delete_df = load_from_db(config.TS_JDBC_URI, config.TS_USER, config.TS_PASSWORD, query)
    listens_to_delete_df \
        .repartition(1) \
        .write \
        .mode("append") \
        .parquet(DELETED_LISTENS_SAVE_PATH)
