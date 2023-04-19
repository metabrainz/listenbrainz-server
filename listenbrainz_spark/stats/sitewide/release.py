from typing import List

from listenbrainz_spark.stats import run_query, SITEWIDE_STATS_ENTITY_LIMIT


def get_releases(table: str, cache_tables: List[str], user_listen_count_limit, top_releases_limit: int = SITEWIDE_STATS_ENTITY_LIMIT):
    """
    Get release information (release_name, release_mbid etc) ordered by
    listen count (number of times listened to tracks which belong to a
    particular release).

    Args:
        table: name of the temporary table
        user_listen_count_limit: per user per entity listen count above which it should be capped
        top_releases_limit: number of top releases to retain
    Returns:
        iterator: an iterator over result, contains only 1 row
                {
                    [
                        {
                            'release_name': str
                            'release_mbid': str,
                            'artist_name': str,
                            'artist_mbids': list(str),
                            'listen_count': int
                        },
                        ...
                    ],
                }
    """
    cache_table = cache_tables[0]
    # we sort twice, the ORDER BY in CTE sorts to eliminate all
    # but top LIMIT results. collect_list's docs mention that the
    # order of collected results is not guaranteed so sort again
    # with sort_array.
    result = run_query(f"""
        WITH gather_release_data AS (
            SELECT user_id
                 , l.release_mbid
                 , COALESCE(rel.release_name, l.release_name) AS release_name
                 , COALESCE(rel.album_artist_name, l.artist_name) AS release_artist_name
                 , COALESCE(rel.artist_credit_mbids, l.artist_credit_mbids) AS artist_credit_mbids
                 , rel.caa_id
                 , rel.caa_release_mbid
              FROM {table} l
         LEFT JOIN {cache_table} rel
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
        ), intermediate_table AS (
            SELECT first(any_release_name) AS release_name
                 , release_mbid
                 , first(any_artist_name) AS artist_name
                 , artist_credit_mbids
                 , caa_id
                 , caa_release_mbid
                 , SUM(listen_count) as total_listen_count
              FROM user_counts
          GROUP BY lower(any_release_name)
                 , release_mbid
                 , lower(any_artist_name)
                 , artist_credit_mbids
                 , caa_id
                 , caa_release_mbid
        ), entity_count AS (
            SELECT count(*) AS total_count
              FROM intermediate_table
        ), ordered_stats AS (
            SELECT *
              FROM intermediate_table
          ORDER BY total_listen_count DESC
             LIMIT {top_releases_limit}
        ), grouped_stats AS (
            SELECT sort_array(
                        collect_list(
                            struct(
                                total_listen_count AS listen_count
                              , release_name
                              , release_mbid
                              , artist_name
                              , coalesce(artist_credit_mbids, array()) AS artist_mbids
                              , caa_id
                              , caa_release_mbid
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
