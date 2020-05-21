import time
from collections import defaultdict
from datetime import datetime

from flask import current_app

from listenbrainz_spark.constants import LAST_FM_FOUNDING_YEAR
from listenbrainz_spark.path import LISTENBRAINZ_DATA_DIRECTORY
from listenbrainz_spark.stats import (adjust_days, replace_days,
                                      replace_months, run_query)
from listenbrainz_spark.stats.user.utils import (filter_listens,
                                                 get_last_monday,
                                                 get_latest_listen_ts,
                                                 create_messages)
from listenbrainz_spark.utils import get_listens


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


def get_releases_week():
    """ Get the week top releases for all users """
    current_app.logger.debug("Calculating release_week...")

    date = get_latest_listen_ts()

    to_date = get_last_monday(date)
    from_date = adjust_days(to_date, 7)

    listens_df = get_listens(from_date, to_date, LISTENBRAINZ_DATA_DIRECTORY)
    filtered_df = filter_listens(listens_df, from_date, to_date)
    filtered_df.createOrReplaceTempView('user_releases_week')

    release_data = get_releases('user_releases_week')
    messages = create_messages(data=release_data, entity='releases', stats_type='user_releases', stats_range='week',
                               from_ts=from_date.timestamp(), to_ts=to_date.timestamp())

    current_app.logger.debug("Done!")

    return messages


def get_releases_month():
    """ Get the month top releases for all users """
    current_app.logger.debug("Calculating release_month...")

    to_date = get_latest_listen_ts()
    from_date = replace_days(to_date, 1)

    listens_df = get_listens(from_date, to_date, LISTENBRAINZ_DATA_DIRECTORY)
    listens_df.createOrReplaceTempView('user_releases_month')

    release_data = get_releases('user_releases_month')

    messages = create_messages(data=release_data, entity='releases', stats_type='user_releases', stats_range='month',
                               from_ts=from_date.timestamp(), to_ts=to_date.timestamp())

    current_app.logger.debug("Done!")

    return messages


def get_releases_year():
    """ Get the year top releases for all users """
    current_app.logger.debug("Calculating release_year...")

    to_date = get_latest_listen_ts()
    from_date = replace_days(replace_months(to_date, 1), 1)

    listens_df = get_listens(from_date, to_date, LISTENBRAINZ_DATA_DIRECTORY)
    listens_df.createOrReplaceTempView('user_releases_year')

    release_data = get_releases('user_releases_year')
    messages = create_messages(data=release_data, entity='releases', stats_type='user_releases', stats_range='year',
                               from_ts=from_date.timestamp(), to_ts=to_date.timestamp())

    current_app.logger.debug("Done!")

    return messages


def get_releases_all_time():
    """ Get the all_time top releases for all users """
    current_app.logger.debug("Calculating release_all_time...")

    to_date = get_latest_listen_ts()
    from_date = datetime(LAST_FM_FOUNDING_YEAR, 1, 1)

    listens_df = get_listens(from_date, to_date, LISTENBRAINZ_DATA_DIRECTORY)
    listens_df.createOrReplaceTempView('user_releases_all_time')

    release_data = get_releases('user_releases_all_time')
    messages = create_messages(data=release_data, entity='releases', stats_type='user_releases', stats_range='all_time',
                               from_ts=from_date.timestamp(), to_ts=to_date.timestamp())

    current_app.logger.debug("Done!")

    return messages
