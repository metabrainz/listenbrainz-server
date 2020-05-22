import time
from collections import defaultdict

from listenbrainz_spark.stats import run_query


def get_artists(table):
    """ Get artist information (artist_name, artist_msid etc) for every user
        ordered by listen count

        Args:
            table (str): name of the temporary table.

        Returns:
            artists: A dict of dicts which can be depicted as:
                    {
                        'user1': [{
                            'artist_name': str, 'artist_msid': str, 'artist_mbids': str, 'listen_count': int
                        }],
                        'user2' : [{...}]
                    }
    """

    t0 = time.time()

    result = run_query("""
            SELECT user_name
                 , artist_name
                 , artist_msid
                 , artist_mbids
                 , count(artist_name) as cnt
              FROM {table}
          GROUP BY user_name
                 , artist_name
                 , artist_msid
                 , artist_mbids
          ORDER BY cnt DESC
            """.format(table=table))

    rows = result.collect()
    artists = defaultdict(list)
    for row in rows:
        artists[row.user_name].append({
            'artist_name': row['artist_name'],
            'artist_msid': row['artist_msid'],
            'artist_mbids': row['artist_mbids'],
            'listen_count': row['cnt'],
        })
    print("Query to calculate artist stats processed in %.2f s" % (time.time() - t0))
    return artists
