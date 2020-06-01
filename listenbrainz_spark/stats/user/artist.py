from listenbrainz_spark.stats import run_query
from pyspark.sql.functions import collect_list, struct


def get_artists(table):
    """ Get artist information (artist_name, artist_msid etc) for every user
        ordered by listen count

        Args:
            table (str): name of the temporary table.

        Returns:
            iterator (iter): an iterator over result, the structure 
                of the result is as follows:
                    {
                        user1: [
                            {
                                artist_name: "artist1",
                                artist_msid: "msid1",
                                artist_mbids: ["mbid1"],
                                listen_count: 10
                            },
                            ...
                        ],
                        ...
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
          ORDER BY cnt DESC
            """.format(table=table))

    iterator = result.withColumn("artist", struct("artist_name", "artist_msid", "artist_mbids", "cnt")).\
        groupBy("user_name").agg(collect_list("artist").alias("artist")).toLocalIterator()

    return iterator
