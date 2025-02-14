from typing import List

from listenbrainz_spark.postgres.recording import get_recording_artist_cache
from listenbrainz_spark.postgres.release import get_release_metadata_cache
from listenbrainz_spark.stats.incremental.user.entity import UserEntityStatsQueryProvider


class RecordingUserEntity(UserEntityStatsQueryProvider):
    """ See base class QueryProvider for details. """

    @property
    def entity(self):
        return "recordings"

    def get_aggregate_query(self, table):
        rec_cache_table = get_recording_artist_cache()
        rel_cache_table = get_release_metadata_cache()
        return f"""
            SELECT user_id
                 , first(l.recording_name) AS recording_name
                 , nullif(l.recording_mbid, '') AS recording_mbid
                 , first(l.artist_name) AS artist_name
                 , l.artist_credit_mbids
                 , nullif(first(l.release_name), '') as release_name
                 , nullif(l.release_mbid, '') AS release_mbid
                 , rec.artists
                 , rel.caa_id
                 , rel.caa_release_mbid
                 , count(*) as listen_count
              FROM {table} l
         LEFT JOIN {rec_cache_table} rec
                ON rec.recording_mbid = l.recording_mbid
         LEFT JOIN {rel_cache_table} rel
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
        """

    def get_combine_aggregates_query(self, existing_aggregate, incremental_aggregate):
        return f"""
            WITH intermediate_table AS (
                SELECT user_id
                     , recording_name
                     , recording_mbid
                     , artist_name
                     , artist_credit_mbids
                     , release_name
                     , release_mbid
                     , artists
                     , caa_id
                     , caa_release_mbid
                     , listen_count
                  FROM {existing_aggregate}
                 UNION ALL
                SELECT user_id
                     , recording_name
                     , recording_mbid
                     , artist_name
                     , artist_credit_mbids
                     , release_name
                     , release_mbid
                     , artists
                     , caa_id
                     , caa_release_mbid
                     , listen_count
                  FROM {incremental_aggregate}
            )
                SELECT user_id
                     , first(recording_name) AS recording_name
                     , recording_mbid
                     , first(artist_name) AS artist_name
                     , artist_credit_mbids
                     , first(release_name) AS release_name
                     , release_mbid
                     , artists
                     , caa_id
                     , caa_release_mbid
                     , sum(listen_count) as listen_count
                  FROM intermediate_table
              GROUP BY user_id
                     , lower(recording_name)
                     , recording_mbid
                     , lower(artist_name)
                     , artist_credit_mbids
                     , lower(release_name)
                     , release_mbid
                     , artists
                     , caa_id
                     , caa_release_mbid
        """

    def get_stats_query(self, final_aggregate):
        return f"""
            WITH entity_count AS (
                SELECT user_id
                     , count(*) AS recordings_count
                  FROM {final_aggregate}
              GROUP BY user_id
            ), ranked_stats AS (
                SELECT user_id
                     , recording_name as track_name
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
                  FROM {final_aggregate}
            ), grouped_stats AS (
                SELECT user_id
                     , sort_array(
                            collect_list(
                                struct(
                                    listen_count
                                  , track_name
                                  , recording_mbid
                                  , artist_name
                                  , coalesce(artist_credit_mbids, array()) AS artist_mbids
                                  , release_name
                                  , release_mbid
                                  , artists
                                  , caa_id
                                  , caa_release_mbid
                                )
                            )
                            , false
                       ) as recordings
                  FROM ranked_stats
                 WHERE rank <= {self.top_entity_limit}
              GROUP BY user_id
            )
                SELECT user_id
                     , recordings_count
                     , recordings
                  FROM grouped_stats
                  JOIN entity_count
                 USING (user_id)
        """
