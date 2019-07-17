import sys
import listenbrainz_spark
import time
import json
import logging
import pika

from collections import defaultdict
from listenbrainz_spark.stats_writer.stats_writer import StatsWriter
from listenbrainz_spark import config
from listenbrainz_spark.stats import run_query
from listenbrainz_spark.stats import adjusted_date
from datetime import datetime
from pyspark.sql.utils import AnalysisException
from py4j.protocol import Py4JJavaError

def get_artists(table):
    """
    Get artists information (artist_name, artist_msid etc) for every user
    ordered by listen count (number of times a user has listened to tracks
    which belong to a particular artist).

    Args:
        table: name of the temporary table.

    Returns:
        artists: A dict of dicts which can be depicted as:
                {
                    'user1': {
                        'artist_name' : 'xxxx',
                        'artist_msid' : 'xxxx',
                        'artist_mbids' : 'xxxx',
                        'count' : 'xxxx'
                    },
                    'user2' : {...}
                }
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
    Get recordings information (recording_name, recording_mbid etc) for every user
    ordered by listen count (number of times a user has listened to the track/recording).

    Args:
        table: name of the temporary table

    Returns:
        recordings: A dict of dicts which can be depicted as:
                {
                    'user1' : {
                        'track_name' : 'xxxx',
                        'recording_msid' : 'xxxx',
                        'recording_mbid' : 'xxxx',
                        'artist_name' : 'xxxx',
                        'artist_msid' : 'xxxx',
                        'artist_mbids' : 'xxxx',
                        'release_name' : 'xxxx',
                        'release_msid' : 'xxxx',
                        'release_mbid' : 'xxxx',
                        'count' : 'xxxx'
                    },
                    'user2' : {...},
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

def get_releases(table):
    """
    Get releases information (release_name, release_mbid etc) for every user
    ordered by listen count (number of times a user has listened to tracks
    which belong to a particular release).

    Args:
        table: name of the temporary table

    Returns:
        artists: A dict of dicts which can be depicted as:
                {
                    'user1' : {
                        'release_name' : 'xxxx',
                        'release_msid' : 'xxxx',
                        'release_mbid' : 'xxxx',
                        'artist_name' : 'xxxx',
                        'artist_msid' : 'xxxx',
                        'artist_mbids' : 'xxxx',
                        'count' : 'xxxx'
                    },
                    'user2' : {...},
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

def main():
    """
    Calculate statistics of users for previous month.

    Args:
        app_name: Application name to uniquely identify the submitted
                  application amongst other applications

    """
    t0 = time.time()
    try:
        listenbrainz_spark.init_spark_session('user')
    except Exception as err:
        logging.error("Cannot initialize spark session: %s / %s. Aborting." % (type(err).__name__, str(err)))
        sys.exit(-1)
    date = adjusted_date(-1)
    logging.info("Loading dataframe...")
    try:
        df = listenbrainz_spark.sql_context.read.parquet('{}/data/listenbrainz/{}/{}.parquet'.format(config.HDFS_CLUSTER_URI, date.year, date.month))
    except AnalysisException as err:
        logging.error("Cannot read files from HDFS: %s / %s. Aborting." % (type(err).__name__, str(err)))
        sys.exit(-1)
    df.printSchema()

    table = 'listens_{}'.format(datetime.strftime(date, '%Y_%m'))
    try:
        df.registerTempTable(table)
    except AnalysisException as err:
        logging.error("Cannot register dataframe: %s / %s. Aborting..." % (type(err).__name__, str(err)))
        sys.exit(-1)
    query_t0 = time.time()
    logging.info("DataFrame loaded and registered in %.2f s" % (query_t0 - t0))

    # data : Nested dict which can be depicted as:
    # {
    #   'user1' : {
    #       'artist' : {artists dict returned by func get_artists},
    #       'recordings' : {recordings dict returned by func get_recordings},
    #       'releases': {releases dict returned by func get_releasess},
    #       'yearmonth' : 'date when the stats were calculated'
    #   },
    #   'user2' : {...}
    # }
    data = defaultdict(dict)
    try:
        artist_data = get_artists(table)
    except Py4JJavaError as err:
        logging.error("Problem in getting artist data: %s / %s. Aborting..." % (type(err).__name__, str(err)))
        sys.exit(-1)

    for user_name, artist_stats in artist_data.items():
        data[user_name]['artists'] = {
            'artist_stats': artist_stats,
            'artist_count': len(artist_stats),
        }
    try:
        recording_data = get_recordings(table)
    except Py4JJavaError as err:
        logging.error("Problem in getting recording data: %s / %s. Aborting..." % (type(err).__name__, str(err)))
        sys.exit(-1)

    for user_name, recording_stats in recording_data.items():
        data[user_name]['recordings'] = recording_stats

    try:
        release_data = get_releases(table)
    except Py4JJavaError as err:
        logging.error("Problem in parsing release data: %s / %s. Aborting..." % (type(err).__name__, str(err)))
        sys.exit(-1)

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
            logging.info("Statistics of %s pushed to rabbitmq" % (user_name))
        except pika.exceptions.ConnectionClosed:
            logging.error("Connection to rabbitmq closed while trying to publish: Statistics of %s not published" % (user_name))
            continue
        except Exception as err:
            logging.error("Cannot publish statistics of %s to rabbitmq channel: %s / %s." % (user_name, type(err).__name__, str(err)), exc_info=True)
            continue
