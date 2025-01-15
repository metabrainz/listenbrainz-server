import abc
from datetime import datetime
from typing import Tuple

from listenbrainz_spark.stats import get_dates_for_stats_range
from listenbrainz_spark.stats.common.listening_activity import get_time_range_bounds


class ListenRangeSelector(abc.ABC):

    @abc.abstractmethod
    def get_dates(self) -> Tuple[str, datetime, datetime]:
        raise NotImplementedError()


class StatsRangeListenRangeSelector(ListenRangeSelector):

    def __init__(self, stats_range):
        self.stats_range = stats_range
        self.from_date, self.to_date = get_dates_for_stats_range(stats_range)

    def get_dates(self) -> Tuple[str, datetime, datetime]:
        return self.stats_range, self.from_date, self.to_date


class FromToRangeListenRangeSelector(ListenRangeSelector):

    def __init__(self, from_date: datetime, to_date: datetime):
        self.from_date = from_date
        self.to_date = to_date
        self.stats_range = f"custom_{from_date.today().strftime('%Y%m%d')}_{to_date.today().strftime('%Y%m%d')}"

    def get_dates(self) -> Tuple[str, datetime, datetime]:
        return self.stats_range, self.from_date, self.to_date


class ListeningActivityListenRangeSelector(ListenRangeSelector):

    def __init__(self, stats_range: str, year: int = None):
        self.year = year
        self.stats_range = stats_range
        self.from_date, self.to_date, self.step, self.date_format, self.spark_date_format = get_time_range_bounds(
            self.stats_range,
            year
        )

    def get_dates(self) -> Tuple[str, datetime, datetime]:
        return self.stats_range, self.from_date, self.to_date
