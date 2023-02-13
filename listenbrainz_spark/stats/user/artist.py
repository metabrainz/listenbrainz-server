from typing import Iterator

from data.model.user_artist_stat import ArtistRecord
from listenbrainz_spark.stats import run_query


def get_artists(table: str, cache_table: str, number_of_results: int) -> Iterator[ArtistRecord]:
    """ Get artist information (artist_name, artist_credit_id etc) for every user
        ordered by listen count

        Args:
            table: name of the temporary table.
            number_of_results: number of top results to keep per user.

        Returns:
            iterator (iter): an iterator over result
                    {
                        user1: [
                            {
                                'artist_name': str,
                                'artist_credit_id': int,
                                'listen_count': int
                            }
                        ],
                        user2: [{...}],
                    }
    """

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
        ), intermediate_table AS (
            SELECT user_id
            -- we group by lower(artist_name) and pick the first artist name for cases where
            -- the artist name differs in case. for mapped listens the artist name from MB will
            -- be used. for unmapped listens we can't know which case is correct so use any. note
            -- that due to presence of artist mbid as the third group, mapped and unmapped listens
            -- will always be separately grouped therefore first will work fine for unmapped
            -- listens and doesn't matter for mapped ones.
                 , first(artist_name) AS any_artist_name
                 , artist_mbid
                 , count(*) AS listen_count
             FROM listens_with_mb_data
         GROUP BY user_id
                , lower(artist_name)
                , artist_mbid    
        ), entity_count as (
            SELECT user_id
                 , count(*) as artists_count
              FROM intermediate_table
          GROUP BY user_id      
        ), ranked_stats as (
            SELECT user_id
                 , any_artist_name AS artist_name
                 , artist_mbid
                 , listen_count
                 , row_number() OVER (PARTITION BY user_id ORDER BY listen_count DESC) AS rank
              FROM intermediate_table
        ), grouped_stats AS (
            SELECT user_id
                 , sort_array(
                        collect_list(
                            struct(
                                listen_count
                              , artist_name
                              , artist_mbid
                            )
                        )
                        , false
                   ) as artists
              FROM ranked_stats
             WHERE rank <= {number_of_results}
          GROUP BY user_id
        )
            SELECT user_id
                 , artists_count
                 , artists
              FROM grouped_stats
              JOIN entity_count
             USING (user_id)
    """)

    return result.toLocalIterator()
