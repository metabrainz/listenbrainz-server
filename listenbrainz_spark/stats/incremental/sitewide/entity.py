import abc
from pathlib import Path
from typing import List

from pyspark.sql import DataFrame
from pyspark.sql.types import StructType

import listenbrainz_spark
from listenbrainz_spark import hdfs_connection
from listenbrainz_spark.path import INCREMENTAL_DUMPS_SAVE_PATH, LISTENBRAINZ_INTERMEDIATE_STATS_DIRECTORY
from listenbrainz_spark.stats import SITEWIDE_STATS_ENTITY_LIMIT
from listenbrainz_spark.utils import read_files_from_HDFS


class SitewideEntity(abc.ABC):
    
    def __init__(self, entity):
        self.entity = entity
    
    def get_existing_aggregate_path(self, stats_range) -> str:
        return f"/sitewide_stats_aggregates/{self.entity}/{stats_range}"

    def get_partial_aggregate_schema(self) -> StructType:
        raise NotImplementedError()

    def aggregate(self, table, cache_tables, user_listen_count_limit) -> DataFrame:
        raise NotImplementedError()

    def combine_aggregates(self, existing_aggregate, incremental_aggregate) -> DataFrame:
        raise NotImplementedError()

    def get_top_n(self, final_aggregate, N) -> DataFrame:
        raise NotImplementedError()

    def generate_stats(self, stats_range: str, cache_tables: List[str], user_listen_count_limit, top_entity_limit: int = SITEWIDE_STATS_ENTITY_LIMIT):
        prefix = f"sitewide_{self.entity}_{stats_range}"
        existing_aggregate_path = self.get_existing_aggregate_path(stats_range)
        hdfs_connection.client.makedirs(Path(existing_aggregate_path).parent)

        # todo: handle stats ranges
        if not hdfs_connection.client.status(existing_aggregate_path, strict=False):
            table = f"{prefix}_full_listens"
            read_files_from_HDFS(LISTENBRAINZ_INTERMEDIATE_STATS_DIRECTORY) \
                .createOrReplaceTempView(table)
            full_df = self.aggregate(table, cache_tables, user_listen_count_limit)
            full_df.write.mode("overwrite").parquet(existing_aggregate_path)

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
    