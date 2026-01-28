from typing import List

from listenbrainz_spark.postgres.release import get_release_metadata_cache
from listenbrainz_spark.stats.incremental.user.entity import UserEntityStatsQueryProvider


class ReleaseUserEntity(UserEntityStatsQueryProvider):
    """ See base class QueryProvider for details. """

    @property
    def entity(self):
        return "releases"

    def get_aggregate_query(self, table):
        cache_table = get_release_metadata_cache()
        return f"""
            WITH gather_release_data AS (
                SELECT user_id
                     , nullif(l.release_mbid, '') AS any_release_mbid
                     , COALESCE(rel.release_name, l.release_name) AS any_release_name
                     , COALESCE(rel.album_artist_name, l.artist_name) AS release_artist_name
                     , COALESCE(rel.artist_credit_mbids, l.artist_credit_mbids) AS artist_credit_mbids
                     , rel.artists
                     , rel.caa_id
                     , rel.caa_release_mbid
                  FROM {table} l
             LEFT JOIN {cache_table} rel
                    ON rel.release_mbid = l.release_mbid
            )
               SELECT user_id
                    , first(any_release_name) AS release_name
                    , any_release_mbid AS release_mbid
                    , first(release_artist_name) AS artist_name
                    , artist_credit_mbids
                    , artists
                    , caa_id
                    , caa_release_mbid
                    , count(*) as listen_count
                 FROM gather_release_data
                WHERE any_release_name != ''
                  AND any_release_name IS NOT NULL
             GROUP BY user_id
                    , lower(any_release_name)
                    , any_release_mbid
                    , lower(release_artist_name)
                    , artist_credit_mbids
                    , artists
                    , caa_id
                    , caa_release_mbid
        """

    def get_combine_aggregates_query(self, existing_aggregate, incremental_aggregate):
        return f"""
            WITH intermediate_table AS (
                SELECT user_id
                     , release_name
                     , release_mbid
                     , artist_name
                     , artist_credit_mbids
                     , artists
                     , caa_id
                     , caa_release_mbid
                     , listen_count
                  FROM {existing_aggregate}
                 UNION ALL
                SELECT user_id
                     , release_name
                     , release_mbid
                     , artist_name
                     , artist_credit_mbids
                     , artists
                     , caa_id
                     , caa_release_mbid
                     , listen_count
                  FROM {incremental_aggregate}
            )
                SELECT user_id
                     , first(release_name) AS release_name
                     , release_mbid
                     , first(artist_name) AS artist_name
                     , artist_credit_mbids
                     , artists
                     , caa_id
                     , caa_release_mbid
                     , sum(listen_count) as listen_count
                  FROM intermediate_table
              GROUP BY user_id
                     , lower(release_name)
                     , release_mbid
                     , lower(artist_name)
                     , artist_credit_mbids
                     , artists
                     , caa_id
                     , caa_release_mbid
        """

    def get_stats_query(self, final_aggregate):
        return f"""
            WITH entity_count AS (
                SELECT user_id
                     , count(*) AS releases_count
                  FROM {final_aggregate}
              GROUP BY user_id
            ), ranked_stats AS (
                SELECT user_id
                     , release_name
                     , release_mbid
                     , artist_name
                     , artist_credit_mbids
                     , artists
                     , caa_id
                     , caa_release_mbid
                     , listen_count
                     , row_number() OVER (PARTITION BY user_id ORDER BY listen_count DESC) AS rank
                  FROM {final_aggregate}
            ), grouped_stats AS (
                SELECT user_id
                     , sort_array(
                            collect_list(
                                struct(
                                    listen_count
                                  , release_name
                                  , release_mbid
                                  , artist_name
                                  , coalesce(artist_credit_mbids, array()) AS artist_mbids
                                  , artists
                                  , caa_id
                                  , caa_release_mbid
                                )
                            )
                            , false
                       ) as releases
                  FROM ranked_stats
                 WHERE rank <= {self.top_entity_limit}
              GROUP BY user_id
            )
                SELECT user_id
                     , releases_count
                     , releases
                  FROM grouped_stats
                  JOIN entity_count
                 USING (user_id)
        """
