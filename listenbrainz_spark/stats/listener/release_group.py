from typing import Iterator, List

from data.model.entity_listener_stat import ArtistListenerRecord
from listenbrainz_spark.stats import run_query


def get_listeners(table: str, cache_tables: List[str], number_of_results: int) -> Iterator[ArtistListenerRecord]:
    """ Get information about top listeners of a release group.

        Args:
            table: name of the temporary table having listens.
            cache_tables: release data tables
            number_of_results: number of top results to keep per user.

        Returns:
            iterator (iter): an iterator over result

            {
                "release-group-mbid-1": {
                    "count": total listen count,
                    "top_listeners": [list of user ids of top listeners]
                },
                // ...
            }

    """
    rel_cache_table = cache_tables[0]
    rg_cache_table = cache_tables[1]
    result = run_query(f"""
        WITH gather_release_data AS (
            SELECT user_id
                 , rg.release_group_mbid
                 -- this is intentional as we don't have a release group name field in listen submission json
                 -- and for the purposes of this stat, they'd usually be the same.
                 , COALESCE(rg.title, l.release_name) AS release_group_name
                 , COALESCE(rg.artist_credit_name, l.artist_name) AS release_group_artist_name
                 , COALESCE(rg.artist_credit_mbids, l.artist_credit_mbids) AS artist_credit_mbids
                 , rg.caa_id
                 , rg.caa_release_mbid
              FROM {table} l
         LEFT JOIN {rel_cache_table} rel
                ON rel.release_mbid = l.release_mbid
         LEFT JOIN {rg_cache_table} rg
                ON rg.release_group_mbid = rel.release_group_mbid
        ), intermediate_table AS (
            SELECT user_id
                 , release_group_mbid
                 , release_group_name
                 , release_group_artist_name
                 , artist_credit_mbids
                 , caa_id
                 , caa_release_mbid
                 , count(*) AS listen_count
              FROM gather_release_data
          GROUP BY release_group_mbid
                 , release_group_name
                 , release_group_artist_name
                 , artist_credit_mbids
                 , caa_id
                 , caa_release_mbid
                 , user_id
        ), entity_count as (
            SELECT release_group_mbid
                 , SUM(listen_count) as total_listen_count
              FROM intermediate_table
          GROUP BY release_group_mbid      
        ), ranked_stats as (
            SELECT release_group_mbid
                 , release_group_name
                 , release_group_artist_name AS artist_name
                 , artist_credit_mbids AS artist_mbids
                 , caa_id
                 , caa_release_mbid
                 , user_id 
                 , listen_count
                 , row_number() OVER (PARTITION BY user_id ORDER BY listen_count DESC) AS rank
              FROM intermediate_table
        ), grouped_stats AS (
            SELECT release_group_mbid
                 , release_group_name
                 , artist_name
                 , artist_mbids
                 , caa_id
                 , caa_release_mbid
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
          GROUP BY release_group_mbid
                 , release_group_name
                 , artist_name
                 , artist_mbids
                 , caa_id
                 , caa_release_mbid
        )
            SELECT release_group_mbid
                 , release_group_name
                 , artist_name
                 , artist_mbids
                 , caa_id
                 , caa_release_mbid
                 , listeners
                 , total_listen_count
              FROM grouped_stats
              JOIN entity_count
             USING (release_group_mbid)
    """)

    return result.toLocalIterator()
