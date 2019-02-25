import sys
import listenbrainz_spark
import time
import json

from collections import defaultdict
from datetime import datetime
from dateutil.relativedelta import relativedelta
from listenbrainz_spark.stats_writer.stats_writer import StatsWriter
from listenbrainz_spark import config
from listenbrainz_spark.stats import run_query

data = defaultdict(dict)

def get_artists(table):
    """
    Args:
        table: name of the temporary table
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
    t = time.time()
    rows = query.collect()
    artists = defaultdict(list)
    print("time taken by collect call: %.2f" % (time.time() - t))
    for row in rows:
        artists[row.user_name].append({
            'artist_name': row.artist_name,
            'artist_msid': row.artist_msid,
            'artist_mbids': row.artist_mbids,
            'listen_count': row.cnt,
        })
    for user_name, artist_stats in artists.items():
        data[user_name]['artists'] = {}
        data[user_name]['artists']['artist_stats'] = artist_stats
        data[user_name]['artists']['artist_count'] = len(artist_stats)
    query_t0 = time.time()
    print("Query to calculate artist stats processed in %.2f s" % (query_t0 - t0))


def get_recordings(table):
    """
    Args:
        table: name of the temporary table
    """
    t0 = time.time()
    query = run_query("""
            SELECT user_name
                 , track_name
                 , recording_msid
                 , recording_mbid
                 , count(recording_msid) as cnt
              FROM %s
          GROUP BY user_name, track_name, recording_msid, recording_mbid
          ORDER BY cnt DESC
        """ % (table))
    t = time.time()
    rows = query.collect()
    recordings = defaultdict(list)
    print("time taken by collect call: %.2f" % (time.time() - t))
    for row in rows:
        recordings[row.user_name].append({
            'track_name': row.track_name,
            'recording_msid': row.recording_msid,
            'recording_mbid': row.recording_mbid,
            'listen_count': row.cnt,
        })
    for user_name, recording_stats in recordings.items():
        data[user_name]['recordings'] = {}
        data[user_name]['recordings'] = recording_stats
    query_t0 = time.time()
    print("Query to calculate artist stats processed in %.2f s" % (query_t0 - t0))

def get_releases(table):
    """
    Args:
        table: name of the temporary table
    """
    t0 = time.time()
    query = run_query("""
            SELECT user_name
                 , release_name
                 , release_msid
                 , release_mbid
                 , count(release_msid) as cnt
              FROM %s
          GROUP BY user_name, release_name, release_msid, release_mbid
          ORDER BY cnt DESC
        """ % (table))
    releases = defaultdict(list)
    t = time.time()
    rows = query.collect()
    releases = defaultdict(list)
    print("time taken by collect call: %.2f" % (time.time() - t))
    for row in rows:
        releases[row.user_name].append({
            'release_name': row.release_name,
            'release_msid': row.release_msid,
            'release_mbid': row.release_mbid,
            'listen_count': row.cnt,
        })
    for user_name, release_stats in releases.items():
        data[user_name]['releases'] = {}
        data[user_name]['releases'] = release_stats
    query_t0 = time.time()
    print("Query to calculate artist stats processed in %.2f s" % (query_t0 - t0))


def get_users(table):
    """ DataFrame is registered as a temporary table
    Args:
        table : name of the temporary table

    Returns:
        users: list containing user names of all the users
    """
    t0 = time.time()
    query = run_query("""
            SELECT DISTINCT user_name
              FROM %s
        """ % table)
    users = [row.user_name for row in query.collect()]
    query_t0 = time.time()
    query.show()
    print("Query to get list of users processed in %.2f s" % (query_t0 - t0))
    return users

def main(app_name):
    """
    Args:
        app_name: Application name to uniquely identify the submitted
                  application amongst other applications
    """
    t0 = time.time()
    listenbrainz_spark.init_spark_session(app_name)
    t = datetime.utcnow().replace(day=1)
    date = t + relativedelta(months=-1)
    try:
        df = listenbrainz_spark.sql_context.read.parquet('{}/data/listenbrainz/{}/{}.parquet'.format(config.HDFS_CLUSTER_URI, date.year, date.month))
        print("Loading dataframe...")
    except:
        print ("No Listens for last month")
        sys.exit(-1)
    df.printSchema()
    print(df.columns)
    print(df.count())
    table = 'listens_{}'.format(datetime.strftime(date, '%Y_%m'))
    print(table)
    df.registerTempTable(table)
    print("Running Query...")
    query_t0 = time.time()
    print("DataFrame loaded in %.2f s" % (query_t0 - t0))
    users = get_users(table)
    print("Number of users: %d" % len(users))
    get_artists(table)
    get_recordings(table)
    get_releases(table)
    rabbbitmq_conn_obj = StatsWriter()
    yearmonth = datetime.strftime(date, '%Y-%m')
    for user_name, metadata in data.items():
        data[user_name]['yearmonth'] = yearmonth
        rabbitmq_data = {}
        rabbitmq_data[user_name] = metadata
        rabbbitmq_conn_obj.start(rabbitmq_data)

    
