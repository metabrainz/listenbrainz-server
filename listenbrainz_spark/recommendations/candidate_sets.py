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
from listenbrainz_spark import utils
from listenbrainz_spark.recommendations.utils import save_html
from listenbrainz_spark.recommendations.recommend import get_user_id

from pyspark.sql.functions import lit
from pyspark.sql.utils import AnalysisException, ParseException

# Candidate Set HTML is generated if set to true.
SAVE_CANDIDATE_HTML = True

def get_top_artists(user_name):
    """ Prepare dataframe of top y (limit) artists listened to by the user where y
        is a config value.

        Args:
            user_name (str): User name of the user.

        Returns:
            top_artists_df (dataframe): Dataframe with columns as:
                ['user_name', 'artist_name', 'artist_msid', 'count']
    """
    top_artists_df = run_query("""
            SELECT user_name
                 , artist_name
                 , artist_msid
                 , count(artist_msid) as count
              FROM listens_df
          GROUP BY user_name, artist_name, artist_msid
            HAVING user_name = "%s"
          ORDER BY count DESC
             LIMIT %s
    """ % (user_name, config.TOP_ARTISTS_LIMIT))
    return top_artists_df

def get_similar_artists_with_limit(artists):
    """ Prepare similar artists dataframe which consists of top x (limit) artists similar to each
        of the top artists listened to by the user where x is a config value.

        Args:
            artists (tuple): A tuple of top y artists names.

        Returns:
            similar_artists_df (dataframe): Dataframe with columns as:
                ['artist_name', 'similar_artist_name']
    """
    similar_artists_df = run_query("""
        SELECT top_similar_artists.artist_name
             , top_similar_artists.similar_artist_name
          FROM (
            SELECT row_number() OVER (PARTITION BY similar_artists.artist_name ORDER BY similar_artists.count DESC)
                AS rank, similar_artists.*
              FROM (
                SELECT artist_name_0 as artist_name
                     , artist_name_1 as similar_artist_name
                     , count
                  FROM artists_relation
                 WHERE artist_name_0 IN %s
                 UNION
                SELECT artist_name_1 as artist_name
                     , artist_name_0 as similar_artist_name
                     , count
                  FROM artists_relation
                 WHERE artist_name_1 IN %s
              ) similar_artists
          ) top_similar_artists
         WHERE top_similar_artists.rank <= %s
    """ % (artists, artists, config.SIMILAR_ARTISTS_LIMIT))
    return similar_artists_df

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
    candidate_recording_ids_df = df.withColumn('user_id', lit(user_id)).select('user_id', 'recording_id')
    return candidate_recording_ids_df

def get_net_similar_artists():
    """ Prepare dataframe consisting of similar artists which do not contain any of the
        top artists.

        Returns:
            net_similar_artists_df (dataframe): Dataframe with column as:
                ['similar_artist_name']
    """
    net_similar_artists_df = run_query("""
        SELECT similar_artist_name
          FROM similar_artist
         WHERE similar_artist_name
        NOT IN (
            SELECT artist_name
              FROM top_artist
        )
    """)
    return net_similar_artists_df

def get_top_artists_with_collab():
    """ Prepare dataframe consisting of top artists with non zero collaborations.

        Returns:
            top_artists_with_collab_df (dataframe): Dataframe with column as:
                ['artist_name']
    """
    top_artists_with_collab_df = run_query("""
        SELECT DISTINCT artist_name
          FROM similar_artist
    """)
    return top_artists_with_collab_df

def get_similar_artists_for_candidate_html(artist_name):
    """ Prepare dataframe consisting of artists similar to given artist.

        Args:
            artist_name (str): Artist name of top artist.

        Returns:
            df (dataframe): Dataframe with column as:
                ['similar_artist_name']
    """
    df = run_query("""
        SELECT similar_artist_name
          FROM similar_artist
         WHERE artist_name = "%s"
    """ % (artist_name))
    return df

