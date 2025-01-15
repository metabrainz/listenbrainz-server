import abc
from datetime import datetime, date
from typing import Iterator, Dict

from pyspark.sql import DataFrame

from listenbrainz_spark.stats.incremental.range_selector import ListenRangeSelector


class MessageCreator(abc.ABC):

    def __init__(self, entity: str, message_type: str):
        self.entity = entity
        self.message_type = message_type

    @abc.abstractmethod
    def create_start_message(self):
        raise NotImplementedError()

    @abc.abstractmethod
    def create_end_message(self):
        raise NotImplementedError()

    @abc.abstractmethod
    def parse_row(self, row: Dict) -> Dict | None:
        raise NotImplementedError()

    @abc.abstractmethod
    def create_messages(self, results: DataFrame) -> Iterator[Dict]:
        raise NotImplementedError()


class StatsMessageCreator(MessageCreator, abc.ABC):

    def __init__(self, entity: str, message_type: str, selector: ListenRangeSelector, database: str = None):
        super().__init__(entity, message_type)
        self.selector = selector
        self.stats_range, self.from_date, self.to_date = self.selector.get_dates()
        if database:
            self.database = database
        else:
            self.database = f"{self.entity}_{self.stats_range}_{date.today().strftime('%Y%m%d')}"

    def create_start_message(self):
        return {"type": "couchdb_data_start", "database": self.database}

    def create_end_message(self):
        return {"type": "couchdb_data_end", "database": self.database}

    def parse_row(self, row):
        return row
