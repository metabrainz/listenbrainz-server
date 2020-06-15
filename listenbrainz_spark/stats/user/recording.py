from listenbrainz_spark.stats import run_query
from pyspark.sql.functions import collect_list, sort_array, struct


def get_recordings(table):
    """
    Get recording information (recording_name, recording_mbid etc) for every user
    ordered by listen count (number of times a user has listened to the track/recording).

    Args:
        table: name of the temporary table

    Returns:
        iterator (iter): an iterator over result:
                {
                    'user1' : [{
                        'track_name': str,
                        'recording_msid': str,
                        'recording_mbid': str,
                        'artist_name': str,
                        'artist_msid': str,
                        'artist_mbids': str,
                        'release_name': str,
                        'release_msid': str,
                        'release_mbid': str,
                        'listen_count': int
                    }],
                    'user2' : [{...}],
                }
    """
    result = run_query("""
            SELECT user_name
                 , track_name
                 , nullif(recording_msid, '') as recording_msid
                 , nullif(recording_mbid, '') as recording_mbid
                 , artist_name
                 , nullif(artist_msid, '') as artist_msid
                 , artist_mbids
                 , nullif(release_name, '') as release_name
                 , nullif(release_msid, '') as release_msid
                 , nullif(release_mbid, '') as release_mbid
                 , count(track_name) as listen_count
              FROM {}
          GROUP BY user_name
                 , track_name
                 , recording_msid
                 , recording_mbid
                 , artist_name
                 , artist_msid
                 , artist_mbids
                 , release_name
                 , release_msid
                 , release_mbid
        """.format(table))

    iterator = result \
        .withColumn("recordings", struct("listen_count", "track_name", "recording_msid", "recording_mbid", "artist_name",
                                         "artist_msid", "artist_mbids", "release_name", "release_msid", "release_mbid")) \
        .groupBy("user_name") \
        .agg(sort_array(collect_list("recordings"), asc=False).alias("recordings")) \
        .toLocalIterator()

    return iterator