def get_similar_artists(top_artists_df, user_name):
    """ Get similar artists dataframe.

        Args:
            top_artists_df (dataframe): Dataframe containing top artists of the user.
            user_name (str): User name of the user.

        Returns:
            similar_artists_df (dataframe): Dataframe with columns as:
                ['artist_name', 'similar_artist_name']
    """
    top_artists = ()
    for row in top_artists_df.collect():
        top_artists += (row.artist_name,)

    try:
        if len(top_artists) == 1:
            # Handle tuple with single entity
            similar_artists_df = get_similar_artists_with_limit(tuple(top_artists[0]))
        else:
            similar_artists_df = get_similar_artists_with_limit(top_artists)
    except ParseException as err:
        raise ParseException('Failed to parse similar artists query plan for "{}". Similar artists candidate set' \
            ' cannot be generated: {} \n{}.'.format(user_name, type(err).__name__, str(err)), stackTrace=True)
    except AnalysisException as err:
        raise AnalysisException('Failed to analyse similar artists query for "{}". Similar artists candidate set' \
            ' cannot be generated: {} \n{}.'.format(user_name, type(err).__name__, str(err)), stackTrace=True)

    try:
        similar_artists_df.take(1)[0]
    except IndexError as err:
        raise IndexError('No similar artists found for top artists listened to by "{}". All the top artists are with' \
            ' zero collaborations therefore top artists and similar artists candidate set cannot be generated' \
            .format(user_name))
    return similar_artists_df

def get_top_artists_recording_ids(similar_artist_df, user_name, user_id):
    """ Get recording ids of top artists.

        Args:
            similar_artists_df (dataframe): Dataframe consisting of similar artists.
            user_name (str): User name of the user.
            user_id (int): User id of the user.

        Returns:
            top_artists_recordings_ids_df (dataframe): Dataframe with columns as:
                ['user_id', 'recording_id']
    """

    # top artists with collaborations not equal to zero.
    top_artists_with_collab = ()
    top_artist_with_collab_df = get_top_artists_with_collab()
    for row in top_artist_with_collab_df.collect():
        top_artists_with_collab += (row.artist_name,)

    try:
        if len(top_artists_with_collab) == 1:
            top_artists_recording_ids_df = get_candidate_recording_ids(tuple((
                top_artists_with_collab[0])),user_id)
        else:
            top_artists_recording_ids_df = get_candidate_recording_ids(top_artists_with_collab, user_id)
    except ParseException as err:
        raise ParseException('Failed to parse candidate recordings query plan for "{}". Top artists candidate set' \
            ' cannot be generated: {} \n{}.'.format(user_name, type(err).__name__, str(err)), stackTrace=True)
    except AnalysisException as err:
        raise AnalysisException('Failed to analyse candidate recordings query for "{}". Top artists candidate set' \
            ' cannot be generated: {} \n{}.'.format(user_name, type(err).__name__, str(err)), stackTrace=True)
    return top_artists_recording_ids_df

def get_similar_artists_recording_ids(similar_artists_df, top_artists_df, user_name, user_id):
    """ Get recording ids of similar artists.

        Args:
            similar_artists_df (dataframe): Dataframe consisting of similar artists.
            top_artists_df (dataframe) : Dataframe consisting of top artists.
            user_name (str): User name of the user.
            user_id (int): User id of the user.

        Returns:
            similar_artists_recording_ids_df (dataframe): Dataframe with columns as:
                ['user_id', 'recording_id']
    """
    similar_artists = ()
    # eliminate artists from similar artists who are a part of top artists
    similar_artists_df = get_net_similar_artists()
    try:
        similar_artists_df.take(1)[0]
    except IndexError as err:
        raise IndexError('Similar artists candidate set not generated for "{}" as similar artists are' \
            ' equivalent to top artists for the user'.format(user_name))

    for row in similar_artists_df.collect():
        similar_artists += (row.similar_artist_name,)

    try:
        if len(similar_artists) == 1:
            similar_artists_recording_ids_df = get_candidate_recording_ids(tuple(similar_artists[0]), user_id)
        else:
            similar_artists_recording_ids_df = get_candidate_recording_ids(similar_artists, user_id)
    except ParseException as err:
        raise ParseException('Failed to parse candidate recordings query plan for "{}". Similar artists candidate set' \
            ' cannot be generated: {} \n{}.'.format(user_name, type(err).__name__, str(err)), stackTrace=True)
    except AnalysisException as err:
        raise AnalysisException('Failed to analyse candidate recordings query for "{}". Similar artists candidate set' \
            ' cannot be generated: {} \n{}.'.format(user_name, type(err).__name__, str(err)), stackTrace=True)

    try:
        similar_artists_recording_ids_df.take(1)[0]
    except IndexError as err:
        raise IndexError('No recordings found associated to artists in similar artists set. Similar artists' \
            ' candidate set cannot be generated for "{}": {} \n {}'.format(user_name, type(err).__name__, str(err)))
    return similar_artists_recording_ids_df

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
    path = os.path.join(config.HDFS_CLUSTER_URI, 'data', 'listenbrainz', 'recommendation-engine', 'candidate-set')
    top_artists_candidate_set_df.write.format('parquet').save(path  + '/top_artists.parquet', mode='overwrite')
    similar_artists_candidate_set_df.write.format('parquet').save(path + '/similar_artists.parquet', mode='overwrite')

