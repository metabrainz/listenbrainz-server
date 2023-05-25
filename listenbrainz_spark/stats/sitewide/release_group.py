from typing import List

from listenbrainz_spark.stats import run_query, SITEWIDE_STATS_ENTITY_LIMIT


def get_release_groups(table: str, cache_tables: List[str], user_listen_count_limit, top_release_groups_limit: int = SITEWIDE_STATS_ENTITY_LIMIT):
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
        WITH gather_release_group_data AS (
            SELECT l.user_id
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
        ), user_counts as (
            SELECT user_id
                 , first(release_group_name) AS any_release_group_name
                 , release_group_mbid
                 , first(release_group_artist_name) AS any_artist_name
                 , artist_credit_mbids
                 , caa_id
                 , caa_release_mbid
                 , LEAST(count(*), {user_listen_count_limit}) as listen_count
              FROM gather_release_group_data
             WHERE release_group_name != ''
               AND release_group_name IS NOT NULL
          GROUP BY user_id
                 , lower(release_group_name)
                 , release_group_mbid
                 , lower(release_group_artist_name)
                 , artist_credit_mbids
                 , caa_id
                 , caa_release_mbid
        ), intermediate_table AS (
            SELECT first(any_release_group_name) AS release_group_name
                 , release_group_mbid
                 , first(any_artist_name) AS artist_name
                 , artist_credit_mbids
                 , caa_id
                 , caa_release_mbid
                 , SUM(listen_count) as total_listen_count
              FROM user_counts
          GROUP BY lower(any_release_group_name)
                 , release_group_mbid
                 , lower(any_artist_name)
                 , artist_credit_mbids
                 , caa_id
                 , caa_release_mbid
        ), entity_count AS (
            SELECT count(*) AS total_count
              FROM intermediate_table
        ), ordered_stats AS (
            SELECT *
              FROM intermediate_table
          ORDER BY total_listen_count DESC
             LIMIT {top_release_groups_limit}
        ), grouped_stats AS (
            SELECT sort_array(
                        collect_list(
                            struct(
                                total_listen_count AS listen_count
                              , release_group_name
                              , release_group_mbid
                              , artist_name
                              , coalesce(artist_credit_mbids, array()) AS artist_mbids
                              , caa_id
                              , caa_release_mbid
                            )
                        )
                       , false
                    ) as stats
              FROM ordered_stats
        )
            SELECT total_count
                 , stats
              FROM grouped_stats
              JOIN entity_count  
                ON TRUE
        """)

    return result.toLocalIterator()
