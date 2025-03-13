from typing import List

from listenbrainz_spark.postgres.release import get_release_metadata_cache
from listenbrainz_spark.postgres.release_group import get_release_group_metadata_cache
from listenbrainz_spark.stats.incremental.user.entity import UserEntityStatsQueryProvider


class ReleaseGroupUserEntity(UserEntityStatsQueryProvider):
    """ See base class QueryProvider for details. """

    @property
    def entity(self):
        return "release_groups"

    def get_aggregate_query(self, table):
        rel_cache_table = get_release_metadata_cache()
        rg_cache_table = get_release_group_metadata_cache()
        return f"""
            WITH gather_release_data AS (
                SELECT user_id
                     , rg.release_group_mbid
                     -- this is intentional as we don't have a release group name field in listen submission json
                     -- and for the purposes of this stat, they'd usually be the same.
                     , COALESCE(rg.title, l.release_name) AS release_group_name
                     , COALESCE(rg.artist_credit_name, l.artist_name) AS release_group_artist_name
                     , COALESCE(rg.artist_credit_mbids, l.artist_credit_mbids) AS artist_credit_mbids
                     , rg.artists
                     , rg.caa_id
                     , rg.caa_release_mbid
                  FROM {table} l
             LEFT JOIN {rel_cache_table} rel
                    ON rel.release_mbid = l.release_mbid
             LEFT JOIN {rg_cache_table} rg
                    ON rg.release_group_mbid = rel.release_group_mbid
            )
                SELECT user_id
                     , first(release_group_name) AS release_group_name
                     , release_group_mbid
                     , first(release_group_artist_name) AS artist_name
                     , artist_credit_mbids
                     , caa_id
                     , caa_release_mbid
                     , artists
                     , count(*) as listen_count
                  FROM gather_release_data
                 WHERE release_group_name != ''
                   AND release_group_name IS NOT NULL
              GROUP BY user_id
                     , lower(release_group_name)
                     , release_group_mbid
                     , lower(release_group_artist_name)
                     , artist_credit_mbids
                     , caa_id
                     , caa_release_mbid
                     , artists
        """

    def get_combine_aggregates_query(self, existing_aggregate, incremental_aggregate):
        return f"""
            WITH intermediate_table AS (
                SELECT user_id
                     , release_group_name
                     , release_group_mbid
                     , artist_name
                     , artist_credit_mbids
                     , artists
                     , caa_id
                     , caa_release_mbid
                     , listen_count
                  FROM {existing_aggregate}
                 UNION ALL
                SELECT user_id
                     , release_group_name
                     , release_group_mbid
                     , artist_name
                     , artist_credit_mbids
                     , artists
                     , caa_id
                     , caa_release_mbid
                     , listen_count
                  FROM {incremental_aggregate}
            )
                SELECT user_id
                     , first(release_group_name) AS release_group_name
                     , release_group_mbid
                     , first(artist_name) AS artist_name
                     , artist_credit_mbids
                     , artists
                     , caa_id
                     , caa_release_mbid
                     , sum(listen_count) as listen_count
                  FROM intermediate_table
              GROUP BY user_id
                     , lower(release_group_name)
                     , release_group_mbid
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
                     , count(*) AS release_groups_count
                  FROM {final_aggregate}
              GROUP BY user_id
            ), ranked_stats AS (
                SELECT user_id
                     , release_group_name
                     , release_group_mbid
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
                                  , release_group_name
                                  , release_group_mbid
                                  , artist_name
                                  , coalesce(artist_credit_mbids, array()) AS artist_mbids
                                  , artists
                                  , caa_id
                                  , caa_release_mbid
                                )
                            )
                            , false
                       ) as release_groups
                  FROM ranked_stats
                 WHERE rank <= {self.top_entity_limit}
              GROUP BY user_id
            )
                SELECT user_id
                     , release_groups_count
                     , release_groups
                  FROM grouped_stats
                  JOIN entity_count
                 USING (user_id)
        """
