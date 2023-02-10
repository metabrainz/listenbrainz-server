from listenbrainz_spark.stats import run_query, SITEWIDE_STATS_ENTITY_LIMIT


def get_releases(table: str, cache_table: str, user_listen_count_limit, top_releases_limit: int = SITEWIDE_STATS_ENTITY_LIMIT):
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
    result = run_query(f"""
        WITH user_counts AS (
            SELECT user_id
                 , first(release_name) AS release_name
                 , release_mbid
                 , first(artist_name) AS artist_name
                 , artist_credit_mbids
                 , LEAST(count(*), {user_listen_count_limit}) as listen_count
              FROM {table}
             WHERE release_name != ''
          GROUP BY user_id
                 , lower(release_name)
                 , release_mbid
                 , lower(artist_name)
                 , artist_credit_mbids
        ), intermediate_table AS (
            SELECT first(release_name) AS release_name
                 , release_mbid
                 , first(artist_name) AS artist_name
                 , artist_credit_mbids
                 , SUM(listen_count) as total_listen_count
              FROM user_counts
          GROUP BY lower(release_name)
                 , release_mbid
                 , lower(artist_name)
                 , artist_credit_mbids
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
