import abc
from datetime import datetime
from pathlib import Path
from typing import List

from pyspark.errors import AnalysisException
from pyspark.sql import DataFrame
from pyspark.sql.types import StructType

import listenbrainz_spark
from listenbrainz_spark import hdfs_connection
from listenbrainz_spark.config import HDFS_CLUSTER_URI
from listenbrainz_spark.path import INCREMENTAL_DUMPS_SAVE_PATH
from listenbrainz_spark.schema import BOOKKEEPING_SCHEMA
from listenbrainz_spark.stats import get_dates_for_stats_range
from listenbrainz_spark.utils import read_files_from_HDFS, logger, get_listens_from_dump


class IncrementalStats(abc.ABC):
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

    def __init__(self, entity: str, stats_range: str):
        """
        Args:
            entity: The entity for which statistics are generated.
            stats_range: The statistics range to calculate the stats for.
        """
        self.entity = entity
        self.stats_range = stats_range
        self.from_date, self.to_date = get_dates_for_stats_range(stats_range)
        self._cache_tables = []

    @abc.abstractmethod
    def get_base_path(self) -> str:
        """ Returns the base HDFS path for storing partial data and metadata for this category of statistics. """
        raise NotImplementedError()

    def get_existing_aggregate_path(self) -> str:
        """ Returns the HDFS path for existing aggregate data. """
        return f"{self.get_base_path()}/aggregates/{self.entity}/{self.stats_range}"

    def get_bookkeeping_path(self) -> str:
        """ Returns the HDFS path for bookkeeping metadata. """
        return f"{self.get_base_path()}/bookkeeping/{self.entity}/{self.stats_range}"

    @abc.abstractmethod
    def get_partial_aggregate_schema(self) -> StructType:
        """ Returns the spark schema of the partial aggregates created during generation of this stat. """
        raise NotImplementedError()

    @abc.abstractmethod
    def aggregate(self, table: str, cache_tables: List[str]) -> DataFrame:
        """
        Create partial aggregates from the given listens.

        Args:
            table: The listen table to aggregation.
            cache_tables: List of metadata cache tables.

        Returns:
            DataFrame: The aggregated DataFrame.
        """
        raise NotImplementedError()

    @abc.abstractmethod
    def combine_aggregates(self, existing_aggregate: str, incremental_aggregate: str) -> DataFrame:
        """
        Combines existing aggregate and incremental aggregate to get the final aggregate to obtain stats from.

        Args:
            existing_aggregate: The table name for existing aggregate.
            incremental_aggregate: The table name for incremental aggregate.

        Returns:
            DataFrame: The combined DataFrame.
        """
        raise NotImplementedError()

    @abc.abstractmethod
    def get_top_n(self, final_aggregate: str, N: int) -> DataFrame:
        """
        Obtain the top N entities for the given statistic from the final aggregate.

        Args:
            final_aggregate: The table name for the final aggregate.
            N: The number of top entities to retrieve.

        Returns:
            DataFrame: The DataFrame containing the top N entities.
        """
        raise NotImplementedError()

    @abc.abstractmethod
    def get_cache_tables(self) -> List[str]:
        """ Returns the list of HDFS paths for the metadata cache tables required by the statistic. """
        raise NotImplementedError()

    def setup_cache_tables(self):
        """ Set up metadata cache tables by reading data from HDFS and creating temporary views. """
        cache_tables = []
        for idx, df_path in enumerate(self.get_cache_tables()):
            df_name = f"entity_data_cache_{idx}"
            cache_tables.append(df_name)
            read_files_from_HDFS(df_path).createOrReplaceTempView(df_name)
        self._cache_tables = cache_tables

    @abc.abstractmethod
    def get_table_prefix(self) -> str:
        """ Get the prefix for table names based on the stat type, entity and stats range. """
        raise NotImplementedError()

    def partial_aggregate_usable(self) -> bool:
        """ Checks whether a partial aggregate exists and is fresh to generate the required stats. """
        metadata_path = self.get_bookkeeping_path()
        existing_aggregate_path = self.get_existing_aggregate_path()

        try:
            metadata = listenbrainz_spark \
                .session \
                .read \
                .schema(BOOKKEEPING_SCHEMA) \
                .json(f"{HDFS_CLUSTER_URI}{metadata_path}") \
                .collect()[0]
            existing_from_date, existing_to_date = metadata["from_date"], metadata["to_date"]
            existing_aggregate_fresh = existing_from_date.date() == self.from_date.date()
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
        metadata_path = self.get_bookkeeping_path()
        existing_aggregate_path = self.get_existing_aggregate_path()

        table = f"{self.get_table_prefix()}_full_listens"
        get_listens_from_dump(self.from_date, self.to_date, include_incremental=False).createOrReplaceTempView(table)

        logger.info("Creating partial aggregate from full dump listens")
        hdfs_connection.client.makedirs(Path(existing_aggregate_path).parent)
        full_df = self.aggregate(table, self._cache_tables)
        full_df.write.mode("overwrite").parquet(existing_aggregate_path)

        hdfs_connection.client.makedirs(Path(metadata_path).parent)
        metadata_df = listenbrainz_spark.session.createDataFrame(
            [(self.from_date, self.to_date, datetime.now())],
            schema=BOOKKEEPING_SCHEMA
        )
        metadata_df.write.mode("overwrite").json(metadata_path)
        logger.info("Finished creating partial aggregate from full dump listens")

        return full_df

    def incremental_dump_exists(self) -> bool:
        return hdfs_connection.client.status(INCREMENTAL_DUMPS_SAVE_PATH, strict=False)

    def create_incremental_aggregate(self) -> DataFrame:
        """
        Create an incremental aggregate from incremental listens.

        Returns:
            DataFrame: The generated incremental aggregate DataFrame.
        """
        table = f"{self.get_table_prefix()}_incremental_listens"
        read_files_from_HDFS(INCREMENTAL_DUMPS_SAVE_PATH) \
            .createOrReplaceTempView(table)
        return self.aggregate(table, self._cache_tables)
