from listenbrainz_spark.stats import run_query
from pyspark.sql.functions import collect_list, sort_array, struct


def get_releases(table):
    """
    Get release information (release_name, release_mbid etc) for every user
    ordered by listen count (number of times a user has listened to tracks
    which belong to a particular release).

    Args:
        table: name of the temporary table

    Returns:
        iterator (iter): an iterator over result
                {
                    'user1' : [{
                        'release_name': str
                        'release_msid': str,
                        'release_mbid': str,
                        'artist_name': str,
                        'artist_msid': str,
                        'artist_mbids': list(str),
                        'listen_count': int
                    }],
                    'user2' : [{...}],
                }
    """
    result = run_query("""
              WITH intermediate_table as (
                SELECT user_name
                     , nullif(release_name, '') as release_name
                     , CASE
                         WHEN release_mbid IS NOT NULL AND release_mbid != '' THEN NULL
                         ELSE nullif(release_msid, '')
                       END as release_msid
                     , nullif(release_mbid, '') as release_mbid
                     , artist_name
                     , CASE
                         WHEN cardinality(artist_mbids) > 0 THEN NULL
                         ELSE nullif(artist_msid, '')
                       END as artist_msid
                     , artist_mbids
                  FROM {}
              )
            SELECT *
                 , count(*) as listen_count
              FROM intermediate_table
             WHERE release_name IS NOT NULL
          GROUP BY user_name
                 , release_name
                 , release_msid
                 , release_mbid
                 , artist_name
                 , artist_msid
                 , artist_mbids
        """.format(table))

    iterator = result \
        .withColumn("releases", struct("listen_count", "release_name", "release_msid", "release_mbid", "artist_name",
                                       "artist_msid", "artist_mbids")) \
        .groupBy("user_name") \
        .agg(sort_array(collect_list("releases"), asc=False).alias("releases")) \
        .toLocalIterator()

    return iterator
