from typing import List

from listenbrainz_spark.postgres.artist import get_artist_country_cache
from listenbrainz_spark.stats.incremental.range_selector import ListenRangeSelector
from listenbrainz_spark.stats.incremental.user.entity import UserEntityStatsQueryProvider


class ArtistUserEntity(UserEntityStatsQueryProvider):
    """ See base class QueryProvider for details. """

    def __init__(self, selector: ListenRangeSelector, top_entity_limit: int):
        super().__init__(selector=selector, top_entity_limit=top_entity_limit)

    @property
    def entity(self):
        return "artists"

    def get_aggregate_query(self, table):
        cache_table = get_artist_country_cache()
        return f"""
            WITH exploded_listens AS (
                SELECT user_id
                     , artist_name AS artist_credit_name
                     , explode_outer(artist_credit_mbids) AS artist_mbid
                 FROM {table}
            ), listens_with_mb_data as (
                SELECT user_id
                     , COALESCE(at.artist_name, el.artist_credit_name) AS artist_name
                     , el.artist_mbid
                  FROM exploded_listens el
             LEFT JOIN {cache_table} at
                    ON el.artist_mbid = at.artist_mbid
            )
                SELECT user_id
                -- we group by lower(artist_name) and pick the first artist name for cases where
                -- the artist name differs in case. for mapped listens the artist name from MB will
                -- be used. for unmapped listens we can't know which case is correct so use any. note
                -- that due to presence of artist mbid as the third group, mapped and unmapped listens
                -- will always be separately grouped therefore first will work fine for unmapped
                -- listens and doesn't matter for mapped ones.
                     , first(artist_name) AS artist_name
                     , artist_mbid
                     , count(*) AS listen_count
                 FROM listens_with_mb_data
             GROUP BY user_id
                    , lower(artist_name)
                    , artist_mbid
        """

    def get_combine_aggregates_query(self, existing_aggregate, incremental_aggregate):
        return f"""
            WITH intermediate_table AS (
                SELECT user_id
                     , artist_name
                     , artist_mbid
                     , listen_count
                  FROM {existing_aggregate}
                 UNION ALL
                SELECT user_id
                     , artist_name
                     , artist_mbid
                     , listen_count
                  FROM {incremental_aggregate}
            )
                SELECT user_id
                     , first(artist_name) AS artist_name
                     , artist_mbid
                     , sum(listen_count) as listen_count
                  FROM intermediate_table
              GROUP BY user_id
                     , lower(artist_name)
                     , artist_mbid
        """

    def get_stats_query(self, final_aggregate):
        return f"""
            WITH entity_count AS (
                SELECT user_id
                     , count(*) AS artists_count
                  FROM {final_aggregate}
              GROUP BY user_id
            ), ranked_stats AS (
                SELECT user_id
                     , artist_name
                     , artist_mbid
                     , listen_count
                     , row_number() OVER (PARTITION BY user_id ORDER BY listen_count DESC) AS rank
                  FROM {final_aggregate}
            ), grouped_stats AS (
                SELECT user_id
                     , sort_array(
                            collect_list(
                                struct(
                                    listen_count
                                  , artist_name
                                  , artist_mbid
                                )
                            )
                            , false
                       ) as artists
                  FROM ranked_stats
                 WHERE rank <= {self.top_entity_limit}
              GROUP BY user_id
            )
                SELECT user_id
                     , artists_count
                     , artists
                  FROM grouped_stats
                  JOIN entity_count
                 USING (user_id)
        """
