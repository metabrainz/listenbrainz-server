import time
from collections import defaultdict

from listenbrainz_spark.stats import run_query


def get_releases(table):
    """
    Get release information (release_name, release_mbid etc) for every user
    ordered by listen count (number of times a user has listened to tracks
    which belong to a particular release).

    Args:
        table: name of the temporary table

    Returns:
        releases: A dict of dicts which can be depicted as:
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
    t0 = time.time()
    query = run_query("""
            SELECT user_name
                 , release_name
                 , release_msid
                 , release_mbid
                 , artist_name
                 , artist_msid
                 , artist_mbids
                 , count(release_msid) as cnt
              FROM %s
          GROUP BY user_name
                 , release_name
                 , release_msid
                 , release_mbid
                 , artist_name
                 , artist_msid
                 , artist_mbids
          ORDER BY cnt DESC
        """ % (table))
    rows = query.collect()
    releases = defaultdict(list)
    for row in rows:
        releases[row['user_name']].append({
            'release_name': row['release_name'],
            'release_msid': row['release_msid'],
            'release_mbid': row['release_mbid'],
            'artist_name': row['artist_name'],
            'artist_msid': row['artist_msid'],
            'artist_mbids': row['artist_mbids'],
            'listen_count': row['cnt'],
        })
    print("Query to calculate release stats processed in %.2f s" % (time.time() - t0))
    return releases
