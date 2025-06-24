from typing import Iterator, Dict

from pyspark.sql import DataFrame

import listenbrainz_spark
from listenbrainz_spark.stats.incremental.message_creator import SitewideStatsMessageCreator
from listenbrainz_spark.stats.incremental.range_selector import ListenRangeSelector
from listenbrainz_spark.stats.incremental.sitewide.entity import SitewideStatsQueryProvider

from listenbrainz_spark.utils import read_files_from_HDFS
from listenbrainz_spark.path import RECORDING_RECORDING_GENRE_DATAFRAME

class GenreActivitySitewideStatsQuery(SitewideStatsQueryProvider):
    """ See base class QueryProvider for details. """

    def __init__(self, selector: ListenRangeSelector):
        super().__init__(selector)
        self.setup_time_brackets()

    @property
    def entity(self):
        return "genre_activity"

    def setup_time_brackets(self):
        """ Generate a dataframe containing hourly time brackets for genre analysis. """
        time_brackets = [f"{hour:02d}" for hour in range(24)]
        time_brackets_df = listenbrainz_spark.session.createDataFrame(
            [(bracket,) for bracket in time_brackets], 
            schema=["time_bracket"]
        )
        time_brackets_df.createOrReplaceTempView("time_brackets")

    def get_aggregate_query(self, table):
        genres_df = read_files_from_HDFS(RECORDING_RECORDING_GENRE_DATAFRAME)
        genres_df.createOrReplaceTempView("genres")
        return f"""
            WITH genre_listens AS (
                SELECT g.genre
                     , LPAD(HOUR(l.listened_at), 2, '0') AS time_bracket
                     , COUNT(*) AS listen_count
                  FROM {table} l
                  LEFT JOIN genres g ON l.recording_mbid = g.recording_mbid
                 WHERE g.genre IS NOT NULL
              GROUP BY g.genre
                     , time_bracket
                     , LPAD(HOUR(l.listened_at), 2, '0')
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
			WITH ranked_genres AS (
				SELECT 
					genre,
					time_bracket,
					listen_count,
					ROW_NUMBER() OVER (
						PARTITION BY time_bracket 
						ORDER BY listen_count DESC
					) AS rank
				FROM {final_aggregate}
			),
			top_genres AS (
				SELECT genre, time_bracket, listen_count
				FROM ranked_genres
				WHERE rank <= 10
			),
			all_genre_time_combinations AS (
				SELECT DISTINCT 
                	tg.genre, 
                    tg.time_bracket
				FROM top_genres tg
			)
			SELECT sort_array(
					collect_list(
						struct(
							agtc.genre,
							agtc.time_bracket,
							COALESCE(tg.listen_count, 0) AS listen_count
						)
					)
				) AS genre_activity
			FROM all_genre_time_combinations agtc
			LEFT JOIN top_genres tg
			ON agtc.genre = tg.genre
			AND agtc.time_bracket = tg.time_bracket
		"""

class GenreActivitySitewideMessageCreator(SitewideStatsMessageCreator):

    def __init__(self, selector, database=None):
        super().__init__("genre_activity", "sitewide_genre_activity", selector, database)

    def create_messages(self, results: DataFrame, only_inc: bool) -> Iterator[Dict]:
        message = {
            "type": self.message_type,
            "stats_range": self.stats_range,
            "from_ts": int(self.from_date.timestamp()),
            "to_ts": int(self.to_date.timestamp())
        }
        data = results.collect()[0]
        _dict = data.asDict(recursive=True)
        message["data"] = _dict["genre_activity"]
        yield message