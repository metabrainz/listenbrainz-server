from typing import List

from listenbrainz_spark.postgres.release import get_release_metadata_cache
from listenbrainz_spark.stats.incremental.sitewide.entity import SitewideEntityStatsQueryProvider


class ReleaseSitewideEntity(SitewideEntityStatsQueryProvider):
    """ See base class QueryProvider for details. """

    @property
    def entity(self):
        return "releases"

    def get_aggregate_query(self, table):
        user_listen_count_limit = self.get_listen_count_limit()
        rel_cache_table = get_release_metadata_cache()
        return f"""
           WITH gather_release_data AS (
                SELECT user_id
                     , l.release_mbid
                     , COALESCE(rel.release_name, l.release_name) AS release_name
                     , COALESCE(rel.album_artist_name, l.artist_name) AS release_artist_name
                     , COALESCE(rel.artist_credit_mbids, l.artist_credit_mbids) AS artist_credit_mbids
                     , rel.caa_id
                     , rel.caa_release_mbid
                  FROM {table} l
             LEFT JOIN {rel_cache_table} rel
                    ON rel.release_mbid = l.release_mbid
            ), user_counts AS (
                SELECT user_id
                     , first(release_name) AS any_release_name
                     , release_mbid
                     , first(release_artist_name) AS any_artist_name
                     , artist_credit_mbids
                     , caa_id
                     , caa_release_mbid
                     , LEAST(count(*), {user_listen_count_limit}) as listen_count
                  FROM gather_release_data
                 WHERE release_name != ''
                   AND release_name IS NOT NULL
              GROUP BY user_id
                     , lower(release_name)
                     , release_mbid
                     , lower(release_artist_name)
                     , artist_credit_mbids
                     , caa_id
                     , caa_release_mbid
            )
                SELECT first(any_release_name) AS release_name
                     , release_mbid
                     , first(any_artist_name) AS artist_name
                     , artist_credit_mbids
                     , caa_id
                     , caa_release_mbid
                     , SUM(listen_count) as listen_count
                  FROM user_counts
              GROUP BY lower(any_release_name)
                     , release_mbid
                     , lower(any_artist_name)
                     , artist_credit_mbids
                     , caa_id
                     , caa_release_mbid
        """

    def get_combine_aggregates_query(self, existing_aggregate, incremental_aggregate):
        return f"""
            WITH intermediate_table AS (
                SELECT release_name
                     , release_mbid
                     , artist_name
                     , artist_credit_mbids
                     , caa_id
                     , caa_release_mbid
                     , listen_count
                  FROM {existing_aggregate}
                 UNION ALL
                SELECT release_name
                     , release_mbid
                     , artist_name
                     , artist_credit_mbids
                     , caa_id
                     , caa_release_mbid
                     , listen_count
                  FROM {incremental_aggregate}
            )
                SELECT first(release_name) AS release_name
                     , release_mbid
                     , first(artist_name) AS artist_name
                     , artist_credit_mbids
                     , caa_id
                     , caa_release_mbid
                     , sum(listen_count) as listen_count
                  FROM intermediate_table
              GROUP BY lower(release_name)
                     , release_mbid
                     , lower(artist_name)
                     , artist_credit_mbids
                     , caa_id
                     , caa_release_mbid
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
                                  , release_name
                                  , release_mbid
                                  , artist_name
                                  , coalesce(artist_credit_mbids, array()) AS artist_mbids
                                  , caa_id
                                  , caa_release_mbid
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
