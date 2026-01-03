
import logging
from typing import Iterator, Dict

from pyspark.sql import DataFrame

import listenbrainz_spark
from listenbrainz_spark.stats.incremental.message_creator import SitewideStatsMessageCreator
from listenbrainz_spark.stats.incremental.range_selector import ListenRangeSelector, StatsRangeListenRangeSelector
from listenbrainz_spark.stats.incremental.sitewide.entity import SitewideStatsQueryProvider
from listenbrainz_spark.utils import read_files_from_HDFS
from listenbrainz_spark.path import RECORDING_ARTIST_DATAFRAME

logger = logging.getLogger(__name__)


class ArtistEvolutionActivitySitewideStatsQuery(SitewideStatsQueryProvider):
    """ Sitewide stats query provider for artist evolution - aggregates artist listening patterns by time units across all users. """

    def __init__(self, selector: ListenRangeSelector):
        super().__init__(selector)
        self.stats_range = selector.stats_range

    @property
    def entity(self):
        return "artist_evolution_activity"

    def _get_time_field_expression(self):
        """Get the appropriate time field expression based on stats range."""
        if self.stats_range in ("week", "this_week"):
            return "date_format(listened_at, 'EEEE')"
        if self.stats_range in ("month", "this_month"):
            return "day(listened_at)"
        if self.stats_range in ("year", "this_year", "quarter", "half_yearly"):
            return "date_format(listened_at, 'MMMM')"
        else:
            return "year(listened_at)"

    def get_aggregate_query(self, table):
        # Load recording artist metadata and create temp view
        recording_df = read_files_from_HDFS(RECORDING_ARTIST_DATAFRAME)
        recording_df.createOrReplaceTempView("recording_artist")
        
        time_field = self._get_time_field_expression()
        return f"""
            SELECT {time_field} AS time_unit
                 , artist_element.artist_mbid AS artist_mbid
                 , artist_element.artist_credit_name AS artist_name
                 , COUNT(*) AS listen_count
              FROM {table} l
              JOIN recording_artist ra ON l.recording_mbid = ra.recording_mbid
            LATERAL VIEW explode(ra.artists) AS artist_element
          GROUP BY {time_field}
                 , artist_element.artist_mbid
                 , artist_element.artist_credit_name
        """

    def get_combine_aggregates_query(self, existing_aggregate, incremental_aggregate):
        return f"""
            WITH intermediate_table AS (
                SELECT time_unit
                     , artist_mbid
                     , artist_name
                     , listen_count
                  FROM {existing_aggregate}
                 UNION ALL
                SELECT time_unit
                     , artist_mbid
                     , artist_name
                     , listen_count
                  FROM {incremental_aggregate}
            )
                SELECT time_unit
                     , artist_mbid
                     , artist_name
                     , sum(listen_count) as listen_count
                  FROM intermediate_table
              GROUP BY time_unit
                     , artist_mbid
                     , artist_name
        """

    def get_stats_query(self, final_aggregate):
        return f"""
             SELECT sort_array(
                       collect_list(
                            struct(
                                  time_unit
                                , artist_mbid
                                , artist_name
                                , listen_count
                            )
                        ), false
                    ) AS artist_evolution_activity
               FROM {final_aggregate}
        """


class ArtistEvolutionActivitySitewideMessageCreator(SitewideStatsMessageCreator):
    """ Message creator for sitewide artist evolution stats. """

    def __init__(self, selector: StatsRangeListenRangeSelector, database=None):
        super().__init__("artist_evolution_activity", "sitewide_artist_evolution_activity", selector, database)

    @property
    def default_database_prefix(self):
        return f"{self.entity}_{self.stats_range}"

    def create_messages(self, results: DataFrame, only_inc: bool) -> Iterator[Dict]:

        message = {
            "type": self.message_type,
            "stats_range": self.stats_range,
            "from_ts": int(self.from_date.timestamp()),
            "to_ts": int(self.to_date.timestamp())
        }
        
        # Collect the results and extract the artist evolution data
        data = results.collect()[0]
        _dict = data.asDict(recursive=True)
        message["data"] = _dict["artist_evolution_activity"]
        
        logger.info("Created sitewide artist evolution message for range %s with %d artist-time entries", 
                   self.stats_range, len(message["data"]))
        
        yield message
