from listenbrainz_spark.postgres.recording_writer import get_recording_writer_cache
from listenbrainz_spark.stats.incremental.range_selector import ListenRangeSelector
from listenbrainz_spark.stats.incremental.user.entity import UserEntityStatsQueryProvider


class WriterUserEntity(UserEntityStatsQueryProvider):
    """ See base class QueryProvider for details.

    Calculates top writers (composers/lyricists/writers) for each user by
    joining listens with the recording-writer cache. The recording-writer
    cache maps recording_mbid -> (writer_mbid, writer_name) by traversing
    MusicBrainz recording -> work -> artist relationships.

    Each listen contributes one count to every writer associated with the
    recording's linked work(s).
    """

    def __init__(self, selector: ListenRangeSelector, top_entity_limit: int):
        super().__init__(selector=selector, top_entity_limit=top_entity_limit)

    @property
    def entity(self):
        return "writers"

    def get_aggregate_query(self, table):
        cache_table = get_recording_writer_cache()
        return f"""
            WITH listens_with_writers AS (
                SELECT l.user_id
                     , wc.writer_name
                     , wc.writer_mbid
                  FROM {table} l
                  JOIN {cache_table} wc
                    ON l.recording_mbid = wc.recording_mbid
                 WHERE l.recording_mbid IS NOT NULL
            )
                SELECT user_id
                     , first(writer_name) AS writer_name
                     , writer_mbid
                     , count(*) AS listen_count
                  FROM listens_with_writers
              GROUP BY user_id
                     , lower(writer_name)
                     , writer_mbid
        """

    def get_combine_aggregates_query(self, existing_aggregate, incremental_aggregate):
        return f"""
            WITH intermediate_table AS (
                SELECT user_id
                     , writer_name
                     , writer_mbid
                     , listen_count
                  FROM {existing_aggregate}
                 UNION ALL
                SELECT user_id
                     , writer_name
                     , writer_mbid
                     , listen_count
                  FROM {incremental_aggregate}
            )
                SELECT user_id
                     , first(writer_name) AS writer_name
                     , writer_mbid
                     , sum(listen_count) as listen_count
                  FROM intermediate_table
              GROUP BY user_id
                     , lower(writer_name)
                     , writer_mbid
        """

    def get_stats_query(self, final_aggregate):
        return f"""
            WITH entity_count AS (
                SELECT user_id
                     , count(*) AS writers_count
                  FROM {final_aggregate}
              GROUP BY user_id
            ), ranked_stats AS (
                SELECT user_id
                     , writer_name
                     , writer_mbid
                     , listen_count
                     , row_number() OVER (PARTITION BY user_id ORDER BY listen_count DESC) AS rank
                  FROM {final_aggregate}
            ), grouped_stats AS (
                SELECT user_id
                     , sort_array(
                            collect_list(
                                struct(
                                    listen_count
                                  , writer_name
                                  , writer_mbid
                                )
                            )
                            , false
                       ) as writers
                  FROM ranked_stats
                 WHERE rank <= {self.top_entity_limit}
              GROUP BY user_id
            )
                SELECT user_id
                     , writers_count
                     , writers
                  FROM grouped_stats
                  JOIN entity_count
                 USING (user_id)
        """
