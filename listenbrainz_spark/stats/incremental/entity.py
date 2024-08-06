import logging
import os.path
import uuid
from datetime import datetime
from typing import List, Iterator, Optional, Dict

from more_itertools import chunked
from pyspark.sql import Row, DataFrame

from listenbrainz_spark.exceptions import PathNotFoundException
from listenbrainz_spark.hdfs import path_exists, delete_dir, rename
from listenbrainz_spark.path import ARTIST_COUNTRY_CODE_DATAFRAME, INTERMEDIATE_STATS_JOB_PARQUET, \
    LISTENBRAINZ_EXPERIMENTAL_STATS_DIR, INCREMENTAL_DUMPS_SAVE_PATH
from listenbrainz_spark.schema import intermediate_stats_job_schema
from listenbrainz_spark.stats import run_query, get_dates_for_stats_range
from listenbrainz_spark.stats.user import USERS_PER_MESSAGE
from listenbrainz_spark.utils import read_files_from_HDFS, create_dataframe, get_listens_from_dump

logger = logging.getLogger(__name__)


def save_parquet(df, dest_path):
    tmp_path = f"/{uuid.uuid4()}"
    df.write.parquet(tmp_path)
    if path_exists(dest_path):
        delete_dir(dest_path, recursive=True)
    rename(tmp_path, dest_path)


def start_job(type_: str, entity: str, stats_range: str, latest_created_at: datetime):
    started_at = datetime.now()
    new_row_df = create_dataframe(Row(
        type=type_,
        entity=entity,
        range=stats_range,
        latest_created_at=latest_created_at,
        started_at=started_at,
        ended_at=None
    ), schema=intermediate_stats_job_schema)
    try:
        incremental_stats_job_df: DataFrame = read_files_from_HDFS(INTERMEDIATE_STATS_JOB_PARQUET)
        incremental_stats_job_df = incremental_stats_job_df \
            .filter(incremental_stats_job_df.type != type_) \
            .filter(incremental_stats_job_df.entity != entity) \
            .filter(incremental_stats_job_df.range != stats_range)
        incremental_stats_job_df = incremental_stats_job_df.union(new_row_df)
    except PathNotFoundException:
        logger.info("Intermediate job stats records file not found, creating...")
        incremental_stats_job_df = new_row_df

    save_parquet(incremental_stats_job_df, INTERMEDIATE_STATS_JOB_PARQUET)


def end_job(type_: str, entity: str, stats_range: str):
    ended_at = datetime.now()
    try:
        incremental_stats_job_df: DataFrame = read_files_from_HDFS(INTERMEDIATE_STATS_JOB_PARQUET)
        job_row_df = incremental_stats_job_df \
            .filter(incremental_stats_job_df.type == type_) \
            .filter(incremental_stats_job_df.entity == entity) \
            .filter(incremental_stats_job_df.range == stats_range)
        jobs = job_row_df.collect()

        if len(jobs) == 0:
            logger.error(f"Intermediate jobs stats records: no entry found for"
                         f" type={type_}, entity={entity} and range={stats_range}")

        job = jobs[0].asDict()
        job["ended_at"] = ended_at

        updated_job = Row(**job)
        updated_job_df = create_dataframe(updated_job, schema=intermediate_stats_job_schema)

        incremental_stats_job_df = incremental_stats_job_df \
            .filter(incremental_stats_job_df.type != type_) \
            .filter(incremental_stats_job_df.entity != entity) \
            .filter(incremental_stats_job_df.range != stats_range)
        incremental_stats_job_df = incremental_stats_job_df.union(updated_job_df)
        save_parquet(incremental_stats_job_df, INTERMEDIATE_STATS_JOB_PARQUET)
    except PathNotFoundException:
        logger.error("Intermediate job stats records file not found.", exc_info=True)


def get_job(type_: str, entity: str, stats_range: str):
    try:
        incremental_stats_job_df: DataFrame = read_files_from_HDFS(INTERMEDIATE_STATS_JOB_PARQUET)
        incremental_stats_job_df = incremental_stats_job_df \
            .filter(incremental_stats_job_df.type == type_) \
            .filter(incremental_stats_job_df.entity == entity) \
            .filter(incremental_stats_job_df.range == stats_range)

        jobs = incremental_stats_job_df.collect()
        if len(jobs) > 0:
            return jobs[0]
    except PathNotFoundException:
        logger.info("Intermediate job stats records file not found.")
    return None


