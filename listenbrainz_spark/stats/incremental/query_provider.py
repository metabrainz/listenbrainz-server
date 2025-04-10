import abc
from datetime import datetime
from typing import List, Optional

from listenbrainz_spark.stats.incremental.range_selector import ListenRangeSelector


class QueryProvider(abc.ABC):
    """ Base class for providing SQL queries and paths for aggregation. """

    def __init__(self, selector: ListenRangeSelector):
        """
        Args:
            selector: ListenRangeSelector to provide dates and stats range for listens to choose stat from
        """
        self.stats_range, self.from_date, self.to_date = selector.get_dates()

    @property
    @abc.abstractmethod
    def entity(self):
        """ The entity for which statistics are generated. """
        raise NotImplementedError()

    @abc.abstractmethod
    def get_table_prefix(self) -> str:
        """ Get the prefix for table names based on the stat type, entity and stats range. """
        raise NotImplementedError()

    @abc.abstractmethod
    def get_base_path(self) -> str:
        """ Returns the base HDFS path for storing partial data and metadata for this category of statistics. """
        raise NotImplementedError()

    def get_existing_aggregate_path(self) -> str:
        """ Returns the HDFS path for existing aggregate data. """
        return f"{self.get_base_path()}/aggregates/{self.entity}/{self.stats_range}"

    def get_bookkeeping_path(self) -> str:
        """ Returns the HDFS path for bookkeeping metadata directory. """
        return f"{self.get_base_path()}/bookkeeping/{self.entity}/{self.stats_range}"

    @abc.abstractmethod
    def get_aggregate_query(self, table: str) -> str:
        """
        Returns the query to create (partial) aggregates from the given listens.

        Args:
            table: The listen table to aggregation.
        """
        raise NotImplementedError()

    @abc.abstractmethod
    def get_combine_aggregates_query(self, existing_aggregate: str, incremental_aggregate: str) -> str:
        """
        Returns the query to combine existing aggregate and incremental aggregate to get the final
        aggregate to obtain stats from.

        Args:
            existing_aggregate: The table name for existing aggregate.
            incremental_aggregate: The table name for incremental aggregate.
        """
        raise NotImplementedError()

    @abc.abstractmethod
    def get_filter_aggregate_query(self, aggregate: str, inc_listens_table: str, existing_created: datetime) -> str:
        """
        Return the query to filter the aggregate based on the listens submitted since existing created timestamp.

        Args:
            aggregate: The table name for the aggregate to filter
            inc_listens_table: The table name for incremental listens.
            existing_created: The max listen created value last time incremental stats for this query was run.
        """
        raise NotImplementedError()

    @abc.abstractmethod
    def get_stats_query(self, final_aggregate: str) -> str:
        """ Return the query to generate final statistics from final aggregate. """
        raise NotImplementedError()

    def force_partial_aggregate(self):
        """ Returns True if the partial aggregate should be recreated regardless of the existence
        of an existing partial aggregate.
        """
        return False
