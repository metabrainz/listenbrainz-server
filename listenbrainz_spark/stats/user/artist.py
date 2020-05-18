import time
from collections import defaultdict
from datetime import datetime
from flask import current_app

from listenbrainz_spark.constants import LAST_FM_FOUNDING_YEAR
from listenbrainz_spark.path import LISTENBRAINZ_DATA_DIRECTORY
from listenbrainz_spark.stats import replace_months, run_query, adjust_days
from listenbrainz_spark.stats.user.utils import filter_listens, get_latest_listen_ts
from listenbrainz_spark.utils import get_listens


def get_artists(table):
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


def get_artists_last_week():
    current_app.logger.debug("Calculating artist_last_week...")

    date = get_latest_listen_ts()

    # Get date for Monday before "date"
    to_date = adjust_days(date, date.weekday())
    from_date = adjust_days(to_date, 7)

    listens_df = get_listens(from_date, to_date, LISTENBRAINZ_DATA_DIRECTORY)
    filtered_df = filter_listens(listens_df, from_date, to_date)
    filtered_df.createOrReplaceTempView('user_artists_last_week')

    artist_data = get_artists('user_artists_last_week')
    messages = create_messages(artist_data, 'user_artists', 'last_week')

    current_app.logger.debug("Done!")

    return messages


def get_artists_last_month():
    current_app.logger.debug("Calculating artist_last_month...")

    date = get_latest_listen_ts()

    listens_df = get_listens(date, date, LISTENBRAINZ_DATA_DIRECTORY)
    listens_df.createOrReplaceTempView('user_artists_last_month')

    artist_data = get_artists('user_artists_last_month')
    messages = create_messages(artist_data, 'user_artists', 'last_month')

    current_app.logger.debug("Done!")

    return messages


def get_artists_last_year():
    current_app.logger.debug("Calculating artist_last_year...")

    to_date = get_latest_listen_ts()
    from_date = replace_months(to_date, 1)

    listens_df = get_listens(from_date, to_date, LISTENBRAINZ_DATA_DIRECTORY)
    listens_df.createOrReplaceTempView('user_artists_last_year')

    artist_data = get_artists('user_artists_last_year')
    messages = create_messages(artist_data, 'user_artists', 'last_year')

    current_app.logger.debug("Done!")

    return messages


def get_artists_all_time():
    current_app.logger.debug("Calculating artist_all_time...")

    from_date = datetime(LAST_FM_FOUNDING_YEAR, 1, 1)
    to_date = datetime.now()

    listens_df = get_listens(from_date, to_date, LISTENBRAINZ_DATA_DIRECTORY)
    listens_df.createOrReplaceTempView('user_artists_all_time')

    artist_data = get_artists('user_artists_all_time')
    messages = create_messages(artist_data, 'user_artists', 'all_time')

    current_app.logger.debug("Done!")

    return messages


def create_messages(artist_data, _type, _range):
    messages = []
    for user_name, user_artists in artist_data.items():
        messages.append({
            'musicbrainz_id': user_name,
            'type': _type,
            'range': _range,
            'artists': user_artists,
            'count': len(user_artists)
        })

    return messages
