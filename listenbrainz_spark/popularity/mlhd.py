import logging
from datetime import datetime
from pathlib import Path

from pyspark.sql import DataFrame

import listenbrainz_spark
from listenbrainz_spark import hdfs_connection
from listenbrainz_spark.path import MLHD_PLUS_DATA_DIRECTORY
from listenbrainz_spark.schema import BOOKKEEPING_SCHEMA
from listenbrainz_spark.stats import run_query
from listenbrainz_spark.stats.incremental.message_creator import MessageCreator
from listenbrainz_spark.stats.incremental.query_provider import QueryProvider
from listenbrainz_spark.utils import read_files_from_HDFS

logger = logging.getLogger(__name__)


class MlhdStatsEngine:

    def __init__(self, provider: QueryProvider, message_creator: MessageCreator):
        self.provider = provider
        self.message_creator = message_creator

    def create_partial_aggregate(self) -> DataFrame:
        metadata_path = self.provider.get_bookkeeping_path()
        existing_aggregate_path = self.provider.get_existing_aggregate_path()

        table = f"{self.provider.get_table_prefix()}_full_listens"
        read_files_from_HDFS(MLHD_PLUS_DATA_DIRECTORY).createOrReplaceTempView(table)

        logger.info("Creating partial aggregate from full dump listens")
        hdfs_connection.client.makedirs(Path(existing_aggregate_path).parent)
        full_query = self.provider.get_aggregate_query(table)
        full_df = run_query(full_query)
        full_df.write.mode("overwrite").parquet(existing_aggregate_path)

        hdfs_connection.client.makedirs(Path(metadata_path).parent)
        metadata_df = listenbrainz_spark.session.createDataFrame(
            [(self.provider.from_date, self.provider.to_date, datetime.now())],
            schema=BOOKKEEPING_SCHEMA
        )
        metadata_df.write.mode("overwrite").json(metadata_path)
        logger.info("Finished creating partial aggregate from full dump listens")

        return full_df

    def generate_stats(self) -> DataFrame:
        prefix = self.provider.get_table_prefix()
        self.create_partial_aggregate()

        partial_df = read_files_from_HDFS(self.provider.get_existing_aggregate_path())
        partial_table = f"{prefix}_existing_aggregate"
        partial_df.createOrReplaceTempView(partial_table)

        results_query = self.provider.get_stats_query(partial_table)
        results_df = run_query(results_query)
        return results_df

    def run(self):
        results = self.generate_stats()
        yield self.message_creator.create_start_message()
        for message in self.message_creator.create_messages(results, False):
            yield message
        yield self.message_creator.create_end_message()
