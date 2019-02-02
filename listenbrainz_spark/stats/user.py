import sys
import listenbrainz_spark
import time
from datetime import datetime  

month = datetime.now().month
year = datetime.now().year

def get_total_listens(user_name, table):
    """ 
    Args:
        user_name: name of the user 
        table: name of the temporary table

    Returns:
        count: listen_count of the previous month
    """
    t0 = time.time()
    query = listenbrainz_spark.sql_context.sql("""
            SELECT count(artist_name) as cnt
              FROM %s
              where user_name = '%s'
        """ % (table, user_name))
    query_t0 = time.time()
    query.show()
    print("Query to calculate listen count proccessed in %.2f s" % (query_t0 - t0))
    return query.collect()[0].cnt


def get_artists(user_name, table):
    """ 
    Args:
        user_name: name of the user 
        table: name of the temporary table

    Returns:
        artist (dict): listen_count and statistics
               of top 20 artists listened in the previous month
    """
    t0 = time.time()
    query = listenbrainz_spark.sql_context.sql("""
            SELECT artist_name, artist_msid, artist_mbids, count(artist_name) as cnt
              FROM %s
             WHERE user_name = '%s'
          GROUP BY artist_name, artist_msid, artist_mbids
          ORDER BY cnt DESC
             LIMIT 20
        """ % (table, user_name))
    query_t0 = time.time()
    print("Query to calculate artist stats proccessed in %.2f s" % (query_t0 - t0))
    query.show()
    artist_stats = []
    artist = {}
    for row in query.collect():
        artist['artist_name'] = row.artist_name
        artist['artist_msid'] = row.artist_msid
        artist['artist_mbids'] = row.artist_mbids
        artist['listen_count'] = row.cnt
        artist_stats.append(artist)
        artist = {}
    count = get_total_listens(user_name, table)
    artist['artist_count'] = count
    artist['artist_stats'] = artist_stats
    return artist


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
    query = listenbrainz_spark.sql_context.sql("""
            SELECT track_name, recording_msid, recording_mbid, count(track_name) as cnt
              FROM %s
             WHERE user_name = '%s'
          GROUP BY track_name, recording_msid, recording_mbid
          ORDER BY cnt DESC
             LIMIT 20
        """ % (table, user_name))
    query_t0 = time.time()
    print("Query to calculate recording stats proccessed in %.2f s" % (query_t0 - t0))
    query.show()
    recording_stats = []
    for row in query.collect():
        recording = {}
        recording['track_name'] = row.track_name
        recording['recording_msid'] = row.recording_msid
        recording['recording_mbid'] = row.recording_mbid
        recording['listen_count'] = row.cnt
        recording_stats.append(recording)
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
    query = listenbrainz_spark.sql_context.sql("""
            SELECT release_name, release_msid, release_mbid, count(release_name) as cnt
              FROM %s
             WHERE user_name = '%s'
          GROUP BY release_name, release_msid, release_mbid
          ORDER BY cnt DESC
             LIMIT 20
        """ % (table, user_name))
    query_t0 = time.time()
    print("Query to calculate release stats proccessed in %.2f s" % (query_t0 - t0))
    query.show()
    release_stats = []
    for row in query.collect():
        release = {}
        release['release_name'] = row.release_name
        release['release_msid'] = row.release_msid
        release['release_mbid'] = row.release_mbid
        release['listen_count'] = row.cnt
        release_stats.append(release)
    return release_stats


def get_users(table):
    """ DataFrame is registered as a temporary table 
    Args:
        table : name of the temporary table

    Returns:
        users: list containing user names of all the users
    """
    t0 = time.time()
    query = listenbrainz_spark.sql_context.sql("""
        SELECT DISTINCT user_name
        FROM %s
        """ % table)
    query_t0 = time.time()
    users = [row.user_name for row in query.collect()]
    print("Query proccessed in %.2f s" % (query_t0 - t0))
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
        df = listenbrainz_spark.sql_context.read.parquet('hdfs://hadoop-master:9000/data/listenbrainz/{}/{}.parquet'.format(curr_year, prev_month))
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
    stats = []
    for user in users:
        user_data = {}
        user_data[user] = {}
        user_data[user]['artists'] = get_artists(user, table)
        user_data[user]['recordings'] = get_recordings(user, table)
        user_data[user]['releases'] = get_releases(user, table)
        stats.append(user_data)
    print (stats)
        
