import time

from listenbrainz_spark import session

from collections import defaultdict

def get_artists(df):
    """
    Get artist information (artist_name, artist_msid etc) for every user
    ordered by listen count (number of times a user has listened to tracks
    which belong to a particular artist).

    Args:
        table: name of the temporary table.

    Returns:
        artists: A dict of dicts which can be depicted as:
                {
                    'user1': [{
                        'artist_name': str,
                        'artist_msid': str,
                        'artist_mbids': str,
                        'listen_count': int
                    }],
                    'user2' : [{...}]
                }
    """
    t0 = time.time()
    df = df.select("user_name","artist_name","artist_msid","artist_mbids")
    df = df.groupBy("user_name","artist_name","artist_msid","artist_mbids").count()
    df = df.sort(df['count'].desc())
    rows = df.collect() 
    artists = defaultdict(list)
    for row in rows:
        artists[row.user_name].append({
            'artist_name': row.artist_name,
            'artist_msid': row.artist_msid,
            'artist_mbids': row.artist_mbids,
            'listen_count': row['count']
        })
    print("Query to calculate artist stats processed in %.2f s" % (time.time() - t0))
    return artists


def get_recordings(df):
    """
    Get recording information (recording_name, recording_mbid etc) for every user
    ordered by listen count (number of times a user has listened to the track/recording).

    Args:
        table: name of the temporary table

    Returns:
        recordings: A dict of dicts which can be depicted as:
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
    t0 = time.time()
    df = df.select("user_name", "artist_name", "artist_msid", "artist_mbids", "track_name", "recording_msid", "recording_mbid", "release_name", "release_mbid", "release_msid")
    df = df.groupBy("user_name", "artist_name", "artist_msid", "artist_mbids", "release_name", "release_mbid", "release_msid", "recording_msid", "recording_mbid", "track_name").count()
    df = df.sort(df['count'].desc())
    rows = df.collect()
    recordings = defaultdict(list)
    for row in rows:
        recordings[row.user_name].append({
            'track_name': row.track_name,
            'recording_msid': row.recording_msid,
            'recording_mbid': row.recording_mbid,
            'artist_name': row.artist_name,
            'artist_msid': row.artist_msid,
            'artist_mbids': row.artist_mbids,
            'release_name': row.release_name,
            'release_msid': row.release_msid,
            'release_mbid': row.release_mbid,
            'listen_count': row['count'],
        })
    print("Query to calculate recording stats processed in %.2f s" % (time.time() - t0))
    return recordings


def get_releases(df):
    """
    Get release information (release_name, release_mbid etc) for every user
    ordered by listen count (number of times a user has listened to tracks
    which belong to a particular release).

    Args:
        table: name of the temporary table

    Returns:
        artists: A dict of dicts which can be depicted as:
                {
                    'user1' : [{
                        'release_name': str
                        'release_msid': str,
                        'release_mbid': str,
                        'artist_name': str,
                        'artist_msid': str,
                        'artist_mbids': str,
                        'listen_count': int
                    }],
                    'user2' : [{...}],
                }
    """
    t0 = time.time()
    df = df.select("user_name", "artist_name", "artist_msid", "artist_mbids", "release_name", "release_mbid", "release_msid")
    df = df.groupBy("user_name", "artist_name", "artist_msid", "artist_mbids", "release_name", "release_mbid", "release_msid").count()
    df = df.sort(df['count'].desc())
    rows = df.collect()
    releases = defaultdict(list)
    for row in rows:
        releases[row.user_name].append({
            'release_name': row.release_name,
            'release_msid': row.release_msid,
            'release_mbid': row.release_mbid,
            'artist_name': row.artist_name,
            'artist_msid': row.artist_msid,
            'artist_mbids': row.artist_mbids,
            'listen_count': row['count'],
        })
    print("Query to calculate release stats processed in %.2f s" % (time.time() - t0))
    return releases
