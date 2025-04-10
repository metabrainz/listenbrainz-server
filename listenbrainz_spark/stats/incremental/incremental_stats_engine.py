import logging
from datetime import datetime
from pathlib import Path
from typing import Iterator, Dict

from pyspark.sql import DataFrame
from pyspark.errors import AnalysisException

import listenbrainz_spark
from listenbrainz_spark import hdfs_connection
from listenbrainz_spark.config import HDFS_CLUSTER_URI
from listenbrainz_spark.listens.cache import get_incremental_listens_df
from listenbrainz_spark.listens.metadata import get_listens_metadata
from listenbrainz_spark.schema import BOOKKEEPING_SCHEMA, INCREMENTAL_BOOKKEEPING_SCHEMA
from listenbrainz_spark.stats import run_query
from listenbrainz_spark.stats.incremental.message_creator import MessageCreator
from listenbrainz_spark.stats.incremental.query_provider import QueryProvider
from listenbrainz_spark.utils import read_files_from_HDFS
from listenbrainz_spark.listens.data import get_listens_from_dump, filter_listens_by_range, filter_deleted_listens, \
    incremental_listens_exist

logger = logging.getLogger(__name__)


class IncrementalStatsEngine:
    """
    Provides a framework for generating incremental statistics for a given entity (e.g., users, tracks)
    over a specified date range.

    In the ListenBrainz Spark cluster, full dump listens (which remain constant for ~15 days) and incremental listens
    (ingested daily) are the two main sources of data. Incremental listens are cleared whenever a new full dump is
    imported. Aggregating full dump listens daily for various statistics is inefficient since this data does not
    change.

    To optimize this process:

    1. A partial aggregate is generated from the full dump listens the first time a stat is requested. This partial
       aggregate is stored in HDFS for future use, eliminating the need for redundant full dump aggregation.
    2. Incremental listens are aggregated daily. Although all incremental listens since the full dump’s import are
       used (not just today’s), this introduces some redundant computation.
    3. The incremental aggregate is combined with the existing partial aggregate, forming a combined aggregate from
       which final statistics are generated.

    For non-sitewide statistics, further optimization is possible:

        If an entity’s listens (e.g., for a user) are not present in the incremental listens, its statistics do not
        need to be recalculated. Similarly, entity-level listener stats can skip recomputation when relevant data
        is absent in incremental listens.
    """

    def __init__(self, provider: QueryProvider, message_creator: MessageCreator):
        self.provider = provider
        self.message_creator = message_creator
        self._only_inc = None
        self._final_table = None
        self.incremental_table = None

    @property
    def only_inc(self):
        if self._only_inc is None:
            raise Exception("only_inc is not initialized, call generate_stats first.")
        return self._only_inc

    def partial_aggregate_usable(self) -> bool:
        """ Checks whether a partial aggregate exists and is fresh to generate the required stats. """
        metadata_path = f"{self.provider.get_bookkeeping_path()}/full"
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
        except (AnalysisException, IndexError):
            existing_aggregate_fresh = False

        existing_aggregate_exists = hdfs_connection.client.status(existing_aggregate_path, strict=False)

        return existing_aggregate_fresh and existing_aggregate_exists

    def create_partial_aggregate(self) -> DataFrame:
        """
        Create a new partial aggregate from full dump listens.

        Returns:
            DataFrame: The generated partial aggregate DataFrame.
        """
        metadata_path = f"{self.provider.get_bookkeeping_path()}/full"
        existing_aggregate_path = self.provider.get_existing_aggregate_path()

        table = f"{self.provider.get_table_prefix()}_full_listens"
        get_listens_from_dump(
            self.provider.from_date,
            self.provider.to_date,
            include_incremental=False,
            remove_deleted=True
        ).createOrReplaceTempView(table)

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

    def create_incremental_aggregate(self) -> DataFrame:
        """
        Create an incremental aggregate from incremental listens.

        Returns:
            DataFrame: The generated incremental aggregate DataFrame.
        """
        self.incremental_table = f"{self.provider.get_table_prefix()}_incremental_listens"

        inc_listens_df = get_incremental_listens_df()
        inc_listens_df = filter_listens_by_range(inc_listens_df, self.provider.from_date, self.provider.to_date)
        inc_listens_df = filter_deleted_listens(inc_listens_df, get_listens_metadata().location)
        inc_listens_df.createOrReplaceTempView(self.incremental_table)

        inc_query = self.provider.get_aggregate_query(self.incremental_table)
        return run_query(inc_query)

    def bookkeep_incremental_aggregate(self):
        metadata_path = f"{self.provider.get_bookkeeping_path()}/incremental"
        query = f"SELECT max(created) AS latest_created_at FROM {self.incremental_table}"
        latest_created_at = run_query(query).collect()[0]["latest_created_at"]
        metadata_df = listenbrainz_spark.session.createDataFrame(
            [(latest_created_at, datetime.now())],
            schema=INCREMENTAL_BOOKKEEPING_SCHEMA
        )
        metadata_df.write.mode("overwrite").json(metadata_path)

    def get_incremental_dumps_existing_created(self):
        metadata_path = f"{self.provider.get_bookkeeping_path()}/incremental"
        try:
            metadata = listenbrainz_spark \
                .session \
                .read \
                .schema(INCREMENTAL_BOOKKEEPING_SCHEMA) \
                .json(f"{HDFS_CLUSTER_URI}{metadata_path}") \
                .collect()[0]
            return metadata["created"]
        except AnalysisException:
            return None

    def prepare_final_aggregate(self):
        prefix = self.provider.get_table_prefix()

        if self.provider.force_partial_aggregate() or not self.partial_aggregate_usable():
            self.create_partial_aggregate()
            self._only_inc = False
        else:
            self._only_inc = True

        partial_df = read_files_from_HDFS(self.provider.get_existing_aggregate_path())
        partial_table = f"{prefix}_existing_aggregate"
        partial_df.createOrReplaceTempView(partial_table)

        if incremental_listens_exist():
            inc_df = self.create_incremental_aggregate()
            inc_table = f"{prefix}_incremental_aggregate"
            inc_df.createOrReplaceTempView(inc_table)

            if self._only_inc:
                existing_created = self.get_incremental_dumps_existing_created()

                filter_existing_query = self.provider.get_filter_aggregate_query(
                    partial_table,
                    self.incremental_table,
                    existing_created
                )
                filtered_existing_aggregate_df = run_query(filter_existing_query)
                filtered_existing_table = f"{prefix}_filtered_existing_aggregate"
                filtered_existing_aggregate_df.createOrReplaceTempView(filtered_existing_table)

                filter_incremental_query = self.provider.get_filter_aggregate_query(
                    inc_table,
                    self.incremental_table,
                    existing_created
                )
                filtered_incremental_aggregate_df = run_query(filter_incremental_query)
                filtered_incremental_table = f"{prefix}_filtered_incremental_aggregate"
                filtered_incremental_aggregate_df.createOrReplaceTempView(filtered_incremental_table)
            else:
                filtered_existing_table = partial_table
                filtered_incremental_table = inc_table

            final_query = self.provider.get_combine_aggregates_query(filtered_existing_table, filtered_incremental_table)
            final_df = run_query(final_query)
        else:
            final_df = partial_df

        self._final_table = f"{prefix}_final_aggregate"
        final_df.createOrReplaceTempView(self._final_table)

    def generate_stats(self) -> DataFrame:
        results_query = self.provider.get_stats_query(self._final_table)
        results_df = run_query(results_query)
        return results_df

    @staticmethod
    def create_messages(results, only_inc, message_creator) -> Iterator[Dict]:
        if not only_inc:
            message = message_creator.create_start_message()
            if message is not None:
                yield message
        for message in message_creator.create_messages(results, only_inc):
            yield message
        if not only_inc:
            message = message_creator.create_end_message()
            if message is not None:
                yield message

    def run(self) -> Iterator[Dict]:
        self.prepare_final_aggregate()
        results = self.generate_stats()
        yield from self.create_messages(results, self.only_inc, self.message_creator)
        if incremental_listens_exist():
            self.bookkeep_incremental_aggregate()
