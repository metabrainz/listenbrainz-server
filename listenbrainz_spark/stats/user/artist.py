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


def get_artists_week():
    """ Get the week top artists for all users """
    current_app.logger.debug("Calculating artist_week...")

    date = get_latest_listen_ts()

    to_date = get_last_monday(date)
    from_date = adjust_days(to_date, 7)

    listens_df = get_listens(from_date, to_date, LISTENBRAINZ_DATA_DIRECTORY)
    filtered_df = filter_listens(listens_df, from_date, to_date)
    filtered_df.createOrReplaceTempView('user_artists_week')

    artist_data = get_artists('user_artists_week')
    messages = create_messages(data=artist_data, entity='artists', stats_type='user_artists', stats_range='week',
                               from_ts=from_date.timestamp(), to_ts=to_date.timestamp())

    current_app.logger.debug("Done!")

    return messages


def get_artists_month():
    """ Get the month top artists for all users """
    current_app.logger.debug("Calculating artist_month...")

    to_date = get_latest_listen_ts()
    from_date = replace_days(to_date, 1)

    listens_df = get_listens(from_date, to_date, LISTENBRAINZ_DATA_DIRECTORY)
    listens_df.createOrReplaceTempView('user_artists_month')

    artist_data = get_artists('user_artists_month')

    messages = create_messages(data=artist_data, entity='artists', stats_type='user_artists', stats_range='month',
                               from_ts=from_date.timestamp(), to_ts=to_date.timestamp())

    current_app.logger.debug("Done!")

    return messages


def get_artists_year():
    """ Get the year top artists for all users """
    current_app.logger.debug("Calculating artist_year...")

    to_date = get_latest_listen_ts()
    from_date = replace_days(replace_months(to_date, 1), 1)

    listens_df = get_listens(from_date, to_date, LISTENBRAINZ_DATA_DIRECTORY)
    listens_df.createOrReplaceTempView('user_artists_year')

    artist_data = get_artists('user_artists_year')
    messages = create_messages(data=artist_data, entity='artists', stats_type='user_artists', stats_range='year',
                               from_ts=from_date.timestamp(), to_ts=to_date.timestamp())

    current_app.logger.debug("Done!")

    return messages


def get_artists_all_time():
    """ Get the all_time top artists for all users """
    current_app.logger.debug("Calculating artist_all_time...")

    to_date = get_latest_listen_ts()
    from_date = datetime(LAST_FM_FOUNDING_YEAR, 1, 1)

    listens_df = get_listens(from_date, to_date, LISTENBRAINZ_DATA_DIRECTORY)
    listens_df.createOrReplaceTempView('user_artists_all_time')

    artist_data = get_artists('user_artists_all_time')
    messages = create_messages(data=artist_data, entity='artists', stats_type='user_artists', stats_range='all_time',
                               from_ts=from_date.timestamp(), to_ts=to_date.timestamp())

    current_app.logger.debug("Done!")

    return messages

