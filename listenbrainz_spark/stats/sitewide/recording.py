from typing import List

from listenbrainz_spark.stats import run_query, SITEWIDE_STATS_ENTITY_LIMIT


def get_recordings(table: str, cache_tables: List[str], user_listen_count_limit, top_recordings_limit: int = SITEWIDE_STATS_ENTITY_LIMIT):
    """
    Get recordings information (artist_name etc) for every
    time range specified ordered by listen count.

    Args:
        table: Name of the temporary table.
        user_listen_count_limit: per user per entity listen count above which it should be capped
        top_recordings_limit: number of top artists to retain
    Returns:
        iterator (iter): An iterator over result
    """
    cache_table = cache_tables[0]
    # we sort twice, the ORDER BY in CTE sorts to eliminate all
    # but top LIMIT results. collect_list's docs mention that the
    # order of collected results is not guaranteed so sort again
    # with sort_array.
    result = run_query(f"""
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
         LEFT JOIN {cache_table} rel
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
        ), intermediate_table AS (
            SELECT first(recording_name) AS recording_name
                 , recording_mbid
                 , first(artist_name) AS artist_name
                 , artist_credit_mbids
                 , nullif(first(release_name), '') as release_name
                 , release_mbid
                 , SUM(listen_count) as total_listen_count
              FROM user_counts uc
          GROUP BY lower(uc.recording_name)
                 , recording_mbid
                 , lower(uc.artist_name)
                 , artist_credit_mbids
                 , lower(release_name)
                 , release_mbid
        ), entity_count AS (
            SELECT count(*) AS total_count
              FROM intermediate_table
        ), ordered_stats AS (
            SELECT *
              FROM intermediate_table
          ORDER BY total_listen_count DESC
             LIMIT {top_recordings_limit}
        ), grouped_stats AS (
            SELECT sort_array(
                        collect_list(
                            struct(
                                total_listen_count AS listen_count
                              , recording_name AS track_name
                              , recording_mbid
                              , artist_name
                              , coalesce(artist_credit_mbids, array()) AS artist_mbids
                              , release_name
                              , release_mbid
                            )
                        )
                       , false
                   ) as stats
              FROM ordered_stats
        )
        SELECT total_count
             , stats
          FROM grouped_stats
          JOIN entity_count
            ON TRUE
    """)

    return result.toLocalIterator()
