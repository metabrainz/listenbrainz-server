import sys
import listenbrainz_spark
import time
import json
import logging

from collections import defaultdict
from listenbrainz_spark.stats_writer.stats_writer import StatsWriter
from listenbrainz_spark import config
from listenbrainz_spark.stats import run_query
from listenbrainz_spark.stats import date_for_stats_calculation
from datetime import datetime

def get_artists(table):
    """
    Args:
        table: name of the temporary table

    Returns:
        artists: A dict of dicts containing artists information of every user 
            ordered by listen count (number of times a user has listened to 
            tracks which belong to a particular artist).
            The dict can be depicted as:
                {'user1' : {'artist_name' : 'xxxx', 'artist_msid' : 'xxxx',
                    'artist_mbids' : 'xxxx', 'count' : 'xxxx'}, 'user2' : {...}}
    """
    t0 = time.time()
    query = run_query("""
            SELECT user_name
                 , artist_name
                 , artist_msid
                 , artist_mbids
                 , count(artist_name) as cnt
              FROM %s
          GROUP BY user_name, artist_name, artist_msid, artist_mbids
          ORDER BY cnt DESC
        """ % (table))
    rows = query.collect()
    artists = defaultdict(list)
    for row in rows:
        artists[row.user_name].append({
            'artist_name': row.artist_name,
            'artist_msid': row.artist_msid,
            'artist_mbids': row.artist_mbids,
            'listen_count': row.cnt,
        })
    print("Query to calculate artist stats processed in %.2f s" % (time.time() - t0))
    return artists


def get_recordings(table):
    """
    Args:
        table: name of the temporary table

    Returns:
        recordings: A dict of dicts containing recordings information for every user
            ordered by listen count (number of times a user has listened to the 
            track/recording).
            The dict can be depicted as:
                {'user1' : {'track_name' : 'xxxx', 'recording_msid' : 'xxxx',
                    'recording_mbid' : 'xxxx', 'artist_name' : 'xxxx', 'artist_msid' : 
                    'xxxx', 'artist_mbids' : 'xxxx', 'release_name' : 'xxxx', 
                    'release_msid' : 'xxxx', 'release_mbid' : 'xxxx', 'count' : 'xxxx'},
                     'user2' : {...}}
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

def get_releases(table):
    """
    Args:
        table: name of the temporary table

    Returns:
        artists: A dict od dicts containing release information for every user 
            ordered by listen count (number of times a user has listened to tracks 
            which belong to a particular release).
            The dict can be depicted as:
                {'user1' : {'release_name' : 'xxxx', 'release_msid' : 'xxxx',
                    'release_mbid' : 'xxxx', 'artist_name' : 'xxxx', 'artist_msdid' : 
                    'xxxx', 'artist_mbids' : 'xxxx', count' : 'xxxx'}, 'user2' : {...}}
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
          GROUP BY user_name, release_name, release_msid, release_mbid, artist_name, artist_msid, artist_mbids
          ORDER BY cnt DESC
        """ % (table))
    rows = query.collect()
    releases = defaultdict(list)
    for row in rows:
        releases[row.user_name].append({
            'release_name': row.release_name,
            'release_msid': row.release_msid,
            'release_mbid': row.release_mbid,
            'artist_name': row.artist_name,
            'artist_msid': row.artist_msid,
            'artist_mbids': row.artist_mbids,
            'listen_count': row.cnt,
        })
    print("Query to calculate release stats processed in %.2f s" % (time.time() - t0))
    return releases

def main(app_name):
    """
    Args:
        app_name: Application name to uniquely identify the submitted
                  application amongst other applications

        The script will be run to calculate stats for previous month.

    """
    t0 = time.time()
    try:
        listenbrainz_spark.init_spark_session(app_name)
    except Exception as err:
        logging.error("Cannot initialize spark session: %s / %s. Aborting." % (type(err).__name__, str(err)))
        sys.exit(-1)
    date = date_for_stats_calculation()
    try:
        df = listenbrainz_spark.sql_context.read.parquet('{}/data/listenbrainz/{}/{}.parquet'.format(config.HDFS_CLUSTER_URI, date.year, date.month))
        print("Loading dataframe...")
    except Exception as err:
        logging.error("Cannot read files from HDFS: %s / %s. Aborting." % (type(err).__name__, str(err)))
        sys.exit(-1)
    df.printSchema()

    table = 'listens_{}'.format(datetime.strftime(date, '%Y_%m'))
    print(table)
    df.registerTempTable(table)
    print("Running Query...")
    query_t0 = time.time()
    print("DataFrame loaded in %.2f s" % (query_t0 - t0))

    data = defaultdict(dict)
    """
        data : Nested dict which can be depicted as:
                {'user1' : {'artist' : {artists dict returned by func get_artists},
                 'recordings' : {recordings dict returned by func get_recordings}, 
                 'releases': {releases dict returned by func get_releasess}, 'yearmonth' : 
                 'date when the stats were calculated'}, 'user2' : {...}} 
    """
    artist_data = get_artists(table)
    for user_name, artist_stats in artist_data.items():
        data[user_name]['artists'] = {
            'artist_stats': artist_stats,
            'artist_count': len(artist_stats),
        }

    recording_data = get_recordings(table)
    for user_name, recording_stats in recording_data.items():
        data[user_name]['recordings'] = recording_stats

    release_data = get_releases(table)
    for user_name, release_stats in release_data.items():
        data[user_name]['releases'] = release_stats

    rabbbitmq_conn_obj = StatsWriter()
    yearmonth = datetime.strftime(date, '%Y-%m')
    for user_name, metadata in data.items():
        data[user_name]['yearmonth'] = yearmonth
        rabbitmq_data = {
            'type' : 'user',
            user_name : metadata,
        }
        try:
            rabbbitmq_conn_obj.start(rabbitmq_data)
            print("Statistics of %s pushed to rabbitmq" % (user_name))
        except Exception as err:
            logging.error("Cannot publish statistics of %s to rabbitmq channel: %s / %s." % (user_name, type(err).__name__, str(err)), exc_info=True)
            continue
            