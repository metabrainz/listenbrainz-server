from listenbrainz_spark.stats import run_query


def get_recordings(table: str, cache_table: str, number_of_results: int):
    """
    Get recording information (recording_name, recording_mbid etc) for every user
    ordered by listen count (number of times a user has listened to the track/recording).

    Args:
        table: name of the temporary table
        number_of_results: number of top results to keep per user.

    Returns:
        iterator (iter): an iterator over result:
                {
                    'user1' : [
                        {
                            'track_name': str,
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
            SELECT user_id
                 , first(l.recording_name) AS any_recording_name
                 , nullif(l.recording_mbid, '') AS any_recording_mbid
                 , first(l.artist_name) AS any_artist_name
                 , l.artist_credit_mbids
                 , nullif(first(l.release_name), '') as any_release_name
                 , l.release_mbid
                 , rel.caa_id
                 , rel.caa_release_mbid
                 , count(*) as listen_count
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
        ), entity_count as (
            SELECT user_id
                 , count(*) as recordings_count
              FROM intermediate_table
          GROUP BY user_id      
        ), ranked_stats as (
            SELECT user_id
                 , any_recording_name AS track_name
                 , any_recording_mbid AS recording_mbid
                 , any_release_name AS release_name
                 , release_mbid
                 , any_artist_name AS artist_name
                 , artist_credit_mbids
                 , caa_id
                 , caa_release_mbid
                 , listen_count
                 , row_number() OVER (PARTITION BY user_id ORDER BY listen_count DESC) AS rank
              FROM intermediate_table
        ), grouped_stats AS (
            SELECT user_id
                 , sort_array(
                        collect_list(
                            struct(
                                listen_count
                              , track_name
                              , recording_mbid
                              , artist_name
                              , coalesce(artist_credit_mbids, array()) AS artist_mbids
                              , release_name
                              , release_mbid
                              , caa_id
                              , caa_release_mbid
                            )
                        )
                        , false
                   ) as recordings
              FROM ranked_stats
             WHERE rank <= {number_of_results}
          GROUP BY user_id
        )
            SELECT user_id
                 , recordings_count
                 , recordings
              FROM grouped_stats
              JOIN entity_count
             USING (user_id)
        """)

    return result.toLocalIterator()
