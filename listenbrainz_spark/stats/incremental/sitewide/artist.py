from typing import List

from listenbrainz_spark.path import ARTIST_COUNTRY_CODE_DATAFRAME
from listenbrainz_spark.stats.incremental.sitewide.entity import SitewideEntityProvider


class AritstSitewideEntity(SitewideEntityProvider):

    def entity(self):
        return "artists"

    def get_cache_tables(self) -> List[str]:
        return [ARTIST_COUNTRY_CODE_DATAFRAME]

    def get_aggregate_query(self, table, cache_tables):
        user_listen_count_limit = self.get_listen_count_limit()
        cache_table = cache_tables[0]
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
            ), user_counts as (
                SELECT user_id
                     , first(artist_name) AS any_artist_name
                     , artist_mbid
                     , LEAST(count(*), {user_listen_count_limit}) as listen_count
                  FROM listens_with_mb_data
              GROUP BY user_id
                     , lower(artist_name)
                     , artist_mbid
            )
                SELECT first(any_artist_name) AS artist_name
                     , artist_mbid
                     , SUM(listen_count) as listen_count
                  FROM user_counts
              GROUP BY lower(any_artist_name)
                     , artist_mbid
        """

    def get_combine_aggregates_query(self, existing_aggregate, incremental_aggregate):
        return f"""
            WITH intermediate_table AS (
                SELECT artist_name
                     , artist_mbid
                     , listen_count
                  FROM {existing_aggregate}
                 UNION ALL
                SELECT artist_name
                     , artist_mbid
                     , listen_count
                  FROM {incremental_aggregate}
            )
                SELECT first(artist_name) AS artist_name
                     , artist_mbid
                     , sum(listen_count) as listen_count
                  FROM intermediate_table
              GROUP BY lower(artist_name)
                     , artist_mbid
        """

    def get_stats_query(self, final_aggregate):
        return f"""
            WITH entity_count AS (
                SELECT count(*) AS total_count
                  FROM {final_aggregate}
            ), ordered_stats AS (
                SELECT *
                  FROM {final_aggregate}
              ORDER BY listen_count DESC
                 LIMIT {self.top_entity_limit}
            ), grouped_stats AS (
                SELECT sort_array(
                            collect_list(
                                struct(
                                    listen_count
                                  , artist_name
                                  , artist_mbid
                                )
                            )
                            , false
                       ) AS stats
                  FROM ordered_stats
            )
                SELECT total_count
                     , stats
                  FROM grouped_stats
                  JOIN entity_count
                    ON TRUE
        """
