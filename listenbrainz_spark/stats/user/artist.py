from typing import Iterator

from data.model.user_artist_stat import ArtistRecord
from listenbrainz_spark.stats import run_query


def get_artists(table: str) -> Iterator[ArtistRecord]:
    """ Get artist information (artist_name, artist_credit_id etc) for every user
        ordered by listen count

        Args:
            table: name of the temporary table.

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
        )
        SELECT user_id
             , sort_array(
                    collect_list(
                        struct(
                            listen_count
                          , any_artist_name AS artist_name
                          , coalesce(artist_credit_mbids, array()) AS artist_mbids
                        )
                    )
                    , false
               ) as artists
          FROM intermediate_table
      GROUP BY user_id 
    """)

    return result.toLocalIterator()