def get_candidate_html_data(similar_artist_df, user_name):
    """ Get artists similar to top artists listened to by the user. The function is invoked
        when candidate set HTML is to be generated.

        Args:
            top_artists_with_collab (dataframe): Dataframe of top artists listened to by the user
                whose similar artists count is not zero.
            user_name (str): User name of the user.

        Returns:
            artists (dict): Dictionary can be depicted as:
                {
                    'top_artists 1' : ['similar_artist 1', 'similar_artist 2' ... 'similar_artist x'],
                    'top_artists 2' : ['similar_artist 1', 'similar_artist 2' ... 'similar_artist x'],
                    .
                    .
                    .
                    'top_artists y' : ['similar_artist 1', 'similar_artist 2' ... 'similar_artist x'],
                }
    """
    artists = defaultdict(dict)
    top_artist_with_collab_df = get_top_artists_with_collab()
    for row in top_artist_with_collab_df.collect():
        df = get_similar_artists_for_candidate_html(row.artist_name)
        artists[row.artist_name] = [row.similar_artist_name for row in df.collect()]
    return artists

def save_candidate_html(user_data):
    """ Save user data to an HTML file.

        Args:
            user_data (dict): Dcitionary can be depicted as:
                {
                    'user_name 1': {
                        'artists': {
                            'top_artists 1' : ['similar_artist 1', 'similar_artist 2' ... 'similar_artist x'],
                        ...
                        'top_artists y' : ['similar_artist 1', 'similar_artist 2' ... 'similar_artist x'],
                        },
                        'time' : 'xxx'
                    },
                }
    """
    date = datetime.utcnow().strftime('%Y-%m-%d')
    candidate_html = 'Candidate-{}-{}.html'.format(uuid.uuid4(), date)
    context = {
        'user_data' : user_data
    }
    save_html(candidate_html, context, 'candidate.html')

