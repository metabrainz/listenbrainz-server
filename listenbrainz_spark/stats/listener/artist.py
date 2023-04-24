from typing import Iterator, List

from data.model.entity_listener_stat import ArtistListenerRecord
from listenbrainz_spark.stats import run_query


def get_listeners(table: str, cache_tables: List[str], number_of_results: int) -> Iterator[ArtistListenerRecord]:
    """ Get information about top listeners of an artist

        Args:
            table: name of the temporary table having listens.
            cache_tables: artist data table
            number_of_results: number of top results to keep per user.

        Returns:
            iterator (iter): an iterator over result

            {
                "artist-mbid-1": {
                    "count": total listen count,
                    "top_listeners": [list of user ids of top listeners]
                },
                // ...
            }

    """
    cache_table = cache_tables[0]
    result = run_query(f"""
        WITH exploded_listens AS (
            SELECT user_id
                 , explode_outer(artist_credit_mbids) AS artist_mbid
              FROM {table}
        ), listens_with_mb_data as (
            SELECT user_id
                 , artist_mbid
                 , at.artist_name
              FROM exploded_listens el
              JOIN {cache_table} at
             USING (artist_mbid)
        ), intermediate_table AS (
            SELECT artist_mbid
                 , artist_name
                 , user_id
                 , count(*) AS listen_count
              FROM listens_with_mb_data
          GROUP BY artist_mbid
                 , artist_name
                 , user_id
        ), entity_count as (
            SELECT artist_mbid
                 , SUM(listen_count) as total_listen_count
              FROM intermediate_table
          GROUP BY artist_mbid      
        ), ranked_stats as (
            SELECT artist_mbid
                 , artist_name
                 , user_id 
                 , listen_count
                 , row_number() OVER (PARTITION BY user_id ORDER BY listen_count DESC) AS rank
              FROM intermediate_table
        ), grouped_stats AS (
            SELECT artist_mbid
                 , artist_name
                 , sort_array(
                        collect_list(
                            struct(
                                listen_count
                              , user_id 
                            )
                        )
                        , false
                   ) as listeners
              FROM ranked_stats
             WHERE rank < {number_of_results}
          GROUP BY artist_mbid
                 , artist_name
        )
            SELECT artist_mbid
                 , artist_name
                 , listeners
                 , total_listen_count
              FROM grouped_stats
              JOIN entity_count
             USING (artist_mbid)
    """)

    return result.toLocalIterator()
