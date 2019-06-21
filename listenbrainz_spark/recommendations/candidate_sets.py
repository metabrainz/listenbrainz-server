import os
import sys
import uuid
import json
import logging
from time import time
from datetime import datetime
from collections import defaultdict

import listenbrainz_spark
from listenbrainz_spark import config
from listenbrainz_spark.stats import run_query
from listenbrainz_spark.recommendations import utils

from pyspark.sql.functions import lit
from pyspark.sql.window import Window
from py4j.protocol import Py4JJavaError
from pyspark.sql.functions import row_number, col
from pyspark.sql.utils import QueryExecutionException, AnalysisException, ParseException

# Candidate Set HTML is generated if set to true.
candidateHTML = True

def get_top_artists(user_name):
    """ Prepare dataframe of top y (limit) artists listened to by the user where y
        is a config value.

        Args:
            user_name (str): User name of the user for whom top artists dataframe is to be
                computed.

        Returns:
            top_artists_df (dataframe): Dataframe with columns as:
                ['user_name', 'artist_nmae', 'artist_msid', 'count']
    """
    top_artists_df = run_query("""
        SELECT user_name, artist_name, artist_msid, count(artist_msid) as count
            FROM listens_df
         GROUP BY user_name, artist_name, artist_msid
         HAVING user_name = "%s"
         ORDER BY count DESC
         LIMIT %s
    """ % (user_name, config.TOP_ARTISTS_LIMIT))
    return top_artists_df

def get_candidate_recording_ids(artists, user_id):
    """ Prepare dataframe of recording ids which belong to artists provided as argument.

        Args:
            artists (tuple): A tuple of artist names.
            user_id (int): User id of the user.

        Returns:
            candidate_recording_ids_df (dataframe): Dataframe with columns as:
                ['user_id', 'recording_id']
    """
    df = run_query("""
        SELECT recording_id
            FROM recording
         WHERE artist_name IN %s
    """ % (artists,))
    candidate_recording_ids_df = df.withColumn('user_id', lit(user_id)) \
    .select('user_id', 'recording_id')
    return candidate_recording_ids_df

def get_user_id(user_name):
    """ Get user id associated with the user_name.

        Args:
            user_name (str): User name of the user.

        Returns:
            user_id (int): User id of the user.
    """
    df = run_query("""
        SELECT user_id
            FROM user
         WHERE user_name = "%s"
    """ % (user_name))
    return df.first()['user_id']

def get_similar_artists_with_limit(df):
    """ Prepare similar artists dataframe which consists of top x (limit) artists similar to each
        of the top y (limit) artists listened to by the user where x and y are config values.

        Args:
            df (dataframe): Dataframe consisting of artists similar to each of the top y artists
            without limit x.

        Returns:
            similar_artists_df (dataframe): Dataframe consisting of artists similar to each of the
                top y artists with limit x. Dataframe columns can be depicted as:
                    ['artist_name_1']
    """
    window = Window.partitionBy(df['artist_name_0']).orderBy(df['count'].desc())
    df = df.select('*', row_number().over(window).alias('rank')).filter(col('rank') <=                                      config.SIMILAR_ARTISTS_LIMIT)
    similar_artists_df = df.select('artist_name_1')
    return similar_artists_df

def get_similar_artists_without_limit(artists):
    """ Prepare similar artists dataframe which consists of artists similar to each of the
        top y (limit) artists listened to by the user where y is a config value.

        Args:
            artists (tuple): A tuple of top y artists names.

        Returns:
            similar_artists_df (dataframe): Dataframe with columns as:
                ['artist_name_0', 'artist_name_1', 'count']
    """
    similar_artists_df = run_query("""
        SELECT artist_name_0, artist_name_1, count
            FROM artists_relation
         WHERE artist_name_0 IN %s
    """ % (artists,))
    return similar_artists_df

