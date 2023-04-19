from typing import List

from listenbrainz_spark.stats import run_query


def get_release_groups(table: str, cache_tables: List[str], number_of_results: int):
    """
    Get release group information (release_group_name, release_group_mbid etc) for every user
    ordered by listen count (number of times a user has listened to tracks
    which belong to a particular release).

    Args:
        table: name of the temporary table
        number_of_results: number of top results to keep per user.

    Returns:
        iterator (iter): an iterator over result
                {
                    'user1' : [{
                        'release_group_name': str
                        'release_group_mbid': str,
                        'artist_name': str,
                        'artist_mbids': list(str),
                        'listen_count': int
                    }],
                    'user2' : [{...}],
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
        ), intermediate_table as (
            SELECT user_id
                 , first(release_group_name) AS any_release_group_name
                 , release_group_mbid
                 , first(release_group_artist_name) AS any_artist_name
                 , artist_credit_mbids
                 , caa_id
                 , caa_release_mbid
                 , count(*) as listen_count
              FROM gather_release_data
             WHERE release_group_name != ''
               AND release_group_name IS NOT NULL
          GROUP BY user_id
                 , lower(release_group_name)
                 , release_group_mbid
                 , lower(release_group_artist_name)
                 , artist_credit_mbids
                 , caa_id
                 , caa_release_mbid
        ), entity_count as (
            SELECT user_id
                 , count(*) as release_groups_count
              FROM intermediate_table
          GROUP BY user_id      
        ), ranked_stats as (
            SELECT user_id
                 , any_release_group_name AS release_group_name
                 , release_group_mbid
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
                              , release_group_name
                              , release_group_mbid
                              , artist_name
                              , coalesce(artist_credit_mbids, array()) AS artist_mbids
                              , caa_id
                              , caa_release_mbid
                            )
                        )
                       , false
                    ) as release_groups
              FROM ranked_stats
             WHERE rank <= {number_of_results}
          GROUP BY user_id
        )
            SELECT user_id
                 , release_groups_count
                 , release_groups
              FROM grouped_stats
              JOIN entity_count
             USING (user_id)
        """)

    return result.toLocalIterator()
