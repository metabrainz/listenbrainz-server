from listenbrainz_spark.stats import run_query
from pyspark.sql.functions import collect_list, sort_array, struct


def get_artists(table: str, limit: int = 1000):
    """ Get artist information (artist_name, artist_msid etc) for every time range specified
        the "time_range" table ordered by listen count

        Args:
            table: Name of the temporary table.
            limit: number of top artists to retain
        Returns:
            iterator (iter): An iterator over result
    """

    result = run_query(f"""
        WITH intermediate_table as (
            SELECT artist_name
                 , artist_credit_mbids
                 , count(*) as listen_count
              FROM {table}
          GROUP BY artist_name
                 , artist_credit_mbids
          ORDER BY listen_count DESC
             LIMIT {limit}
        )
        SELECT collect_list(
                    struct(
                        artist_name
                      , coalesce(artist_credit_mbids, array()) AS artist_mbids
                      , listen_count
                    )
               ) AS stats
          FROM intermediate_table
    """)

    return result.toLocalIterator()
