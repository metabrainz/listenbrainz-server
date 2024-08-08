from listenbrainz_spark.path import RECORDING_ARTIST_DATAFRAME, RELEASE_METADATA_CACHE_DATAFRAME
from listenbrainz_spark.stats import run_query
from listenbrainz_spark.stats.incremental import Entity, save_parquet, end_job


class Recording(Entity):

    def get_stats_from_listens(self, listen_table: str):
        rec_cache_table = self.get_cache_tables()[0]
        rel_cache_table = self.get_cache_tables()[1]
        return run_query(f"""
            WITH intermediate_table as (
                SELECT user_id
                     , first(l.recording_name) AS any_recording_name
                     , nullif(l.recording_mbid, '') AS any_recording_mbid
                     , first(l.artist_name) AS any_artist_name
                     , l.artist_credit_mbids
                     , nullif(first(l.release_name), '') as any_release_name
                     , nullif(l.release_mbid, '') AS any_release_mbid
                     , rec.artists
                     , rel.caa_id
                     , rel.caa_release_mbid
                     , count(*) as listen_count
                  FROM {listen_table} l
             LEFT JOIN parquet.`{rec_cache_table}` rec
                    ON rec.recording_mbid = l.recording_mbid
             LEFT JOIN parquet.`{rel_cache_table}` rel
                    ON rel.release_mbid = l.release_mbid
              GROUP BY l.user_id
                     , lower(l.recording_name)
                     , l.recording_mbid
                     , lower(l.artist_name)
                     , l.artist_credit_mbids
                     , lower(l.release_name)
                     , l.release_mbid
                     , rec.artists
                     , rel.caa_id
                     , rel.caa_release_mbid
            )
                SELECT user_id
                     , any_recording_name AS track_name
                     , any_recording_mbid AS recording_mbid
                     , any_release_name AS release_name
                     , any_release_mbid AS release_mbid
                     , any_artist_name AS artist_name
                     , artist_credit_mbids
                     , artists
                     , caa_id
                     , caa_release_mbid
                     , listen_count
                  FROM intermediate_table
            """)

    def combine_existing_and_new_stats(self, existing_table: str, new_table: str):
        return run_query(f"""
            SELECT COALESCE(n.user_id, e.user_id) AS user_id
                 , COALESCE(n.track_name, e.track_name) AS track_name
                 , COALESCE(n.recording_mbid, e.recording_mbid) AS recording_mbid
                 , COALESCE(n.release_name, e.release_name) AS release_name
                 , COALESCE(n.release_mbid, e.release_mbid) AS release_mbid
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
               AND n.track_name = e.track_name
               AND (n.recording_mbid = e.recording_mbid OR (n.recording_mbid IS NULL AND e.recording_mbid IS NULL))
               AND (n.release_name = e.release_name OR (n.release_name IS NULL AND e.release_name IS NULL))
               AND (n.release_mbid = e.release_mbid OR (n.release_mbid iS NULL AND e.release_mbid IS NULL))
               AND n.artist_name = e.artist_name
               AND (n.artist_credit_mbids = e.artist_credit_mbids OR (n.artist_credit_mbids IS NULL AND e.artist_credit_mbids IS NULL))
               AND (n.artists = e.artists OR (n.artists IS NULL AND e.artists IS NULL))
               AND (n.caa_id = e.caa_id OR (n.caa_id IS NULL AND e.caa_id IS NULL))
               AND (n.caa_release_mbid = e.caa_release_mbid OR (n.caa_release_mbid IS NULL AND e.caa_release_mbid IS NULL))
        """)

    def filter_top_full(self, table: str, k: int):
        return run_query(f"""
              WITH intermediate AS (
                SELECT user_id
                     , track_name
                     , recording_mbid
                     , release_name
                     , release_mbid
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
                                  , track_name
                                  , recording_mbid
                                  , release_name
                                  , release_mbid
                                  , artist_name
                                  , coalesce(artist_credit_mbids, array()) as artist_mbids
                                  , artists
                                  , caa_id
                                  , caa_release_mbid
                                )
                            )
                            , false
                       ) as recordings
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
                     , track_name
                     , recording_mbid
                     , release_name
                     , release_mbid
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
            ), aggregate_stats AS (
               SELECT user_id
                     , sort_array(
                        collect_list(
                            struct(
                                new_listen_count AS listen_count
                              , track_name
                              , recording_mbid
                              , release_name
                              , release_mbid
                              , artist_name
                              , coalesce(artist_credit_mbids, array()) as artist_mbids
                              , artists
                              , caa_id
                              , caa_release_mbid
                            )
                        )
                        , false
                     ) as recordings
                FROM filtered_entity_stats
               WHERE rank <= {k}
            GROUP BY user_id
              HAVING ANY(new_listen_count != old_listen_count)
            ), entity_counts AS (
              SELECT user_id
                   , count(*) as recordings_count
                FROM filtered_entity_stats
            GROUP BY user_id    
            )
              SELECT agg.user_id
                   , recordings as data
                   , recordings_count as count
                FROM aggregate_stats agg
                JOIN entity_counts ec
                  ON agg.user_id = ec.user_id
        """)

    def post_process_incremental(self, type_, entity, stats_range, combined_entity_table, stats_aggregation_path):
        new_stats_df = run_query(f"""
            SELECT user_id
                 , track_name
                 , recording_mbid
                 , release_name
                 , release_mbid
                 , artist_name
                 , artist_credit_mbids
                 , artists
                 , caa_id
                 , caa_release_mbid
                 , new_listen_count AS listen_count
              FROM {combined_entity_table}
        """)
        save_parquet(new_stats_df, stats_aggregation_path)
        end_job(type_, entity, stats_range)

    def get_cache_tables(self):
        return [RECORDING_ARTIST_DATAFRAME, RELEASE_METADATA_CACHE_DATAFRAME]