def save_candidate_sets(top_artists_candidate_set_df, similar_artists_candidate_set_df):
    """ Save candidate sets to HDFS.

        Args:
            top_artists_candidate_set_df (dataframe): Dataframe consisting of recording ids of
                top artists listened to by a user for all the users for whom recommendations shall
                be generated. Dataframe columns can be depicted as:
                    ['user_id', 'recording_id']
            similar_artists_candidate_set_df (dataframe): Dataframe consisting of recording ids of
                artists similar to top artists listened to by a user for all the users for whom
            recommendations shall be generated. Dataframe columns can be depicted as:
                ['user_id', 'recording_id']
    """
    path = os.path.join(config.HDFS_CLUSTER_URI, 'data', 'listenbrainz', 'recommendation-engine',                           'candidate-set')
    top_artists_candidate_set_df.write.format('parquet').save(path  + '/top_artists.parquet', mode='overwrite')
    similar_artists_candidate_set_df.write.format('parquet').save(path + '/similar_artists.parquet',                        mode='overwrite')

def get_similar_artist_candidate_html(artist):
    """ Prepare similar artists dataframe which consists of top x (limit) artists similar
        to the top artist given as argument where x is a config value. The function is invoked
        when candidate set HTML is to be generated.

        Args:
            artist (str): Name of one of the top artist.

        Returns:
            similar_artists_df (dataframe): Dataframe consisting of artists similar to the top artist
                given as argument with limit x. Dataframe column can be depicted as:
                    ['artist_name_1']
    """
    similar_artists_df = run_query("""
        SELECT artist_name_1
            FROM artists_relation
         WHERE artist_name_0 = "%s"
        ORDER BY count DESC
        LIMIT %s
    """ % (artist, config.SIMILAR_ARTISTS_LIMIT))
    return similar_artists_df

def get_candidate_html_data(top_artist_with_collab, user_name):
    """ Get artists similar to top artists listened to by the user. The function is invoked
        when candidate set HTML is to be generated.

        Args:
            top_artists_with_collab (dataframe): Dataframe of top artists listened to by the user
                whose similar artists count is not zero.
            user_name (str): User name of the user.

        Returns:
            artists (dict): Dictionary can be depicted as:
                {
                    'top_artists 1' : ['similar_artist 1', 'simialr_artist 2' ... 'similar_artist x'],
                    'top_artists 2' : ['similar_artist 1', 'simialr_artist 2' ... 'similar_artist x'],
                    .
                    .
                    .
                    'top_artists y' : ['similar_artist 1', 'simialr_artist 2' ... 'similar_artist x'],
                }
    """
    artists = defaultdict(dict)
    for row in top_artist_with_collab.collect():
        similar_artists_df = get_similar_artist_candidate_html(row.artist_name_0)
        artists[row.artist_name_0] = [row.artist_name_1 for row in similar_artists_df.collect()]
    return artists

def save_candidate_html(user_data):
    """ Save user data to an HTML file.

        Args:
            user_data (dict): Dcitionary can be depicted as:
                {
                    'user_name 1': {
                        'artists': {
                            'top_artists 1' : ['similar_artist 1', 'simialr_artist 2' ... 'similar_artist x'],
                        ...
                        'top_artists y' : ['similar_artist 1', 'simialr_artist 2' ... 'similar_artist x'],
                        },
                        'time' : 'xxx'
                    },
                }
    """
    date = datetime.utcnow().strftime('%Y-%m-%d')
    candidate_html = 'Canidate-{}-{}.html'.format(uuid.uuid4(), date)
    context = {
        'user_data' : user_data
    }
    utils.save_html(candidate_html, context, 'candidate.html')

