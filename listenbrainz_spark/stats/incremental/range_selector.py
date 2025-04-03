import abc
from datetime import datetime
from typing import Tuple

from listenbrainz_spark.stats import get_dates_for_stats_range
from listenbrainz_spark.stats.common.listening_activity import get_time_range_bounds


class ListenRangeSelector(abc.ABC):
    """ Abstract class to choose timeframe of listens to use for a particular job """

    @abc.abstractmethod
    def get_dates(self) -> Tuple[str, datetime, datetime]:
        """ Returns the name of the stats range, and start date and end date to select listens """
        raise NotImplementedError()


class StatsRangeListenRangeSelector(ListenRangeSelector):
    """ Selector that chooses start and end date based on the given stats range """

    def __init__(self, stats_range):
        self.stats_range = stats_range
        self.from_date, self.to_date = get_dates_for_stats_range(stats_range)

    def get_dates(self) -> Tuple[str, datetime, datetime]:
        return self.stats_range, self.from_date, self.to_date


class FromToRangeListenRangeSelector(ListenRangeSelector):
    """ Selector which uses the provided start and end data as is """

    def __init__(self, from_date: datetime, to_date: datetime):
        self.from_date = from_date
        self.to_date = to_date
        self.stats_range = f"custom_{from_date.today().strftime('%Y%m%d')}_{to_date.today().strftime('%Y%m%d')}"

    def get_dates(self) -> Tuple[str, datetime, datetime]:
        return self.stats_range, self.from_date, self.to_date


class ListeningActivityListenRangeSelector(ListenRangeSelector):
    """ Selector to use for listening activity stats. """

    def __init__(self, stats_range: str, year: int = None):
        self.year = year
        self.stats_range = stats_range
        self.from_date, self.to_date, self.step, self.date_format, self.spark_date_format = get_time_range_bounds(
            self.stats_range,
            year
        )

    def get_dates(self) -> Tuple[str, datetime, datetime]:
        return self.stats_range, self.from_date, self.to_date
