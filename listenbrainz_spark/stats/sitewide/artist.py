from listenbrainz_spark.stats import run_query, SITEWIDE_STATS_ENTITY_LIMIT


def get_artists(table: str, cache_table: str, user_listen_count_limit, top_artists_limit: int = SITEWIDE_STATS_ENTITY_LIMIT):
    """ Get artist information (artist_name etc) for every time range specified
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
        WITH exploded_listens AS (
            SELECT user_id
                 , artist_name AS artist_credit_name
                 , explode_outer(artist_credit_mbids) AS artist_mbid
             FROM {table}
        ), listens_with_mb_data as (
            SELECT user_id
                 , COALESCE(at.artist_name, el.artist_credit_name) AS artist_name
                 , el.artist_mbid
              FROM exploded_listens el
         LEFT JOIN {cache_table} at
                ON el.artist_mbid = at.artist_mbid
        ), user_counts as (
            SELECT user_id
                 , first(artist_name) AS any_artist_name
                 , artist_mbid
                 , LEAST(count(*), {user_listen_count_limit}) as listen_count
             FROM listens_with_mb_data
         GROUP BY user_id
                , lower(artist_name)
                , artist_mbid
        ), intermediate_table AS (
            SELECT first(any_artist_name) AS artist_name
                 , artist_mbid
                 , SUM(listen_count) as total_listen_count
              FROM user_counts
          GROUP BY lower(any_artist_name)
                 , artist_mbid
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
                              , artist_mbid
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