def main():
    ti = time()
    try:
        listenbrainz_spark.init_spark_session('Candidate_set')
    except AttributeError as err:
        logging.error('Cannot initialize Spark Session: {} \n {}. Aborting...'.format(type(err).__name__,str(err)),         exc_info=True)
        sys.exit(-1)
    except Exception as err:
        logging.error('An error occurred: {} \n {}. Aborting...'.format(type(err).__name__,str(err)), exc_info=True)
        sys.exit(-1)

    listens_df = None
    for y in range(config.STARTING_YEAR, config.ENDING_YEAR + 1):
        for m in range(config.STARTING_MONTH, config.ENDING_MONTH + 1):
            try:
                month = listenbrainz_spark.sql_context.read.parquet('{}/data/listenbrainz/{}/{}.parquet'.format(             config.HDFS_CLUSTER_URI, y, m))
                listens_df = listens_df.union(month) if listens_df else month
            except AnalysisException as err:
                logging.error('Cannot read parquet files from HDFS: {} \n {}'.format(type(err).__name__,str(err)))
                continue
            except Exception as err:
                logging.error('An error occured while fetching \"/data/listenbrainz/{}/{}.parquet\": {} \n {}.              Aborting...'.format(y, m, type(err).__name__, str(err)), exc_info=True)
                sys.exit(-1)
    if not listens_df:
        raise SystemExit("Parquet files containing listening history from {}-{} to {}-{} missing from HDFS".format(         config.STARTING_YEAR, "%02d" % config.STARTING_MONTH, config.ENDING_YEAR, "%02d" % config.ENDING_MONTH))

    artists_relation_df = None
    try:
        path = '{}/data/listenbrainz/similar_artists/artist_artist_relations.parquet'.format(config.HDFS_CLUSTER_URI)
        artists_relation_df = listenbrainz_spark.sql_context.read.parquet(path)
    except AnalysisException as err:
        logging.error('Cannot read artist-artist relation from HDFS: {} \n {}. Aborting...'.format(type(err).__name__,
            str(err)))
        sys.exit(-1)
    except Exception as err:
        logging.error('An error occured while fecthing artist-artist relation: {} \n {}. Aborting...'.format(type(err)      .__name__, str(err)))
        sys.exit(-1)
    if not artists_relation_df:
        raise SystemExit("Parquet file conatining artist-artist relation is missing from HDFS. Aborting...")

    try:
        path = os.path.join(config.HDFS_CLUSTER_URI, 'data', 'listenbrainz', 'recommendation-engine', 'dataframes')
        recordings_df = listenbrainz_spark.sql_context.read.parquet(path + '/recordings_df.parquet')
        users_df = listenbrainz_spark.sql_context.read.parquet(path + '/users_df.parquet')
    except AnalysisException as err:
        logging.error('Cannot read parquet files from HDFS: {} \n {}'.format(type(err).__name__,str(err)))
        sys.exit(-1)
    except Exception as err:
        logging.error('An error occured while fetching parquets: {} \n {}. Aborting...'.format(type(err).__name__,
            str(err)), exc_info=True)
        sys.exit(-1)

    logging.info('Registering Dataframes...')
    try:
        listens_df.createOrReplaceTempView('listens_df')
        recordings_df.createOrReplaceTempView('recording')
        users_df.createOrReplaceTempView('user')
        artists_relation_df.createOrReplaceTempView('artists_relation')
    except AnalysisException as err:
        logging.error('Cannot register dataframe: {} \n {}. Aborting...'.format(type(err).__name__, str(err)))
        sys.exit(-1)
    except Exception as err:
        logging.error('An error occured while registering dataframe: {} \n {}. Aborting...'.format(type(err).__name__,      str(err)), exc_info=True)
        sys.exit(-1)
    logging.info('Files fectched from HDFS and dataframes registered in {}s'.format('{:.2f}'.format(time() - ti)))

    path = os.path.join(os.path.dirname(os.path.abspath(__file__)),'recommendation-metadata.json')
    user_data = defaultdict(dict)
    with open(path) as f:
        recommendation_metadata = json.load(f)
        similar_artists_candidate_set_df = None
        top_artists_candidate_set_df = None
        for user_name in recommendation_metadata['user_name']:
            top_artists = ()
            similar_artists = ()
            top_artists_with_collab = ()
            try:
                ts = time()
                user_id = get_user_id(user_name)
                top_artists_df = get_top_artists(user_name)
                if not top_artists_df.take(1):
                    logging.info('"{}" is either a new user or has empty listening history. Candidate sets cannot be generated'.format(user_name))
                    continue
                for row in top_artists_df.collect():
                    top_artists += (row.artist_name,)

                # Handle tuple with single entity
                if len(top_artists) == 1:
                    df = get_similar_artists_without_limit(tuple(top_artists[0]))
                else:
                    df = get_similar_artists_without_limit(top_artists)
                if not df.take(1):
                    logging.info('Candidate sets cannot be generated since no similar artists for any of the top artists found: \n{}'.format(top_artists))
                    continue
                similar_artists_df = get_similar_artists_with_limit(df)

                # Gets only those top artists whose similar artists count is not 0
                top_artist_with_collab_df = df.select('artist_name_0').distinct()
                for row in top_artist_with_collab_df.collect():
                    top_artists_with_collab += (row.artist_name_0,)
                if len(top_artists_with_collab) == 1:
                    top_artists_recording_ids_df = get_candidate_recording_ids(tuple((top_artists_with_collab[0])),         user_id)
                else:
                    top_artists_recording_ids_df = get_candidate_recording_ids(top_artists_with_collab, user_id)
                top_artists_candidate_set_df = top_artists_candidate_set_df.union(top_artists_recording_ids_df) \
                    if top_artists_candidate_set_df else top_artists_recording_ids_df

                # eliminate artists from similar artist who are a part of top artists
                net_similar_artists_df = similar_artists_df.select('artist_name_1').subtract(top_artists_df.select(          'artist_name'))
                if not net_similar_artists_df.take(1):
                    logging.info('Similar artists candidate set not generated for "{}" as similar artists are           equivalent to top artists for the user'.format(user_name))
                    continue
                for row in net_similar_artists_df.collect():
                    similar_artists += (row.artist_name_1,)
                if len(similar_artists) == 1:
                    similar_artists_recording_ids_df = get_candidate_recording_ids(tuple(similar_artists[0]), user_id)
                else:
                    similar_artists_recording_ids_df = get_candidate_recording_ids(similar_artists, user_id)
                similar_artists_candidate_set_df = similar_artists_candidate_set_df.union(                                  similar_artists_recording_ids_df) \
                    if similar_artists_candidate_set_df else similar_artists_recording_ids_df

                if candidateHTML:
                    user_data[user_name]['artists'] = get_candidate_html_data(top_artist_with_collab_df, user_name)
                    user_data[user_name]['time'] = '{:.2f}'.format(time() - ts)
                logging.info('candidate_set generated for \"{}\"'.format(user_name))
            except TypeError as err:
                logging.error('{}: Invalid user name. User \"{}\" does not exist.'.format(type(err).__name__,user_name))
            except QueryExecutionException as err:
                logging.error('Failed to execute query: {} \n {}. Aborting...'.format(type(err).__name__, str(err)))
            except AnalysisException as err:
                logging.error('Failed to analyse query plan: {} \n {}. Aborting...'.format(type(err).__name__,str(err)))
            except ParseException as err:
                logging.error('Failed to parse SQL command: {} \n {}. Aborting...'.format(type(err).__name__, str(err)))
            except Exception as err:
                logging.error('Candidate set for \"{}\" not generated. {} \n {}'.format(user_name, type(err).__name__,      str(err)), exc_info=True)
    try:
        save_candidate_sets(top_artists_candidate_set_df, similar_artists_candidate_set_df)
    except Py4JJavaError as err:
        logging.error("Unable to save candidate set: {} \n {}. Aborting...".format(type(err).__name__,str(err)))
        sys.exit(-1)
    except Exception as err:
        logging.error('An error occured while candidate set: {} \n {}. Aborting...'.format(type(err).__name__,
            str(err),exc_info=True))
        sys.exit(-1)

    if candidateHTML:
        save_candidate_html(user_data)
