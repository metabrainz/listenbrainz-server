import uuid

from listenbrainz_spark import config
from listenbrainz_spark.hdfs.utils import move
from listenbrainz_spark.path import DELETED_LISTENS_SAVE_PATH, DELETED_USER_LISTEN_HISTORY_SAVE_PATH
from listenbrainz_spark.postgres.utils import load_from_db
from listenbrainz_spark.stats import run_query
from listenbrainz_spark.utils import read_files_from_HDFS


def import_deleted_listens():
    query = """
        SELECT id
             , user_id
             , listened_at
             , recording_msid
             , listen_created::timestamp(3) with time zone AS created
          FROM listen_delete_metadata
         WHERE status = 'complete'::listen_delete_metadata_status_enum
    """
    new_listens_to_delete_df = load_from_db(config.TS_JDBC_URI, config.TS_USER, config.TS_PASSWORD, query)
    existing_listens_to_delete_df = read_files_from_HDFS(DELETED_LISTENS_SAVE_PATH)

    new_listens_to_delete_df.createOrReplaceTempView("new_listens_to_delete")
    existing_listens_to_delete_df.createOrReplaceTempView("existing_listens_to_delete")

    columns = "id, user_id, listened_at, recording_msid, created"
    all_listens_to_delete_df = run_query(f"""\
        WITH intermediate AS (
            SELECT {columns} FROM new_listens_to_delete
             UNION ALL
            SELECT {columns} FROM existing_listens_to_delete
        )
            SELECT {columns} FROM intermediate GROUP BY {columns}
    """)

    temp_df_path = f"/tmp/{str(uuid.uuid4())}"
    all_listens_to_delete_df \
        .repartition(1) \
        .write \
        .mode("overwrite") \
        .parquet(temp_df_path)

    move(temp_df_path, DELETED_LISTENS_SAVE_PATH)


def import_deleted_user_listen_history():
    query = """SELECT id, user_id, max_created FROM deleted_user_listen_history"""
    new_deleted_history_df = load_from_db(config.TS_JDBC_URI, config.TS_USER, config.TS_PASSWORD, query)
    existing_deleted_history_df = read_files_from_HDFS(DELETED_USER_LISTEN_HISTORY_SAVE_PATH)

    new_deleted_history_df.createOrReplaceTempView("new_listen_history_to_delete")
    existing_deleted_history_df.createOrReplaceTempView("existing_listen_history_to_delete")

    all_deleted_history_df = run_query("""\
        WITH intermediate AS (
            SELECT user_id, max_created FROM new_listen_history_to_delete
         UNION ALL
            SELECT user_id, max_created FROM existing_listen_history_to_delete
        )
           SELECT user_id, max(max_created) AS max_created FROM intermediate GROUP BY user_id
    """)

    temp_df_path = f"/tmp/{str(uuid.uuid4())}"
    all_deleted_history_df \
        .repartition(1) \
        .write \
        .mode("overwrite") \
        .parquet(temp_df_path)

    move(temp_df_path, DELETED_USER_LISTEN_HISTORY_SAVE_PATH)


def main():
    """ Import deleted listens from timescale """
    import_deleted_listens()
    import_deleted_user_listen_history()