def get_artists_from_listens(table: str, cache_tables: List[str]):
    cache_table = cache_tables[0]
    return run_query(f"""
        WITH exploded_listens AS (
            SELECT user_id
                 , artist_name AS artist_credit_name
                 , explode_outer(artist_credit_mbids) AS artist_mbid
             FROM {table}
        ), listens_with_mb_data as (
            SELECT user_id
                 , COALESCE(at.artist_name, el.artist_credit_name) AS artist_name
                 , el.artist_mbid
              FROM exploded_listens el
         LEFT JOIN {cache_table} at
                ON el.artist_mbid = at.artist_mbid
        ), intermediate_table AS (
            SELECT user_id
                 , first(artist_name) AS any_artist_name
                 , artist_mbid
                 , count(*) AS listen_count
             FROM listens_with_mb_data
         GROUP BY user_id
                , lower(artist_name)
                , artist_mbid    
        )
           SELECT user_id
                , any_artist_name AS artist_name
                , artist_mbid
                , listen_count
             FROM intermediate_table
    """)


def combine_artist_stats(existing_table, new_table):
    return run_query(f"""
        SELECT COALESCE(e.user_id, n.user_id) AS user_id
             , COALESCE(e.artist_mbid, n.artist_mbid) AS artist_mbid
             , COALESCE(e.artist_name, n.artist_name) AS artist_name
             , COALESCE(e.listen_count, 0) AS old_listen_count
             , COALESCE(e.listen_count, 0) + COALESCE(n.listen_count, 0) AS new_listen_count
          FROM parquet.`{existing_table}` AS e
     FULL JOIN parquet.`{new_table}` n
            ON e.user_id = n.user_id
           AND e.artist_mbid = n.artist_mbid
           AND e.artist_name = n.artist_name
    """)


def filter_top_k_artists(table, k):
    return run_query(f"""
          WITH intermediate AS (
            SELECT user_id
                 , artist_name
                 , artist_mbid
                 , listen_count
                 , row_number() OVER (PARTITION BY user_id ORDER BY listen_count DESC) AS rank
              FROM {table}
          )
            SELECT user_id
                 , sort_array(
                        collect_list(
                            struct(
                                listen_count
                              , artist_name
                              , artist_mbid
                            )
                        )
                        , false
                   ) as artists
              FROM intermediate
             WHERE rank <= {k}
          GROUP BY user_id
    """)


def filter_top_k_artists_incremental(incremental_listens_table, combined_artists_table, k):
    return run_query(f"""
        WITH users_with_changes AS (
            SELECT DISTINCT user_id
              FROM {incremental_listens_table}  
        ), filtered_artist_stats AS (
            SELECT user_id
                 , artist_mbid
                 , artist_name
                 , old_listen_count
                 , new_listen_count
                 , RANK() over (PARTITION BY user_id ORDER BY new_listen_count DESC) AS rank
              FROM {combined_artists_table} c
             WHERE c.user_id IN (SELECT user_id FROM users_with_changes)
        )   SELECT user_id
                 , sort_array(
                    collect_list(
                        struct(
                            new_listen_count AS listen_count
                          , artist_name
                          , artist_mbid
                        )
                    )
                    , false
                 ) as artists
            FROM filtered_artist_stats
           WHERE rank <= {k}
        GROUP BY user_id
          HAVING ANY(new_listen_count != old_listen_count)
    """)


def full_process_job(from_date, to_date, type_, entity, stats_range, cache_table, stats_aggregation_path):
    full_listens_table = f"user_{entity}_{stats_range}_full"
    get_listens_from_dump(from_date, to_date).createOrReplaceTempView(full_listens_table)
    latest_created_at = run_query(f"select max(created) as latest_created_at from {full_listens_table}") \
        .collect()[0].latest_created_at
    start_job(type_, entity, stats_range, latest_created_at)

    full_artists_df = get_artists_from_listens(full_listens_table, [cache_table])
    save_parquet(full_artists_df, stats_aggregation_path)

    end_job(type_, entity, stats_range)

    artists_table = f"artists_{entity}_{stats_range}_full"
    full_artists_df.createOrReplaceTempView(artists_table)

    return filter_top_k_artists(artists_table, 1000)


