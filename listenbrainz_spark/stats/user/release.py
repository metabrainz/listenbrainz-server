from listenbrainz_spark.stats import run_query


def get_releases(table: str, number_of_results: int):
    """
    Get release information (release_name, release_mbid etc) for every user
    ordered by listen count (number of times a user has listened to tracks
    which belong to a particular release).

    Args:
        table: name of the temporary table
        number_of_results: number of top results to keep per user.

    Returns:
        iterator (iter): an iterator over result
                {
                    'user1' : [{
                        'release_name': str
                        'release_mbid': str,
                        'artist_name': str,
                        'artist_mbids': list(str),
                        'listen_count': int
                    }],
                    'user2' : [{...}],
                }
    """
    result = run_query(f"""
        WITH intermediate_table as (
            SELECT user_id
                , first(release_name) AS any_release_name
                , release_mbid
                , first(artist_name) AS any_artist_name
                , artist_credit_mbids
                , count(*) as listen_count
              FROM {table}
             WHERE release_name != ''
          GROUP BY user_id
                , lower(release_name)
                , release_mbid
                , lower(artist_name)
                , artist_credit_mbids
        ), entity_count as (
            SELECT user_id
                 , count(*) as releases_count
              FROM intermediate_table
          GROUP BY user_id      
        ), ranked_stats as (
            SELECT user_id
                 , any_release_name AS release_name
                 , release_mbid
                 , any_artist_name AS artist_name
                 , artist_credit_mbids
                 , listen_count
                 , row_number() OVER (PARTITION BY user_id ORDER BY listen_count DESC) AS rank
              FROM intermediate_table
        ), grouped_stats AS (
            SELECT user_id
                 , sort_array(
                        collect_list(
                            struct(
                                listen_count
                              , release_name
                              , release_mbid
                              , artist_name
                              , coalesce(artist_credit_mbids, array()) AS artist_mbids
                            )
                        )
                       , false
                    ) as releases
              FROM ranked_stats
             WHERE rank < {number_of_results}
          GROUP BY user_id
        )
            SELECT user_id
                 , releases_count
                 , releases
              FROM grouped_stats
              JOIN entity_count
             USING (user_id)
        """)

    return result.toLocalIterator()
