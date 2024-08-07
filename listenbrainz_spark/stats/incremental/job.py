import logging
import uuid
from datetime import datetime
from pathlib import Path

from pyspark import Row
from pyspark.sql import DataFrame

from listenbrainz_spark.exceptions import PathNotFoundException
from listenbrainz_spark.hdfs import path_exists, create_dir, rename, delete_dir
from listenbrainz_spark.path import INTERMEDIATE_STATS_JOB_PARQUET
from listenbrainz_spark.schema import intermediate_stats_job_schema
from listenbrainz_spark.utils import create_dataframe, read_files_from_HDFS

logger = logging.getLogger(__name__)

def save_parquet(df, dest_path):
    tmp_path = f"/{uuid.uuid4()}"
    df.write.parquet(tmp_path)

    if path_exists(dest_path):
        delete_dir(dest_path, recursive=True)

    dest_path_parent = str(Path(dest_path).parent)
    create_dir(dest_path_parent)
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
            .filter(incremental_stats_job_df.range == stats_range) \
            .filter(incremental_stats_job_df.ended_at.isNotlNull())

        jobs = incremental_stats_job_df.collect()
        if len(jobs) > 0:
            return jobs[0]
    except PathNotFoundException:
        logger.info("Intermediate job stats records file not found.")
    return None
