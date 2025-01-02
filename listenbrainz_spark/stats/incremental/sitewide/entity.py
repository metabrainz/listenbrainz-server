import abc
import logging
from datetime import datetime
from pathlib import Path
from typing import List

from pyspark.errors import AnalysisException
from pyspark.sql import DataFrame
from pyspark.sql.types import StructType, StructField, TimestampType

import listenbrainz_spark
from listenbrainz_spark import hdfs_connection
from listenbrainz_spark.config import HDFS_CLUSTER_URI
from listenbrainz_spark.path import INCREMENTAL_DUMPS_SAVE_PATH, \
    LISTENBRAINZ_SITEWIDE_STATS_AGG_DIRECTORY, LISTENBRAINZ_SITEWIDE_STATS_BOOKKEEPING_DIRECTORY
from listenbrainz_spark.stats import SITEWIDE_STATS_ENTITY_LIMIT
from listenbrainz_spark.utils import read_files_from_HDFS, get_listens_from_dump


logger = logging.getLogger(__name__)
BOOKKEEPING_SCHEMA = StructType([
    StructField('from_date', TimestampType(), nullable=False),
    StructField('to_date', TimestampType(), nullable=False),
    StructField('created', TimestampType(), nullable=False),
])


class SitewideEntity(abc.ABC):
    
    def __init__(self, entity):
        self.entity = entity
    
    def get_existing_aggregate_path(self, stats_range) -> str:
        return f"{LISTENBRAINZ_SITEWIDE_STATS_AGG_DIRECTORY}/{self.entity}/{stats_range}"

    def get_bookkeeping_path(self, stats_range) -> str:
        return f"{LISTENBRAINZ_SITEWIDE_STATS_BOOKKEEPING_DIRECTORY}/{self.entity}/{stats_range}"

    def get_listen_count_limit(self, stats_range: str) -> int:
        """ Return the per user per entity listen count above which it should
        be capped. The rationale is to avoid a single user's listens from
        over-influencing the sitewide stats.

        For instance: if the limit for yearly recordings count is 500 and a user
        listens to a particular recording for 10000 times, it will be counted as
        500 for calculating the stat.
        """
        return 500

    def get_partial_aggregate_schema(self) -> StructType:
        raise NotImplementedError()

    def aggregate(self, table, cache_tables, user_listen_count_limit) -> DataFrame:
        raise NotImplementedError()

    def combine_aggregates(self, existing_aggregate, incremental_aggregate) -> DataFrame:
        raise NotImplementedError()

    def get_top_n(self, final_aggregate, N) -> DataFrame:
        raise NotImplementedError()

    def get_cache_tables(self) -> List[str]:
        raise NotImplementedError()

    def generate_stats(self, stats_range: str, from_date: datetime,
                       to_date: datetime, top_entity_limit: int = SITEWIDE_STATS_ENTITY_LIMIT):
        user_listen_count_limit = self.get_listen_count_limit(stats_range)

        cache_tables = []
        for idx, df_path in enumerate(self.get_cache_tables()):
            df_name = f"entity_data_cache_{idx}"
            cache_tables.append(df_name)
            read_files_from_HDFS(df_path).createOrReplaceTempView(df_name)

        metadata_path = self.get_bookkeeping_path(stats_range)
        try:
            metadata = listenbrainz_spark \
                .session \
                .read \
                .schema(BOOKKEEPING_SCHEMA) \
                .json(f"{HDFS_CLUSTER_URI}{metadata_path}") \
                .collect()[0]
            existing_from_date, existing_to_date = metadata["from_date"], metadata["to_date"]
            existing_aggregate_usable = existing_from_date.date() == from_date.date()
        except AnalysisException:
            existing_aggregate_usable = False
            logger.info("Existing partial aggregate not found!")

        prefix = f"sitewide_{self.entity}_{stats_range}"
        existing_aggregate_path = self.get_existing_aggregate_path(stats_range)

        if not hdfs_connection.client.status(existing_aggregate_path, strict=False) or not existing_aggregate_usable:
            table = f"{prefix}_full_listens"
            get_listens_from_dump(from_date, to_date, include_incremental=False).createOrReplaceTempView(table)

            logger.info("Creating partial aggregate from full dump listens")
            hdfs_connection.client.makedirs(Path(existing_aggregate_path).parent)
            full_df = self.aggregate(table, cache_tables, user_listen_count_limit)
            full_df.write.mode("overwrite").parquet(existing_aggregate_path)

            hdfs_connection.client.makedirs(Path(metadata_path).parent)
            metadata_df = listenbrainz_spark.session.createDataFrame(
                [(from_date, to_date, datetime.now())],
                schema=BOOKKEEPING_SCHEMA
            )
            metadata_df.write.mode("overwrite").json(metadata_path)

        full_df = read_files_from_HDFS(existing_aggregate_path)

        if hdfs_connection.client.status(INCREMENTAL_DUMPS_SAVE_PATH, strict=False):
            table = f"{prefix}_incremental_listens"
            read_files_from_HDFS(INCREMENTAL_DUMPS_SAVE_PATH) \
                .createOrReplaceTempView(table)
            inc_df = self.aggregate(table, cache_tables, user_listen_count_limit)
        else:
            inc_df = listenbrainz_spark.session.createDataFrame([], schema=self.get_partial_aggregate_schema())

        full_table = f"{prefix}_existing_aggregate"
        full_df.createOrReplaceTempView(full_table)

        inc_table = f"{prefix}_incremental_aggregate"
        inc_df.createOrReplaceTempView(inc_table)

        combined_df = self.combine_aggregates(full_table, inc_table)
        
        combined_table = f"{prefix}_combined_aggregate"
        combined_df.createOrReplaceTempView(combined_table)
        results_df = self.get_top_n(combined_table, top_entity_limit)

        return results_df.toLocalIterator()
    