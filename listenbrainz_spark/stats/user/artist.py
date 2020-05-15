import time
from datetime import datetime

from collections import defaultdict
from listenbrainz_spark.utils import get_listens
from listenbrainz_spark.stats import adjust_months, adjust_days
from listenbrainz_spark.path import LISTENBRAINZ_DATA_DIRECTORY
from listenbrainz_spark.constants import LAST_FM_FOUNDING_YEAR


def get_artists(from_date=None, to_date=None):
    """ Get artist information (artist_name, artist_msid etc) for every user
        ordered by listen count in a particular time range.

        Args:
            table (str): name of the temporary table.
            from_date (str): UNIX timestamp of start time, defaults to LAST_FM_FOUNDING_YEAR
            to_date (str): UNIX timestamp of end time, defaults to NOW

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

    if from_date is None:
        from_date = datetime(LAST_FM_FOUNDING_YEAR, 1, 1)

    if to_date is None:
        to_date = datetime.now()

    listens_df = get_listens(from_date, to_date, LISTENBRAINZ_DATA_DIRECTORY)

    result = listens_df.filter(listens_df.listened_at.between(from_date, to_date)).groupBy(
        'user_name', 'artist_name', 'artist_msid', 'artist_mbids').count().orderBy('count', ascending=False)

    rows = result.collect()
    artists = defaultdict(list)
    for row in rows:
        artists[row.user_name].append({
            'artist_name': row['artist_name'],
            'artist_msid': row['artist_msid'],
            'artist_mbids': row['artist_mbids'],
            'listen_count': row['count'],
        })
    print("Query to calculate artist stats processed in %.2f s" % (time.time() - t0))
    return artists


def get_artists_last_week():
    from_date = adjust_days(datetime.now(), 7)
    to_date = datetime.now()
    return get_artists(from_date, to_date)


def get_artists_last_month():
    from_date = adjust_months(datetime.now(), 1)
    to_date = datetime.now()
    return get_artists(from_date, to_date)


def get_artists_last_year():
    from_date = adjust_months(datetime.now(), 12)
    to_date = datetime.now()
    return get_artists(from_date, to_date)


def get_artists_all_time():
    return get_artists()
