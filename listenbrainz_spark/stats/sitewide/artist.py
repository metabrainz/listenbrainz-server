from listenbrainz_spark.stats import run_query, SITEWIDE_STATS_ENTITY_LIMIT


def get_artists(table: str, limit: int = SITEWIDE_STATS_ENTITY_LIMIT):
    """ Get artist information (artist_name, artist_msid etc) for every time range specified
        the "time_range" table ordered by listen count

        Args:
            table: Name of the temporary table.
            limit: number of top artists to retain
        Returns:
            iterator (iter): An iterator over result
    """
    # we sort twice, the ORDER BY in CTE sorts to eliminate all
    # but top LIMIT results. collect_list's docs mention that the
    # order of collected results is not guaranteed so sort again
    # with sort_array.
    result = run_query(f"""
        WITH intermediate_table as (
            SELECT first(artist_name) AS any_artist_name
                 , artist_credit_mbids
                 , count(*) as listen_count
              FROM {table}
          GROUP BY lower(artist_name)
                 , artist_credit_mbids
          ORDER BY listen_count DESC
             LIMIT {limit}
        )
        SELECT sort_array(
                    collect_list(
                        struct(
                            listen_count
                          , any_artist_name AS artist_name
                          , coalesce(artist_credit_mbids, array()) AS artist_mbids
                        )
                    )
                    , false
               ) AS stats
          FROM intermediate_table
    """)

    return result.toLocalIterator()
