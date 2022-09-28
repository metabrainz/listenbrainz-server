from listenbrainz_spark.stats import run_query, SITEWIDE_STATS_ENTITY_LIMIT


def get_artists(table: str, user_listen_count_limit, top_artists_limit: int = SITEWIDE_STATS_ENTITY_LIMIT):
    """ Get artist information (artist_name, artist_msid etc) for every time range specified
        the "time_range" table ordered by listen count

        Args:
            table: name of the temporary table
            user_listen_count_limit: per user per entity listen count above which it should be capped
            top_artists_limit: number of top artists to retain
        Returns:
            iterator (iter): An iterator over result
    """
    # we sort twice, the ORDER BY in CTE sorts to eliminate all
    # but top LIMIT results. collect_list's docs mention that the
    # order of collected results is not guaranteed so sort again
    # with sort_array.
    result = run_query(f"""
        WITH user_counts as (
            SELECT user_id
                 , first(artist_name) AS artist_name
                 , artist_credit_mbids
                 , LEAST(count(*), {user_listen_count_limit}) as listen_count
              FROM {table}
          GROUP BY user_id
                 , lower(artist_name)
                 , artist_credit_mbids
        ), intermediate_table AS (
            SELECT first(artist_name) AS artist_name
                 , artist_credit_mbids
                 , SUM(listen_count) as total_listen_count
              FROM user_counts
          GROUP BY lower(artist_name)
                 , artist_credit_mbids
        ), entity_count AS (
            SELECT count(*) AS total_count
              FROM intermediate_table
        ), ordered_stats AS (
            SELECT *
              FROM intermediate_table
          ORDER BY total_listen_count DESC
             LIMIT {top_artists_limit}
        ), grouped_stats AS (
            SELECT sort_array(
                        collect_list(
                            struct(
                                total_listen_count AS listen_count
                              , artist_name
                              , coalesce(artist_credit_mbids, array()) AS artist_mbids
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
    """)

    return result.toLocalIterator()
