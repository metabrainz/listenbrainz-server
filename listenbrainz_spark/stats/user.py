import sys
import listenbrainz_spark
import time
from collections import defaultdict
from datetime import datetime
from listenbrainz_spark.stats_writer.stats_writer import StatsWriter
from listenbrainz_spark import config
from listenbrainz_spark.stats import run_query

LIMIT = 100
USER_BATCH_SIZE = 100
month = datetime.now().month
year = datetime.now().year


def get_artist_count(user_name, table):
    """
    Args:
        user_name: name of the user
        table: name of the temporary table

    Returns:
        count: listen_count of the previous month
    """
    t0 = time.time()
    query = run_query("""
            SELECT count(*) as cnt
              FROM (SELECT DISTINCT artist_name from %s where user_name = '%s')
        """ % (table, user_name))
    count = query.collect()[0].cnt
    query_t0 = time.time()
    print("Query to calculate listen count proccessed in %.2f s" % (query_t0 - t0))
    return count


def get_artists(user_names, table):
    """
    Args:
        user_names ([str]): list of usernames
        table: name of the temporary table

    Returns:
        artist (dict): listen_count and statistics
               of top 20 artists listened in the previous month
    """
    t0 = time.time()
    batch_df = None
    for name in user_names:
        query = run_query("""
                SELECT user_name
                     , artist_name
                     , artist_msid
                     , artist_mbids
                     , count(artist_name) as cnt
                  FROM %s
                 WHERE user_name = '%s'
              GROUP BY artist_name, artist_msid, artist_mbids
              ORDER BY cnt DESC
                 LIMIT %s
            """ % (table, user_name, LIMIT))
        batch_df = batch_df.union(query) if batch_df else query
    print("time taken to run all queries for %d users: %.2f" % (len(user_names), time.time() - t0))
    data = defaultdict(list)
    t = time.time()
    rows = batch_df.collect()
    print("time taken by collect call: %.2f" % (time.time() - t))
    for row in rows:
        data[row.user_name].append({
            'artist_name': row.artist_name,
            'artist_msid': row.artist_msid,
            'artist_mbids': row.artist_mbids,
            'listen_count': row.cnt,
        })
    query_t0 = time.time()
    print("Query to calculate artist stats proccessed in %.2f s" % (query_t0 - t0))
    return data


def get_recordings(user_name, table):
    """
    Args:
        user_name: name of the user
        table: name of the temporary table

    Returns:
        recording_stats (list): statistics of top 20 recordings
                            listened in the previous month
    """
    t0 = time.time()
    query = run_query("""
            SELECT track_name, recording_msid, recording_mbid, count(track_name) as cnt
              FROM %s
             WHERE user_name = '%s'
          GROUP BY track_name, recording_msid, recording_mbid
          ORDER BY cnt DESC
             LIMIT %s
        """ % (table, user_name, LIMIT))
    recording_stats = []
    for row in query.collect():
        recording = {}
        recording['track_name'] = row.track_name
        recording['recording_msid'] = row.recording_msid
        recording['recording_mbid'] = row.recording_mbid
        recording['listen_count'] = row.cnt
        recording_stats.append(recording)
    query_t0 = time.time()
    print("Query to calculate recording stats proccessed in %.2f s" % (query_t0 - t0))
    return recording_stats


def get_releases(user_name, table):
    """
    Args:
        user_name: name of the user
        table: name of the temporary table

    Returns:
        release_stats (list): statistics of top 20 recordings
                            listened in the previous month
    """
    t0 = time.time()
    query = run_query("""
            SELECT release_name, release_msid, release_mbid, count(release_name) as cnt
              FROM %s
             WHERE user_name = '%s'
          GROUP BY release_name, release_msid, release_mbid
          ORDER BY cnt DESC
             LIMIT %s
        """ % (table, user_name, LIMIT))
    release_stats = []
    for row in query.collect():
        release = {}
        release['release_name'] = row.release_name
        release['release_msid'] = row.release_msid
        release['release_mbid'] = row.release_mbid
        release['listen_count'] = row.cnt
        release_stats.append(release)
    query_t0 = time.time()
    print("Query to calculate release stats proccessed in %.2f s" % (query_t0 - t0))
    return release_stats


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
    print("Query to get list of users proccessed in %.2f s" % (query_t0 - t0))
    return users

def main(app_name):
    """
    Args:
        app_name: Application name to uniquely identify the submitted
                  application amongst other applications

    Returns:
        stats (list): list of dicts where each dict is a message/packet
                    for RabbitMQ containing user stats
    """
    t0 = time.time()
    listenbrainz_spark.init_spark_session(app_name)
    prev_month = month - 1 if month > 1 else 12
    curr_year = year if prev_month < 12 else year - 1
    try:
        df = listenbrainz_spark.sql_context.read.parquet('{}/data/listenbrainz/{}/{}.parquet'.format(config.HDFS_CLUSTER_URI, curr_year, prev_month))
        print("Loading dataframe...")
    except:
        print ("No Listens for last month")
        sys.exit(-1)
    df.printSchema()
    print(df.columns)
    print(df.count())
    table = 'listens_{}_{}'.format(prev_month, curr_year)
    print(table)
    df.registerTempTable(table)
    print("Running Query...")
    query_t0 = time.time()
    print("DataFrame loaded in %.2f s" % (query_t0 - t0))
    users = get_users(table)
    print("Number of users: %d" % len(users))
    obj = StatsWriter()
    stats = []
    while users:
        t = time.time()
        batch = users[:USER_BATCH_SIZE]
        print("Doing a batch of %d users" % len(batch))
        artists = get_artists(batch, table)
        batch_data = defaultdict(dict)
        for user in batch:
            batch_data[user]['artists'] = artists[user]
        print(json.dumps(batch_data, indent=4))
        users = users[USER_BATCH_SIZE:]
        print("total time taken by batch: %.2f" % (time.time() - t))

