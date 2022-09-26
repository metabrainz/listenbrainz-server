from typing import Iterator

from data.model.user_artist_stat import ArtistRecord
from listenbrainz_spark.stats import run_query


def get_artists(table: str, number_of_results: int) -> Iterator[ArtistRecord]:
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
        WITH intermediate_table as (
            SELECT user_id
                 , first(artist_name) AS any_artist_name
                 , artist_credit_mbids
                 , count(*) as listen_count
              FROM {table}
          GROUP BY user_id
                 , lower(artist_name)
                 , artist_credit_mbids
        ), entity_count as (
            SELECT user_id
                 , count(*) as artists_count
              FROM intermediate_table
          GROUP BY user_id      
        ), ranked_stats as (
            SELECT user_id
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
                              , artist_name
                              , coalesce(artist_credit_mbids, array()) AS artist_mbids
                            )
                        )
                        , false
                   ) as artists
              FROM ranked_stats
             WHERE rank < {number_of_results}
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
