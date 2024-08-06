from listenbrainz_spark.path import ARTIST_COUNTRY_CODE_DATAFRAME
from listenbrainz_spark.stats import run_query
from listenbrainz_spark.stats.incremental import Entity


class Artist(Entity):

    def get_stats_from_listens(self, listen_table: str):
        cache_table = self.get_cache_tables()[0]
        return run_query(f"""
            WITH exploded_listens AS (
                SELECT user_id
                     , artist_name AS artist_credit_name
                     , explode_outer(artist_credit_mbids) AS artist_mbid
                 FROM {listen_table}
            ), listens_with_mb_data as (
                SELECT user_id
                     , COALESCE(at.artist_name, el.artist_credit_name) AS artist_name
                     , el.artist_mbid
                  FROM exploded_listens el
             LEFT JOIN {cache_table} at
                    ON el.artist_mbid = at.artist_mbid
            ), intermediate_table AS (
                SELECT user_id
                     , first(artist_name) AS any_artist_name
                     , artist_mbid
                     , count(*) AS listen_count
                 FROM listens_with_mb_data
             GROUP BY user_id
                    , lower(artist_name)
                    , artist_mbid    
            )
               SELECT user_id
                    , any_artist_name AS artist_name
                    , artist_mbid
                    , listen_count
                 FROM intermediate_table
        """)

    def combine_existing_and_new_stats(self, existing_table: str, new_table: str):
        return run_query(f"""
            SELECT COALESCE(e.user_id, n.user_id) AS user_id
                 , COALESCE(e.artist_mbid, n.artist_mbid) AS artist_mbid
                 , COALESCE(e.artist_name, n.artist_name) AS artist_name
                 , COALESCE(e.listen_count, 0) AS old_listen_count
                 , COALESCE(e.listen_count, 0) + COALESCE(n.listen_count, 0) AS new_listen_count
              FROM {existing_table} AS e
         FULL JOIN {new_table} n
                ON e.user_id = n.user_id
               AND e.artist_mbid = n.artist_mbid
               AND e.artist_name = n.artist_name
        """)

    def filter_top_full(self, table: str, k: int):
        return run_query(f"""
              WITH intermediate AS (
                SELECT user_id
                     , artist_name
                     , artist_mbid
                     , listen_count
                     , row_number() OVER (PARTITION BY user_id ORDER BY listen_count DESC) AS rank
                  FROM {table}
              )
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
                  FROM intermediate
                 WHERE rank <= {k}
              GROUP BY user_id
        """)

    def filter_top_incremental(self, incremental_listens_table: str, combined_stats_table: str, k: int):
        return run_query(f"""
            WITH users_with_changes AS (
                SELECT DISTINCT user_id
                  FROM {incremental_listens_table}  
            ), filtered_artist_stats AS (
                SELECT user_id
                     , artist_mbid
                     , artist_name
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
                              , artist_name
                              , artist_mbid
                            )
                        )
                        , false
                     ) as artists
                FROM filtered_artist_stats
               WHERE rank <= {k}
            GROUP BY user_id
              HAVING ANY(new_listen_count != old_listen_count)
        """)

    def get_cache_tables(self):
        return [ARTIST_COUNTRY_CODE_DATAFRAME]
