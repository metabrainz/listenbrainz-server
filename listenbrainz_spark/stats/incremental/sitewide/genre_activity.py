from typing import Iterator, Dict

from pyspark.sql import DataFrame

import listenbrainz_spark
from listenbrainz_spark.stats.incremental.message_creator import SitewideStatsMessageCreator
from listenbrainz_spark.stats.incremental.range_selector import ListenRangeSelector
from listenbrainz_spark.stats.incremental.sitewide.entity import SitewideStatsQueryProvider


class GenreActivitySitewideStatsQuery(SitewideStatsQueryProvider):
    """ See base class QueryProvider for details. """

    def __init__(self, selector: ListenRangeSelector):
        super().__init__(selector)
        self.setup_time_brackets()

    @property
    def entity(self):
        return "genre_trend"

    def setup_time_brackets(self):
        """ Generate a dataframe containing time brackets for genre analysis. """
        time_brackets = ['00-06', '06-12', '12-18', '18-24']
        time_brackets_df = listenbrainz_spark.session.createDataFrame(
            [(bracket,) for bracket in time_brackets], 
            schema=["time_bracket"]
        )
        time_brackets_df.createOrReplaceTempView("time_brackets")

    def get_aggregate_query(self, table):
        return f"""
            WITH genre_listens AS (
                SELECT g.genre
                     , CASE
                           WHEN HOUR(l.listened_at) < 6 THEN '00-06'
                           WHEN HOUR(l.listened_at) < 12 THEN '06-12'
                           WHEN HOUR(l.listened_at) < 18 THEN '12-18'
                           ELSE '18-24'
                       END AS time_bracket
                     , COUNT(*) AS listen_count
                  FROM {table} l
                  LEFT JOIN genres g ON l.recording_mbid = g.recording_mbid
                 WHERE g.genre IS NOT NULL
              GROUP BY g.genre
                     , time_bracket
            )
            SELECT genre
                 , time_bracket
                 , listen_count
              FROM genre_listens
        """

    def get_combine_aggregates_query(self, existing_aggregate, incremental_aggregate):
        return f"""
            WITH intermediate_table AS (
                SELECT genre
                     , time_bracket
                     , listen_count
                  FROM {existing_aggregate}
                 UNION ALL
                SELECT genre
                     , time_bracket
                     , listen_count
                  FROM {incremental_aggregate}
            )
                SELECT genre
                     , time_bracket
                     , sum(listen_count) as listen_count
                  FROM intermediate_table
              GROUP BY genre
                     , time_bracket
        """

    def get_stats_query(self, final_aggregate):
        return f"""
            WITH all_genre_time_combinations AS (
                SELECT DISTINCT genre, time_bracket
                  FROM {final_aggregate}
                 CROSS JOIN time_brackets
            )
            SELECT sort_array(
                      collect_list(
                           struct(
                                 genre
                               , time_bracket
                               , COALESCE(fa.listen_count, 0) AS listen_count
                           )
                       )
                   ) AS genre_trend
              FROM all_genre_time_combinations agtc
         LEFT JOIN {final_aggregate} fa
                ON agtc.genre = fa.genre 
               AND agtc.time_bracket = fa.time_bracket
        """


class GenreActivitySitewideMessageCreator(SitewideStatsMessageCreator):

    def __init__(self, selector, database=None):
        super().__init__("genre_trend", "sitewide_genre_trend", selector, database)

    def create_messages(self, results: DataFrame, only_inc: bool) -> Iterator[Dict]:
        message = {
            "type": self.message_type,
            "stats_range": self.stats_range,
            "from_ts": int(self.from_date.timestamp()),
            "to_ts": int(self.to_date.timestamp())
        }
        data = results.collect()[0]
        _dict = data.asDict(recursive=True)
        message["data"] = _dict["genre_trend"]
        yield message