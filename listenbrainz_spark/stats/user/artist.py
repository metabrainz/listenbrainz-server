from typing import Iterator

from data.model.user_artist_stat import UserArtistRecord
from listenbrainz_spark.stats import run_query


def get_artists(table: str) -> Iterator[UserArtistRecord]:
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
            SELECT user_name
                 , artist_name
                 , artist_credit_mbids
                 , count(*) as listen_count
              FROM {table}
          GROUP BY user_name
                 , artist_name
                 , artist_credit_mbids
        )
        SELECT user_name
             , sort_array(
                    collect_list(
                        struct(
                            listen_count
                          , artist_name
                          , artist_credit_mbids AS artist_mbids
                        )
                    )
                    , false
               ) as artists
          FROM intermediate_table
      GROUP BY user_name 
    """)

    return result.toLocalIterator()
