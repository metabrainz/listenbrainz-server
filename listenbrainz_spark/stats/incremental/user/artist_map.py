from typing import List

from listenbrainz_spark.path import ARTIST_COUNTRY_CODE_DATAFRAME
from listenbrainz_spark.stats.incremental.range_selector import ListenRangeSelector
from listenbrainz_spark.stats.incremental.user.artist import ArtistUserEntity
from listenbrainz_spark.stats.incremental.user.entity import UserEntityStatsQueryProvider


class ArtistMapUserEntity(ArtistUserEntity):
    """ See base class QueryProvider for details. """

    def __init__(self, selector: ListenRangeSelector, top_entity_limit: int):
        super().__init__(selector=selector, top_entity_limit=top_entity_limit)

    def get_stats_query(self, final_aggregate, cache_tables: List[str]):
        cache_table = cache_tables[0]
        return f"""
            WITH ranked_stats AS (
                SELECT user_id
                     , artist_name
                     , artist_mbid
                     , listen_count
                     , row_number() OVER (PARTITION BY user_id ORDER BY listen_count DESC) AS rank
                  FROM {final_aggregate}
            ), ranked_countries AS (
                SELECT user_id
                     , country_code AS country
                     , count(*) as artist_count
                     , sum(listen_count) as listen_count
                     , sort_array(
                            collect_list(
                                struct(
                                    listen_count
                                  , rs.artist_name
                                  , rs.artist_mbid
                                )
                            )
                            , false
                       ) as artists
                  FROM ranked_stats rs
                  JOIN {cache_table}
                 USING (artist_mbid)
                 WHERE rank <= {self.top_entity_limit}
              GROUP BY user_id
                     , country_code
            )
                SELECT user_id
                     , sort_array(
                            collect_list(
                                struct(
                                    artist_count
                                  , listen_count
                                  , country
                                  , artists
                                )
                              , false
                            )
                       ) AS artist_map
                  FROM ranked_countries
              GROUP BY user_id
        """
