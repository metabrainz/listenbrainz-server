import time
from collections import defaultdict
from datetime import datetime

from listenbrainz_spark.exceptions import HDFSException
from listenbrainz_spark.path import LISTENBRAINZ_DATA_DIRECTORY
from listenbrainz_spark.stats import adjust_days, adjust_months, run_query
from listenbrainz_spark.utils import get_listens


def get_latest_listen_ts():
    """ Get the timestamp of the latest timestamp present in spark cluster """
    now = datetime.now()
    while True:
        try:
            df = get_listens(now, now, LISTENBRAINZ_DATA_DIRECTORY)
            break
        except HDFSException:
            now = adjust_months(now, 1)

    df.createOrReplaceTempView('latest_listen_ts')
    result = run_query("SELECT MAX(listened_at) as max_timestamp FROM latest_listen_ts")
    rows = result.collect()
    return rows[0]['max_timestamp']


def filter_listens(df, from_date, to_date):
    """
    Filter the given dataframe to return listens which lie between from_date and to_date

    Args:
        df: Dataframe which has to filtered
        from_time(datetime): Start date
        to_time(datetime): End date

    Returns:
        result: Dateframe with listens which lie beween from_date and to_date
    """
    result = df.filter(df.listened_at.between(from_date, to_date))
    return result


def get_last_monday(date):
    """ Get date for Monday before 'date' """
    return adjust_days(date, date.weekday())


def create_messages(data, entity, stats_type, stats_range, from_ts, to_ts):
    """
    Create messages to send the data to the webserver via RabbitMQ

    Args:
        release_data (dict): Data to sent to the webserver
        entity (str): The entity for which statistics are calculated, i.e 'artists',
            'releases' or 'recordings'
        stats_type (str): The type of statistics calculated
        stats_range (str): The range for which the statistics have been calculated
        from_ts (int): The UNIX timestamp of start time of the stats
        to_ts (int): The UNIX timestamp of end time of the stats

    Returns:
        messages (list): A list of messages to be sent via RabbitMQ
    """
    messages = []
    for user_name, user_releases in data.items():
        messages.append({
            'musicbrainz_id': user_name,
            'type': stats_type,
            'range': stats_range,
            'from': from_ts,
            'to': to_ts,
            entity: user_releases,
            'count': len(user_releases)
        })

    return messages


def get_recordings(table):
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
    query = run_query("""
            SELECT user_name
                 , track_name
                 , recording_msid
                 , recording_mbid
                 , artist_name
                 , artist_msid
                 , artist_mbids
                 , release_name
                 , release_msid
                 , release_mbid
                 , count(recording_msid) as cnt
              FROM %s
          GROUP BY user_name, track_name, recording_msid, recording_mbid, artist_name, artist_msid,
                artist_mbids, release_name, release_msid, release_mbid
          ORDER BY cnt DESC
        """ % (table))
    rows = query.collect()
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
            'listen_count': row.cnt,
        })
    print("Query to calculate recording stats processed in %.2f s" % (time.time() - t0))
    return recordings