def incremental_process_job(from_date, to_date, previous_job, type_, entity, stats_range, cache_table, stats_aggregation_path):
    existing_artists_table = f"{entity}_{stats_range}_existing"
    read_files_from_HDFS(stats_aggregation_path).createOrReplaceTempView(existing_artists_table)

    incremental_listens_table = f"user_{entity}_{stats_range}_new"
    read_files_from_HDFS(INCREMENTAL_DUMPS_SAVE_PATH) \
        .filter(f"created > to_timestamp('{previous_job['latest_created_at']}') AND listened_at >= to_timestamp('{from_date}') AND listened_at <= to_timestamp('{to_date}'") \
        .createOrReplaceTempView(incremental_listens_table)

    latest_created_at = run_query(f"select max(created) as latest_created_at from {incremental_listens_table}") \
        .collect()[0].latest_created_at
    start_job(type_, entity, stats_range, latest_created_at)

    new_artists_df = get_artists_from_listens(incremental_listens_table, [cache_table])
    new_artists_table = f"{entity}_{stats_range}_new"
    new_artists_df.createOrReplaceTempView(new_artists_table)

    combined_artists_table = f"{entity}_{stats_range}_combined"
    combined_artists_df = combine_artist_stats(existing_artists_table, new_artists_table)
    combined_artists_df.createOrReplaceTempView(combined_artists_table)
    new_stats_df = run_query(f"""
        SELECT user_id
             , artist_mbid
             , artist_name
             , new_listen_count AS listen_count
          FROM {combined_artists_table}
    """)
    save_parquet(new_stats_df, stats_aggregation_path)

    end_job(type_, entity, stats_range)

    return filter_top_k_artists_incremental(incremental_listens_table, combined_artists_table, 1000)


def create_messages(data, entity: str, stats_range: str, from_date: datetime, to_date: datetime,
                    message_type: str, is_full: bool, database: str) \
        -> Iterator[Optional[Dict]]:
    """
    Create messages to send the data to the webserver via RabbitMQ

    Args:
        data: Data to sent to the webserver
        entity: The entity for which statistics are calculated, i.e 'artists',
            'releases' or 'recordings'
        stats_range: The range for which the statistics have been calculated
        from_date: The start time of the stats
        to_date: The end time of the stats
        message_type: used to decide which handler on LB webserver side should
            handle this message. can be "user_entity" or "year_in_music_top_stats"
        database: the name of the database in which the webserver should store the data

    Returns:
        messages: A list of messages to be sent via RabbitMQ
    """
    if database is None:
        database = f"{entity}_{stats_range}"

    if is_full:
        yield {
            "type": "couchdb_data_start",
            "database": database
        }

    from_ts = int(from_date.timestamp())
    to_ts = int(to_date.timestamp())

    for entries in chunked(data, USERS_PER_MESSAGE):
        multiple_user_stats = []
        for entry in entries:
            multiple_user_stats.append(entry.asDict(recursive=True))

        yield {
            "type": message_type,
            "stats_range": stats_range,
            "from_ts": from_ts,
            "to_ts": to_ts,
            "entity": entity,
            "data": multiple_user_stats,
            "database": database
        }

    if is_full:
        yield {
            "type": "couchdb_data_end",
            "database": database
        }


def get_entity_stats(entity: str, stats_range: str, database: str):
    message_type = "entity"
    from_date, to_date = get_dates_for_stats_range(stats_range)
    previous_job = get_job(message_type, entity, stats_range)
    is_full = previous_job is None or previous_job["latest_created_at"] <= from_date

    cache_table = "artist_country_code"
    read_files_from_HDFS(ARTIST_COUNTRY_CODE_DATAFRAME).createOrReplaceTempView(cache_table)

    stats_aggregation_path = os.path.join(LISTENBRAINZ_EXPERIMENTAL_STATS_DIR, message_type, entity, stats_range)

    if is_full:
        top_artists_df = full_process_job(from_date, to_date, message_type, entity, stats_range, cache_table, stats_aggregation_path)
    else:
        top_artists_df = incremental_process_job(from_date, to_date, previous_job, message_type, entity, stats_range, cache_table, stats_aggregation_path)

    top_artists = top_artists_df.toLocalIterator()
    return create_messages(top_artists, entity, stats_range, from_date, to_date, message_type, is_full, database)