def main():
    ti = time()
    try:
        listenbrainz_spark.init_spark_session('Candidate_set')
    except AttributeError as err:
        logging.error('{} \nAborting...'.format(err))
        sys.exit(-1)
    except Exception as err:
        logging.error('{} \nAborting...'.format(err), exc_info=True)
        sys.exit(-1)

    listens_df = None
    for y in range(config.STARTING_YEAR, config.ENDING_YEAR + 1):
        for m in range(config.STARTING_MONTH, config.ENDING_MONTH + 1):
            try:
                month = listenbrainz_spark.sql_context.read.parquet('{}/data/listenbrainz/{}/{}.parquet' \
                    .format(config.HDFS_CLUSTER_URI, y, m))
                listens_df = listens_df.union(month) if listens_df else month
            except AnalysisException as err:
                logging.error('Cannot read parquet files from HDFS: {} \n {}'.format(type(err).__name__,str(err)))
                continue
            except Exception as err:
                logging.error('An error occured while fetching "/data/listenbrainz/{}/{}.parquet": {} \n {}. Aborting...'
                    .format(y, m, type(err).__name__, str(err)), exc_info=True)
                sys.exit(-1)
    if not listens_df:
        raise SystemExit('Parquet files containing listening history from {}-{} to {}-{} missing from HDFS' \
            .format(config.STARTING_YEAR, '{:02d}'.format(config.STARTING_MONTH), config.ENDING_YEAR, '{:02d}' \
            .format( config.ENDING_MONTH)))

    path = os.path.join(config.HDFS_CLUSTER_URI, 'data', 'listenbrainz', 'similar_artists','artist_artist_relations.parquet')
    try:
        artists_relation_df = utils.read_files_from_HDFS(path)
    except AnalysisException as err:
        logging.error('{} \nAborting...'.format(err))
        sys.exit(-1)
    except Exception as err:
        logging.error('{} \nAborting...'.format(err), exc_info=True)
        sys.exit(-1)

    path = os.path.join(config.HDFS_CLUSTER_URI, 'data', 'listenbrainz', 'recommendation-engine', 'dataframes')
    try:
        recordings_df = utils.read_files_from_HDFS(path + '/recordings_df.parquet')
        users_df = utils.read_files_from_HDFS(path + '/users_df.parquet')
    except AnalysisException as err:
        logging.error('{} \nAborting...'.format(err))
        sys.exit(-1)
    except Exception as err:
        logging.error('{} \nAborting...'.format(err), exc_info=True)
        sys.exit(-1)

    logging.info('Registering Dataframes...')
    try:
        utils.register_dataframe(listens_df, 'listens_df')
        utils.register_dataframe(recordings_df, 'recording')
        utils.register_dataframe(users_df, 'user')
        utils.register_dataframe(artists_relation_df, 'artists_relation')
    except AnalysisException as err:
        logging.error('{} \nAborting...'.format(err))
        sys.exit(-1)
    except Exception as err:
        logging.error('{} \nAborting...'.format(err), exc_info=True)
        sys.exit(-1)
    logging.info('Files fectched from HDFS and dataframes registered in {}s'.format('{:.2f}'.format(time() - ti)))

    path = os.path.join(os.path.dirname(os.path.abspath(__file__)),'recommendation-metadata.json')
    with open(path) as f:
        recommendation_metadata = json.load(f)
        user_names = recommendation_metadata['user_name']

    user_data = defaultdict(dict)
    similar_artists_candidate_set_df = None
    top_artists_candidate_set_df = None
    for user_name in user_names:
        ts = time()
        try:
            user_id = get_user_id(user_name)
        except TypeError as err:
            logging.error('{}: Invalid user name. User "{}" does not exist.'.format(type(err).__name__,user_name))
            continue
        except AnalysisException as err:
            logging.error('Failed to analyse user id query for "{}". Candidate sets cannot be generated: {} \n{}' \
                .format(user_name, type(err).__name__, str(err)))
            continue
        except ParseException as err:
            logging.error('Failed to parse user id query plan for "{}". Candidate sets cannot be generated: {} \n{}' \
                .format(user_name, type(err).__name__, str(err)))
            continue

        try:
            top_artists_df = get_top_artists(user_name)
            top_artists_df.take(1)[0]
        except IndexError as err:
            logging.error('No top artists found, i.e. "{}" is either a new user or has empty listening history.' \
                ' Candidate sets cannot be generated'.format(user_name))
            continue
        except AnalysisException as err:
            logging.error('Failed to analyse top artists query for "{}". Candidate sets cannot be generated: {} \n{}' \
                .format(user_name, type(err).__name__, str(err)))
            continue
        except ParseException as err:
            logging.error('Failed to parse top artists query plan for "{}". Candidate sets cannot be generated: {} \n{}' \
                .format(user_name, type(err).__name__, str(err)))
            continue

        try:
            similar_artists_df = get_similar_artists(top_artists_df, user_name)
        except IndexError as err:
            logging.error(err)
            continue
        except AnalysisException as err:
            logging.error(err)
            continue
        except ParseException as err:
            logging.error(err)
            continue

        try:
            utils.register_dataframe(similar_artists_df, 'similar_artist')
            utils.register_dataframe(top_artists_df, 'top_artist')
        except AnalysisException as err:
            logging.error(err)
            continue
        except Exception as err:
            logging.error(err, exc_info=True)
            continue

        try:
            top_artists_recording_ids_df = get_top_artists_recording_ids(similar_artists_df, user_name, user_id)
        except AnalysisException as err:
            logging.error(err)
            continue
        except ParseException as err:
            logging.error(err)
            continue
        top_artists_candidate_set_df = top_artists_candidate_set_df.union(top_artists_recording_ids_df) \
            if top_artists_candidate_set_df else top_artists_recording_ids_df

        try:
            similar_artists_recording_ids_df = get_similar_artists_recording_ids(similar_artists_df, top_artists_df
                , user_name, user_id)
        except IndexError as err:
            logging.error(err)
            continue
        except AnalysisException as err:
            logging.error(err)
            continue
        except ParseException as err:
            logging.error(err)
            continue
        similar_artists_candidate_set_df = similar_artists_candidate_set_df.union(similar_artists_recording_ids_df) \
            if similar_artists_candidate_set_df else similar_artists_recording_ids_df

        if SAVE_CANDIDATE_HTML:
            user_data[user_name]['artists'] = get_candidate_html_data(similar_artists_df, user_name)
            user_data[user_name]['time'] = '{:.2f}'.format(time() - ts)
        logging.info('candidate_set generated for \"{}\"'.format(user_name))

    try:
        save_candidate_sets(top_artists_candidate_set_df, similar_artists_candidate_set_df)
    except Exception as err:
        logging.error('An error occured while saving candidate sets: {} \n {}. Aborting...'.format(type(err).__name__,
            str(err),exc_info=True))
        sys.exit(-1)

    if SAVE_CANDIDATE_HTML:
        save_candidate_html(user_data)
