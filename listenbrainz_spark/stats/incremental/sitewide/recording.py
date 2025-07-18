from listenbrainz_spark.postgres.release import get_release_metadata_cache
from listenbrainz_spark.stats.incremental.sitewide.entity import SitewideEntityStatsQueryProvider


class RecordingSitewideEntity(SitewideEntityStatsQueryProvider):
    """ See base class QueryProvider for details. """

    @property
    def entity(self):
        return "recordings"

    def get_aggregate_query(self, table):
        user_listen_count_limit = self.get_listen_count_limit()
        rel_cache_table = get_release_metadata_cache()
        return f"""
        WITH user_counts as (
            SELECT user_id
                 , first(l.recording_name) AS recording_name
                 , nullif(l.recording_mbid, '') AS recording_mbid
                 , first(l.artist_name) AS artist_name
                 , l.artist_credit_mbids
                 , nullif(first(l.release_name), '') as release_name
                 , l.release_mbid
                 , rel.caa_id
                 , rel.caa_release_mbid
                 , LEAST(count(*), {user_listen_count_limit}) as listen_count
              FROM {table} l
         LEFT JOIN {rel_cache_table} rel
                ON rel.release_mbid = l.release_mbid
          GROUP BY l.user_id
                 , lower(l.recording_name)
                 , l.recording_mbid
                 , lower(l.artist_name)
                 , l.artist_credit_mbids
                 , lower(l.release_name)
                 , l.release_mbid
                 , rel.caa_id
                 , rel.caa_release_mbid
        )
            SELECT first(recording_name) AS recording_name
                 , recording_mbid
                 , first(artist_name) AS artist_name
                 , artist_credit_mbids
                 , nullif(first(release_name), '') as release_name
                 , release_mbid
                 , caa_id
                 , caa_release_mbid
                 , SUM(listen_count) as listen_count
              FROM user_counts uc
          GROUP BY lower(uc.recording_name)
                 , recording_mbid
                 , lower(uc.artist_name)
                 , artist_credit_mbids
                 , lower(release_name)
                 , release_mbid
                 , caa_id
                 , caa_release_mbid
        """

    def get_combine_aggregates_query(self, existing_aggregate, incremental_aggregate):
        return f"""
            WITH intermediate_table AS (
                SELECT recording_name
                     , recording_mbid
                     , artist_name
                     , artist_credit_mbids
                     , release_name
                     , release_mbid
                     , caa_id
                     , caa_release_mbid
                     , listen_count
                  FROM {existing_aggregate}
                 UNION ALL
                SELECT recording_name
                     , recording_mbid
                     , artist_name
                     , artist_credit_mbids
                     , release_name
                     , release_mbid
                     , caa_id
                     , caa_release_mbid
                     , listen_count
                  FROM {incremental_aggregate}
            )
                SELECT first(recording_name) AS recording_name
                     , recording_mbid
                     , first(artist_name) AS artist_name
                     , artist_credit_mbids
                     , first(release_name) AS release_name
                     , release_mbid
                     , caa_id
                     , caa_release_mbid
                     , sum(listen_count) as listen_count
                  FROM intermediate_table
              GROUP BY lower(recording_name)
                     , recording_mbid
                     , lower(artist_name)
                     , artist_credit_mbids
                     , lower(release_name)
                     , release_mbid
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
                                      , recording_name AS track_name
                                      , recording_mbid
                                      , artist_name
                                      , coalesce(artist_credit_mbids, array()) AS artist_mbids
                                      , release_name
                                      , release_mbid
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
