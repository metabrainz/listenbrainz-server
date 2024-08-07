from listenbrainz_spark.path import RELEASE_GROUP_METADATA_CACHE_DATAFRAME, \
    RELEASE_METADATA_CACHE_DATAFRAME
from listenbrainz_spark.stats import run_query
from listenbrainz_spark.stats.incremental import Entity, save_parquet, end_job


class ReleaseGroup(Entity):

    def get_stats_from_listens(self, listen_table: str):
        rel_cache_table = self.get_cache_tables()[0]
        rg_cache_table = self.get_cache_tables()[1]
        return run_query(f"""
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
                  FROM {listen_table} l
             LEFT JOIN parquet.`{rel_cache_table}` rel
                    ON rel.release_mbid = l.release_mbid
             LEFT JOIN parquet.`{rg_cache_table}` rg
                    ON rg.release_group_mbid = rel.release_group_mbid
            ), intermediate_table as (
                SELECT user_id
                     , first(release_group_name) AS any_release_group_name
                     , release_group_mbid
                     , first(release_group_artist_name) AS any_artist_name
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
            )
                SELECT user_id
                     , any_release_group_name AS release_group_name
                     , release_group_mbid
                     , any_artist_name AS artist_name
                     , artist_credit_mbids
                     , caa_id
                     , caa_release_mbid
                     , artists
                     , listen_count
                  FROM intermediate_table
        """)

    def combine_existing_and_new_stats(self, existing_table: str, new_table: str):
        return run_query(f"""
            SELECT COALESCE(n.user_id, e.user_id) AS user_id
                 , COALESCE(n.release_group_name, e.release_group_name) AS release_group_name
                 , COALESCE(n.release_group_mbid, e.release_mbid) AS release_group_mbid
                 , COALESCE(n.artist_name, e.artist_name) AS artist_name
                 , COALESCE(n.artist_credit_mbids, e.artist_credit_mbids) AS artist_credit_mbids
                 , COALESCE(n.artists, e.artists) AS artists
                 , COALESCE(n.caa_id, e.caa_id) AS caa_id
                 , COALESCE(n.caa_release_mbid, e.caa_release_mbid) AS caa_release_mbid
                 , COALESCE(e.listen_count, 0) AS old_listen_count
                 , COALESCE(n.listen_count, 0) + COALESCE(e.listen_count, 0) AS new_listen_count
              FROM {existing_table} AS e
         FULL JOIN {new_table} n
                ON n.user_id = e.user_id
               AND n.release_group_name = e.release_group_name
               AND n.release_group_mbid = e.release_group_mbid
               AND n.artist_name = e.artist_name
               AND n.artist_credit_mbids = e.artist_credit_mbids
               AND n.artists = e.artists
               AND n.caa_id = e.caa_id
               AND n.caa_release_mbid = e.caa_release_mbid
        """)

    def filter_top_full(self, table: str, k: int):
        return run_query(f"""
              WITH intermediate AS (
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
                  FROM {table}
              )
                SELECT user_id
                     , sort_array(
                            collect_list(
                                struct(
                                    listen_count
                                  , release_group_name
                                  , release_group_mbid
                                  , artist_name
                                  , coalesce(artist_credit_mbids, array()) AS artist_mbids
                                  , caa_id
                                  , caa_release_mbid
                                  , artists
                                )
                            )
                            , false
                       ) as artists
                  FROM intermediate
                 WHERE rank <= {k}
              GROUP BY user_id
        """)

    def filter_top_incremental(self, incremental_listens_table: str, combined_stats_table: str, k: int):
        return run_query(f"""
            WITH users_with_changes AS (
                SELECT DISTINCT user_id
                  FROM {incremental_listens_table}  
            ), filtered_entity_stats AS (
                SELECT user_id
                     , release_group_name
                     , release_group_mbid
                     , artist_name
                     , artist_credit_mbids
                     , artists
                     , caa_id
                     , caa_release_mbid
                     , old_listen_count
                     , new_listen_count
                     , RANK() over (PARTITION BY user_id ORDER BY new_listen_count DESC) AS rank
                  FROM {combined_stats_table} c
                 WHERE c.user_id IN (SELECT user_id FROM users_with_changes)
            )   SELECT user_id
                     , sort_array(
                        collect_list(
                            struct(
                                new_listen_count AS listen_count
                              , release_group_name
                              , release_group_mbid
                              , artist_name
                              , coalesce(artist_credit_mbids, array()) AS artist_mbids
                              , caa_id
                              , caa_release_mbid
                              , artists
                            )
                        )
                        , false
                     ) as release_groups
                FROM filtered_entity_stats
               WHERE rank <= {k}
            GROUP BY user_id
              HAVING ANY(new_listen_count != old_listen_count)
        """)

    def post_process_incremental(self, type_, entity, stats_range, combined_entity_table, stats_aggregation_path):
        new_stats_df = run_query(f"""
            SELECT user_id
                 , release_group_name
                 , release_group_mbid
                 , artist_name
                 , artist_credit_mbids
                 , caa_id
                 , caa_release_mbid
                 , artists
                 , new_listen_count AS listen_count
              FROM {combined_entity_table}
        """)
        save_parquet(new_stats_df, stats_aggregation_path)
        end_job(type_, entity, stats_range)

    def get_cache_tables(self):
        return [RELEASE_METADATA_CACHE_DATAFRAME, RELEASE_GROUP_METADATA_CACHE_DATAFRAME]
