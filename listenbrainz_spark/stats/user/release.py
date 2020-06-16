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
            SELECT user_name
                 , nullif(release_name, '') as release_name
                 , nullif(release_msid, '') as release_msid
                 , nullif(release_mbid, '') as release_mbid
                 , artist_name
                 , nullif(artist_msid, '') as artist_msid
                 , artist_mbids
                 , count(release_name) as listen_count
              FROM {}
             WHERE release_name IS NOT NULL AND release_name != ''
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
