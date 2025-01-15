import logging
from datetime import datetime
from pathlib import Path
from typing import Tuple, Iterator, Dict

from pandas import DataFrame
from pyspark.errors import AnalysisException

import listenbrainz_spark
from listenbrainz_spark import hdfs_connection
from listenbrainz_spark.config import HDFS_CLUSTER_URI
from listenbrainz_spark.path import INCREMENTAL_DUMPS_SAVE_PATH
from listenbrainz_spark.schema import BOOKKEEPING_SCHEMA
from listenbrainz_spark.stats import run_query
from listenbrainz_spark.stats.incremental.message_creator import MessageCreator
from listenbrainz_spark.stats.incremental.provider import Provider
from listenbrainz_spark.utils import read_files_from_HDFS, get_listens_from_dump

logger = logging.getLogger(__name__)


class Aggregator:

    def __init__(self, provider: Provider, message_creator: MessageCreator):
        self.provider = provider
        self.message_creator = message_creator
        self._cache_tables = []
        self._only_inc = None

    @property
    def only_inc(self):
        if self._only_inc is None:
            raise Exception("only_inc is not initialized, call generate_stats first.")
        return self._only_inc

    def _setup_cache_tables(self):
        """ Set up metadata cache tables by reading data from HDFS and creating temporary views. """
        cache_tables = []
        for idx, df_path in enumerate(self.provider.get_cache_tables()):
            df_name = f"entity_data_cache_{idx}"
            cache_tables.append(df_name)
            read_files_from_HDFS(df_path).createOrReplaceTempView(df_name)
        self._cache_tables = cache_tables

    def partial_aggregate_usable(self) -> bool:
        """ Checks whether a partial aggregate exists and is fresh to generate the required stats. """
        metadata_path = self.provider.get_bookkeeping_path()
        existing_aggregate_path = self.provider.get_existing_aggregate_path()

        try:
            metadata = listenbrainz_spark \
                .session \
                .read \
                .schema(BOOKKEEPING_SCHEMA) \
                .json(f"{HDFS_CLUSTER_URI}{metadata_path}") \
                .collect()[0]
            existing_from_date, existing_to_date = metadata["from_date"], metadata["to_date"]
            existing_aggregate_fresh = existing_from_date.date() == self.provider.from_date.date() \
                and existing_to_date.date() <= self.provider.to_date.date()
        except AnalysisException:
            existing_aggregate_fresh = False

        existing_aggregate_exists = hdfs_connection.client.status(existing_aggregate_path, strict=False)

        return existing_aggregate_fresh and existing_aggregate_exists

    def create_partial_aggregate(self) -> DataFrame:
        """
        Create a new partial aggregate from full dump listens.

        Returns:
            DataFrame: The generated partial aggregate DataFrame.
        """
        metadata_path = self.provider.get_bookkeeping_path()
        existing_aggregate_path = self.provider.get_existing_aggregate_path()

        table = f"{self.provider.get_table_prefix()}_full_listens"
        get_listens_from_dump(self.provider.from_date, self.provider.to_date, include_incremental=False) \
            .createOrReplaceTempView(table)

        logger.info("Creating partial aggregate from full dump listens")
        hdfs_connection.client.makedirs(Path(existing_aggregate_path).parent)
        full_query = self.provider.get_aggregate_query(table, self._cache_tables)
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

    def incremental_dump_exists(self) -> bool:
        """ Check if incremental listen dumps exist """
        return hdfs_connection.client.status(INCREMENTAL_DUMPS_SAVE_PATH, strict=False)

    def create_incremental_aggregate(self) -> DataFrame:
        """
        Create an incremental aggregate from incremental listens.

        Returns:
            DataFrame: The generated incremental aggregate DataFrame.
        """
        table = f"{self.provider.get_table_prefix()}_incremental_listens"
        read_files_from_HDFS(INCREMENTAL_DUMPS_SAVE_PATH) \
            .createOrReplaceTempView(table)
        inc_query = self.provider.get_aggregate_query(table, self._cache_tables)
        return run_query(inc_query)

    def generate_stats(self) -> DataFrame:
        self._setup_cache_tables()
        prefix = self.provider.get_table_prefix()

        if self.provider.force_partial_aggregate() or not self.partial_aggregate_usable():
            self.create_partial_aggregate()
            self._only_inc = False
        else:
            self._only_inc = True

        partial_df = read_files_from_HDFS(self.provider.get_existing_aggregate_path())
        partial_table = f"{prefix}_existing_aggregate"
        partial_df.createOrReplaceTempView(partial_table)

        if self.incremental_dump_exists():
            inc_df = self.create_incremental_aggregate()
            inc_table = f"{prefix}_incremental_aggregate"
            inc_df.createOrReplaceTempView(inc_table)

            if self._only_inc:
                filter_query = self.provider.get_filter_aggregate_query(partial_table, inc_table)
                filtered_aggregate_df = run_query(filter_query)
                filtered_table = f"{prefix}_filtered_aggregate"
                filtered_aggregate_df.createOrReplaceTempView(filtered_table)
            else:
                filtered_table = partial_table

            final_query = self.provider.get_combine_aggregates_query(filtered_table, inc_table)
            final_df = run_query(final_query)
        else:
            final_df = partial_df
            self._only_inc = False

        final_table = f"{prefix}_final_aggregate"
        final_df.createOrReplaceTempView(final_table)

        results_query = self.provider.get_stats_query(final_table)
        results_df = run_query(results_query)
        return results_df

    def main(self) -> Iterator[Dict]:
        results = self.generate_stats()
        if not self.only_inc:
            yield self.message_creator.create_start_message()
        for message in self.message_creator.create_messages(results):
            yield message
        if not self.only_inc:
            yield self.message_creator.create_end_message()
