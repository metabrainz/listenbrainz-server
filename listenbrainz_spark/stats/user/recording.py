from listenbrainz_spark.stats import run_query


def get_recordings(table):
    """
    Get recording information (recording_name, recording_mbid etc) for every user
    ordered by listen count (number of times a user has listened to the track/recording).

    Args:
        table: name of the temporary table

    Returns:
        iterator (iter): an iterator over result:
                {
                    'user1' : [
                        {
                            'recording_name': str,
                            'recording_mbid': str,
                            'artist_name': str,
                            'artist_credit_id': int,
                            'release_name': str,
                            'release_mbid': str,
                            'listen_count': int
                        }
                    ],
                    'user2' : [{...}],
                }
    """
    result = run_query(f"""
        WITH intermediate_table as (
            SELECT user_name
                 , recording_name
                 , recording_mbid
                 , artist_name
                 , artist_credit_mbids
                 , nullif(release_name, '') as release_name
                 , release_mbid
                 , count(*) as listen_count
              FROM {table}
          GROUP BY user_name
                 , recording_name
                 , recording_mbid
                 , artist_name
                 , artist_credit_mbids
                 , release_name
                 , release_mbid
        )
        SELECT user_name
             , sort_array(
                    collect_list(
                        struct(
                            listen_count
                          , recording_name
                          , recording_mbid
                          , artist_name
                          , artist_credit_mbids AS artist_mbids
                          , release_name
                          , release_mbid
                        )
                    )
                   , false
                ) as recordings
          FROM intermediate_table
      GROUP BY user_name
        """)

    return result.toLocalIterator()
