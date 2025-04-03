from datetime import datetime
from typing import List

from listenbrainz_spark.postgres.artist import get_artist_country_cache
from listenbrainz_spark.stats.incremental.listener.entity import EntityListenerStatsQueryProvider


class ArtistEntityListenerStatsQuery(EntityListenerStatsQueryProvider):
    """ See base class QueryProvider for details. """

    @property
    def entity(self):
        return "artists"

    def get_aggregate_query(self, table):
        cache_table = get_artist_country_cache()
        return f"""
            WITH exploded_listens AS (
                SELECT user_id
                     , explode_outer(artist_credit_mbids) AS artist_mbid
                  FROM {table}
            ), listens_with_mb_data as (
                SELECT user_id
                     , artist_mbid
                     , at.artist_name
                  FROM exploded_listens el
                  JOIN {cache_table} at
                 USING (artist_mbid)
            )
                SELECT artist_mbid
                     , artist_name
                     , user_id
                     , count(*) AS listen_count
                  FROM listens_with_mb_data
              GROUP BY artist_mbid
                     , artist_name
                     , user_id
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
                SELECT artist_mbid
                     , artist_name
                     , user_id
                     , sum(listen_count) as listen_count
                  FROM intermediate_table
              GROUP BY artist_mbid
                     , artist_name
                     , user_id
        """

    def get_stats_query(self, final_aggregate):
        return f"""
            WITH entity_count as (
                SELECT artist_mbid
                     , SUM(listen_count) as total_listen_count
                     , COUNT(DISTINCT user_id) as total_user_count
                  FROM {final_aggregate}
              GROUP BY artist_mbid
            ), ranked_stats as (
                SELECT artist_mbid
                     , artist_name
                     , user_id
                     , listen_count
                     , row_number() OVER (PARTITION BY artist_mbid ORDER BY listen_count DESC) AS rank
                  FROM {final_aggregate}
            ), grouped_stats AS (
                SELECT artist_mbid
                     , artist_name
                     , sort_array(
                            collect_list(
                                struct(
                                    listen_count
                                  , user_id
                                )
                            )
                            , false
                       ) as listeners
                  FROM ranked_stats
                 WHERE rank < {self.top_entity_limit}
              GROUP BY artist_mbid
                     , artist_name
            )
                SELECT artist_mbid
                     , artist_name
                     , listeners
                     , total_listen_count
                     , total_user_count
                  FROM grouped_stats
                  JOIN entity_count
                 USING (artist_mbid)
        """

    def get_filter_aggregate_query(self, aggregate: str, inc_listens_table: str, existing_created: datetime) -> str:
        return f"""
            WITH exploded_listens AS (
                SELECT explode_outer(artist_credit_mbids) AS artist_mbid
                  FROM {inc_listens_table}
                 WHERE created >= to_timestamp('{existing_created}')
            ), incremental_artists AS (
                SELECT DISTINCT artist_mbid
                  FROM exploded_listens
            )
                SELECT *
                  FROM {aggregate} ea
                 WHERE EXISTS(SELECT 1 FROM incremental_artists ia WHERE ia.artist_mbid = ea.artist_mbid)
        """
