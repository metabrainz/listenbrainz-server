import uuid

from listenbrainz_spark import config, hdfs_connection
from listenbrainz_spark.hdfs.utils import move
from listenbrainz_spark.path import DELETED_LISTENS_SAVE_PATH, DELETED_USER_LISTEN_HISTORY_SAVE_PATH
from listenbrainz_spark.postgres.utils import load_from_db
from listenbrainz_spark.stats import run_query
from listenbrainz_spark.utils import read_files_from_HDFS


def combine_if_exists(new_df, save_path, combine_query_template):
    """ If a dataframe already exists at the save path, load it and combine it with the new dataframe using the provided
    query. Otherwise, save the new dataframe at the save path directly.
    """
    if hdfs_connection.client.status(save_path, strict=False):
        existing_table = f"existing_df_{uuid.uuid4()}"
        new_table = f"new_df_{uuid.uuid4()}"
        existing_df = read_files_from_HDFS(save_path)
        existing_df.createOrReplaceTempView(existing_table)
        new_df.createOrReplaceTempView(new_table)

        query = combine_query_template.format(existing_table=existing_table, new_table=new_table)
        combined_df = run_query(query)

        temp_df_path = f"/tmp/{str(uuid.uuid4())}"
        combined_df \
            .repartition(1) \
            .write \
            .mode("overwrite") \
            .parquet(temp_df_path)

        move(temp_df_path, save_path)
    else:
        new_df \
            .repartition(1) \
            .write \
            .mode("overwrite") \
            .parquet(save_path)


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
    columns = "id, user_id, listened_at, recording_msid, created"
    query = f"""\
        WITH intermediate AS (
            SELECT {columns} FROM {{new_table}}
             UNION ALL
            SELECT {columns} FROM {{existing_table}}
        )
            SELECT {columns} FROM intermediate GROUP BY {columns}
    """
    combine_if_exists(new_listens_to_delete_df, DELETED_LISTENS_SAVE_PATH, query)


def import_deleted_user_listen_history():
    query = """SELECT id, user_id, max_created FROM deleted_user_listen_history"""
    new_deleted_history_df = load_from_db(config.TS_JDBC_URI, config.TS_USER, config.TS_PASSWORD, query)
    query = """\
        WITH intermediate AS (
            SELECT user_id, max_created FROM {new_table}
         UNION ALL
            SELECT user_id, max_created FROM {existing_table}
        )
           SELECT user_id, max(max_created) AS max_created FROM intermediate GROUP BY user_id
    """
    combine_if_exists(new_deleted_history_df, DELETED_USER_LISTEN_HISTORY_SAVE_PATH, query)


def main():
    """ Import deleted listens from timescale """
    import_deleted_listens()
    import_deleted_user_listen_history()
