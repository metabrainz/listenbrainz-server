from listenbrainz_spark.stats import run_query, SITEWIDE_STATS_ENTITY_LIMIT


def get_releases(table: str, limit: int = SITEWIDE_STATS_ENTITY_LIMIT):
    """
    Get release information (release_name, release_mbid etc) ordered by
    listen count (number of times listened to tracks which belong to a
    particular release).

    Args:
        table: name of the temporary table
        limit: number of top releases to retain
    Returns:
        iterator: an iterator over result, contains only 1 row
                {
                    [
                        {
                            'release_name': str
                            'release_msid': str,
                            'release_mbid': str,
                            'artist_name': str,
                            'artist_msid': str,
                            'artist_mbids': list(str),
                            'listen_count': int
                        },
                        ...
                    ],
                }
    """
    result = run_query(f"""
        WITH intermediate_table as (
            SELECT first(release_name) AS any_release_name
                 , release_mbid
                 , first(artist_name) AS any_artist_name
                 , artist_credit_mbids
                 , count(*) as listen_count
              FROM {table}
             WHERE release_name != ''
          GROUP BY lower(release_name)
                 , release_mbid
                 , lower(artist_name)
                 , artist_credit_mbids
          ORDER BY listen_count DESC
             LIMIT {limit}
        )
        SELECT sort_array(
                    collect_list(
                        struct(
                            listen_count
                          , any_release_name AS release_name
                          , release_mbid
                          , any_artist_name AS artist_name
                          , coalesce(artist_credit_mbids, array()) AS artist_mbids
                        )
                    )
                   , false
                ) as stats
          FROM intermediate_table
        """)

    return result.toLocalIterator()
