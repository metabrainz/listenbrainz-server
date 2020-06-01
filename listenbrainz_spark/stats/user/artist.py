from listenbrainz_spark.stats import run_query
from pyspark.sql.functions import collect_list, sort_array, struct


def get_artists(table):
    """ Get artist information (artist_name, artist_msid etc) for every user
        ordered by listen count

        Args:
            table (str): name of the temporary table.

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

    result = run_query("""
            SELECT user_name
                 , artist_name
                 , artist_msid
                 , artist_mbids
                 , count(artist_name) as listen_count
              FROM {table}
          GROUP BY user_name
                 , artist_name
                 , artist_msid
                 , artist_mbids
          ORDER BY listen_count DESC
            """.format(table=table))

    iterator = result \
        .withColumn("artists", struct("listen_count", "artist_name", "artist_msid", "artist_mbids")) \
        .groupBy("user_name") \
        .agg(sort_array(collect_list("artists"), asc=False).alias("artists")) \
        .toLocalIterator()

    return iterator
