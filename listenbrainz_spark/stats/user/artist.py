import listenbrainz_spark.stats.utils as stat_utils
from listenbrainz_spark.stats import run_query
from pyspark.sql.functions import collect_list, sort_array, struct


def get_artists(table: str, use_mapping: bool):
    """ Get artist information (artist_name, artist_msid etc) for every user
        ordered by listen count

        Args:
            table: Name of the temporary table.
            use_mapping: True if MSID-MBID mapping should be used.

        Returns:
            iterator (iter): an iterator over result
                    {
                        user1: [{
                            'artist_name': str,
                            'artist_msid': str,
                            'artist_mbids': list(str),
                            'listen_count': int
                        }],
                        user2: [{...}],
                    }
    """
    listens_df = run_query(f"SELECT * FROM {table}")
    if use_mapping:
        mapped_listens, unmapped_listens = stat_utils.create_mapped_dataframe(listens_df)
    else:
        unmapped_listens = listens_df

    # Calculate stats for unmapped listens
    unmapped_listens.createOrReplaceTempView("unmapped_listens")
    result = run_query("""
              WITH intermediate_table AS (
                SELECT user_name
                     , artist_name
                     , CASE
                         WHEN cardinality(artist_mbids) > 0 THEN NULL
                         ELSE nullif(artist_msid, '')
                       END as artist_msid
                     , artist_mbids
                  FROM unmapped_listens
              )
            SELECT *
                 , COUNT(*) AS listen_count
              FROM intermediate_table
          GROUP BY user_name
                 , artist_name
                 , artist_msid
                 , artist_mbids
            """)

    # Calculate stats for mapped listens and merge it with the stats for unmapped listens
    if use_mapping:
        mapped_listens.createOrReplaceTempView("mapped_listens")
        result.union(run_query("""
                  WITH intermediate_table AS (
                    SELECT user_name
                         , mb_artist_credit_name AS artist_name
                         , CASE
                             WHEN cardinality(artist_mbids) > 0 THEN artist_mbids
                             ELSE mb_artist_credit_mbids
                           END as artist_mbids
                         , NULL AS artist_msid
                      FROM mapped_listens
                  )
                SELECT *
                     , COUNT(*) AS listen_count
                  FROM intermediate_table
              GROUP BY user_name
                     , artist_name
                     , artist_mbids
            """))

    iterator = result \
        .withColumn("artists", struct("listen_count", "artist_name", "artist_msid", "artist_mbids")) \
        .groupBy("user_name") \
        .agg(sort_array(collect_list("artists"), asc=False).alias("artists")) \
        .toLocalIterator()

    return iterator
