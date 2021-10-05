from listenbrainz_spark.stats import run_query


def get_releases(table):
    """
    Get release information (release_name, release_mbid etc) for every user
    ordered by listen count (number of times a user has listened to tracks
    which belong to a particular release).

    Args:
        table: name of the temporary table

    Returns:
        iterator (iter): an iterator over result
                {
                    'user1' : [{
                        'release_name': str
                        'release_msid': str,
                        'release_mbid': str,
                        'artist_name': str,
                        'artist_msid': str,
                        'artist_mbids': list(str),
                        'listen_count': int
                    }],
                    'user2' : [{...}],
                }
    """
    result = run_query(f"""
        WITH intermediate_table as (
            SELECT user_name
                , first(release_name) AS any_release_name
                , release_mbid
                , first(artist_name) AS any_artist_name
                , artist_credit_mbids
                , count(*) as listen_count
              FROM {table}
             WHERE release_name != ''
          GROUP BY user_name
                , lower(release_name)
                , release_mbid
                , lower(artist_name)
                , artist_credit_mbids
        )
        SELECT user_name
             , sort_array(
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
                ) as releases
          FROM intermediate_table
      GROUP BY user_name
        """)

    return result.toLocalIterator()
