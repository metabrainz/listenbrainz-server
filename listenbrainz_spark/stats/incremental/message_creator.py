import abc
from abc import ABC
from datetime import date
from typing import Iterator, Dict, Optional

from pyspark.sql import DataFrame

from listenbrainz_spark.stats.incremental.range_selector import ListenRangeSelector


class MessageCreator(abc.ABC):
    """ Base class for generating messages for sending to LB server from spark query results """

    def __init__(self, entity: str, message_type: str):
        self.entity = entity
        self.message_type = message_type

    @abc.abstractmethod
    def create_start_message(self):
        """ Generate a message marking the start of data generation. """
        raise NotImplementedError()

    @abc.abstractmethod
    def create_end_message(self):
        """ Generate a message marking the end of data generation. """
        raise NotImplementedError()

    @abc.abstractmethod
    def parse_row(self, row: Dict) -> Optional[Dict]:
        """ Parse one statistic row in a message. """
        raise NotImplementedError()

    @abc.abstractmethod
    def create_messages(self, results: DataFrame, only_inc: bool) -> Iterator[Dict]:
        """ Chunk the query results data into multiple messages for storage in LB server. """
        raise NotImplementedError()


class StatsMessageCreator(MessageCreator, abc.ABC):

    def __init__(self, entity: str, message_type: str, selector: ListenRangeSelector, database: str = None):
        super().__init__(entity, message_type)
        self.selector = selector
        self.stats_range, self.from_date, self.to_date = self.selector.get_dates()
        self.database = database

    @property
    @abc.abstractmethod
    def default_database_prefix(self):
        raise NotImplementedError()

    @property
    def default_database(self):
        return f"{self.default_database_prefix}_{date.today().strftime('%Y%m%d')}"

    def get_database(self):
        return self.database or self.default_database

    def create_start_message(self):
        return {"type": "couchdb_data_start", "database": self.get_database()}

    def create_end_message(self):
        return {"type": "couchdb_data_end", "database": self.get_database()}

    def parse_row(self, row):
        return row


class SitewideStatsMessageCreator(StatsMessageCreator, ABC):

    @property
    def default_database_prefix(self):
        return ""

    def create_start_message(self):
        return None

    def create_end_message(self):
        return None
