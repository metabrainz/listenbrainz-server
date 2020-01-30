import os
import sys
import uuid
import json
import logging
from time import time
from datetime import datetime
from collections import defaultdict
from py4j.protocol import Py4JJavaError

import listenbrainz_spark
from listenbrainz_spark import stats
from listenbrainz_spark import config, utils, path
from listenbrainz_spark.recommendations.utils import save_html
from listenbrainz_spark.sql import candidate_sets_queries as sql
from listenbrainz_spark.exceptions import SQLException, SparkSessionNotInitializedException, ViewNotRegisteredException, \
    PathNotFoundException, FileNotFetchedException

from flask import current_app
import pyspark.sql.functions as func
from pyspark.sql.window import Window
from pyspark.sql.functions import lit, col, to_timestamp, current_timestamp, date_sub, row_number
from pyspark.sql.utils import AnalysisException, ParseException

# Candidate Set HTML is generated if set to true.
SAVE_CANDIDATE_HTML = True

def get_listens_for_rec_generation_window(mapped_df):
    """ Get listens to fetch top artists.

        Args:
            mapped_df (dataframe): Dataframe with all the columns/fields that a typical listen has.
    """
    df = mapped_df.select('*') \
        .where((col('listened_at') >= to_timestamp(date_sub(current_timestamp(),
        config.RECOMMENDATION_GENERATION_WINDOW))) & (col('listened_at') <= current_timestamp()))
    return df

def get_top_artists(df, user_name):
    """ Get top artists listened to by the user.

        Args:
            df (dataframe): Dataframe to containing user history.
            user_name (str): Name of the user.

        Returns:
            top_artists_df (dataframe): Columns can be depicted as:
                [
                    'mb_artist_credit_id', 'artist_name'
                ]
    """
    top_artists_df = df.select('mb_artist_credit_id', 'artist_name') \
        .where(col('user_name') == user_name) \
        .groupBy('mb_artist_credit_id', 'artist_name') \
        .agg(func.count('mb_artist_credit_id').alias('count')) \
        .orderBy('count', ascending=False).limit(config.TOP_ARTISTS_LIMIT)

    return top_artists_df

def get_similar_artists(top_artists_df, artists_relation_df, user_name):
    """ Get similar artists dataframe.

        Args:
            top_artists_df (dataframe): Dataframe containing top artists of the user.
            artist_relation_df (dataframe): Dataframe containing artists and similar artists.
            user_name (str): User name of the user.

        Returns:
            similar_artists_df (dataframe): Columns can be depicted as:
                [
                    top_artist_credit_id', 'similar_artist_credit_id', 'similar_artist_name', 'top_artist_name'
                ]
    """
    top_artists = [row.mb_artist_credit_id for row in top_artists_df.collect()]

    similar_artists_df = artists_relation_df.select(
            col('id_0').alias('top_artist_credit_id'), col('id_1').alias('similar_artist_credit_id'), \
            col('name_0').alias('top_artist_name'), col('name_1').alias('similar_artist_name'), 'score') \
            .where(artists_relation_df.id_0.isin(top_artists)) \
        .union(
            artists_relation_df.select(
                col('id_1').alias('top_artist_credit_id'), col('id_0').alias('similar_artist_credit_id'), \
                col('name_1').alias('top_artist_name'), col('name_0').alias('similar_artist_name'), 'score') \
                .where(artists_relation_df.id_1.isin(top_artists))
        ).distinct()

    try:
        similar_artists_df.take(1)[0]
    except IndexError:
        current_app.logger.error('No similar artists found for {}'.format(user_name))
        raise IndexError()

    window = Window.partitionBy('top_artist_credit_id').orderBy(col('score').desc())
    top_similar_artists_df = similar_artists_df.withColumn('rank', row_number().over(window)) \
        .where(col('rank') <= config.SIMILAR_ARTISTS_LIMIT) \
        .select('top_artist_credit_id', 'similar_artist_credit_id', 'similar_artist_name', 'top_artist_name')
    # Remove artists from similar artists that already occurred in top artists.
    distinct_similar_artists_df = top_similar_artists_df[top_similar_artists_df \
        .similar_artist_credit_id.isin(top_artists) == False]

    try:
        distinct_similar_artists_df.take(1)[0]
    except IndexError:
        current_app.logger.error('Similar artists equivalent to top artists for {}.\
            Generating only top artists playlist'.format(user_name))
        raise IndexError()

    return distinct_similar_artists_df

def get_candidate_recording_ids(artist_credit_ids, recordings_df, user_id):
    """ Get recordings corresponding to artist_credit_ids

        Args:
            artist_credit_ids (list): A list of artist_credit ids.
            recordings_df (dataframe): Dataframe containing recording ids
            user_id (int): User id of the user.

        Returns:
            recordings_ids_df (dataframe): Columns can be depicted as:
                [
                    'user_id', 'recording_id'
                ]
    """
    df = recordings_df[recordings_df.mb_artist_credit_id.isin(artist_credit_ids)] \
        .select('recording_id')
    recordings_ids_df = df.withColumn('user_id', lit(user_id)) \
        .select('user_id', 'recording_id')
    return recordings_ids_df

def get_top_artists_recording_ids(top_artists_df, recordings_df, user_id):
    """ Get recording ids of top artists.

        Args:
            top_artists_df (dataframe): Dataframe consisting of top artists.
            recordings_df (dataframe): Dataframe containing recording ids
            user_id (int): User id of the user.

        Returns:
            top_artists_recordings_ids_df (dataframe): Columns can be depicted as:
                [
                    'user_id', 'recording_id'
                ]
    """
    top_artist_credit_ids = [row.mb_artist_credit_id for row in top_artists_df.collect()]
    top_artists_recording_ids_df = get_candidate_recording_ids(top_artist_credit_ids, recordings_df, user_id)
    return top_artists_recording_ids_df

def get_similar_artists_recording_ids(similar_artists_df, recordings_df, user_id):
    """ Get recording ids of similar artists.

        Args:
            similar_artists_df (dataframe): Dataframe consisting of similar artists.
            recordings_df (dataframe): Dataframe containing recording ids
            user_id (int): User id of the user.

        Returns:
            similar_artists_recording_ids_df (dataframe): Columns can be depicted as:
                [
                    'user_id', 'recording_id'
                ]
    """
    similar_artist_credit_ids = [row.similar_artist_credit_id for row in similar_artists_df.collect()]
    similar_artists_recording_ids_df = get_candidate_recording_ids(similar_artist_credit_ids, recordings_df, user_id)
    return similar_artists_recording_ids_df

def save_candidate_sets(top_artists_candidate_set_df, similar_artists_candidate_set_df):
    """ Save candidate sets to HDFS.

        Args:
            top_artists_candidate_set_df (dataframe): Dataframe consisting of recording ids of
                top artists listened to by a user for all the users for whom recommendations shall
                be generated. Dataframe columns can be depicted as:
                    [
                        'user_id', 'recording_id'
                    ]
            similar_artists_candidate_set_df (dataframe): Dataframe consisting of recording ids of
                artists similar to top artists listened to by a user for all the users for whom
                recommendations shall be generated. Columns can be depicted as:
                    [
                        'user_id', 'recording_id'
                    ]
    """
    utils.save_parquet(top_artists_candidate_set_df, path.TOP_ARTIST_CANDIDATE_SET)
    utils.save_parquet(similar_artists_candidate_set_df, path.SIMILAR_ARTIST_CANDIDATE_SET)

def get_candidate_html_data(similar_artists_df, user_name):
    """ Get artists similar to top artists listened to by the user. The function is invoked
        when candidate set HTML is to be generated.

        Args:
            similar_artists_df (dataframe): Dataframe of similar_artists.
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
    artists = defaultdict(list)
    for row in similar_artists_df.collect():
        artists[row.top_artist_name].append(row.similar_artist_name)
    return artists

def save_candidate_html(user_data):
    """ Save user data to an HTML file.

        Args:
            user_data (dict): Dictionary can be depicted as:
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

def get_user_id(df, user_name):
    """ Get user id of the user.

        Args:
            df (dataframe): Dataframe to fetch user id.
            user_name (str): User name of the user.

        Returns:
            row.user_id (int): User id of the user.

        Raises:
            IndexError (exception): if user id is not found.
    """
    try:
        row = df.select('user_id') \
            .where(col('user_name') == user_name).take(1)[0]
        return row.user_id
    except IndexError:
        raise IndexError()

def main():
    ti = time()
    try:
        listenbrainz_spark.init_spark_session('Candidate_set')
    except SparkSessionNotInitializedException as err:
        current_app.logger.error(str(err), exc_info=True)
        sys.exit(-1)

    try:
        mapped_df = utils.read_files_from_HDFS(path.MAPPED_LISTENS)
        recordings_df = utils.read_files_from_HDFS(path.RECORDINGS_DATAFRAME_PATH)
        users_df = utils.read_files_from_HDFS(path.USERS_DATAFRAME_PATH)
        artists_relation_df = utils.read_files_from_HDFS(path.SIMILAR_ARTIST_DATAFRAME_PATH)
    except PathNotFoundException as err:
        current_app.logger.error(str(err), exc_info=True)
        sys.exit(-1)
    except FileNotFetchedException as err:
        current_app.logger.error(str(err), exc_info=True)
        sys.exit(-1)

    listens_df = get_listens_for_rec_generation_window(mapped_df)

    metadata_file_path = os.path.join(os.path.dirname(os.path.abspath(__file__)),'recommendation-metadata.json')
    with open(metadata_file_path) as f:
        recommendation_metadata = json.load(f)
        user_names = recommendation_metadata['user_name']

    user_data = defaultdict(dict)
    similar_artists_candidate_set_df = None
    top_artists_candidate_set_df = None
    for user_name in user_names:
        ts = time()
        try:
            user_id = get_user_id(users_df, user_name)
        except IndexError:
            current_app.logger.error('{} is new/invalid user'.format(user_name))
            continue

        top_artists_df = get_top_artists(listens_df, user_name)

        top_artists_recording_ids_df = get_top_artists_recording_ids(top_artists_df, recordings_df, user_id)
        top_artists_candidate_set_df = top_artists_candidate_set_df.union(top_artists_recording_ids_df) \
            if top_artists_candidate_set_df else top_artists_recording_ids_df

        try:
            similar_artists_df = get_similar_artists(top_artists_df, artists_relation_df, user_name)
        except IndexError:
            continue

        similar_artists_recording_ids_df = get_similar_artists_recording_ids(similar_artists_df, recordings_df, user_id)
        similar_artists_candidate_set_df = similar_artists_candidate_set_df.union(similar_artists_recording_ids_df) \
            if similar_artists_candidate_set_df else similar_artists_recording_ids_df

        if SAVE_CANDIDATE_HTML:
            user_data[user_name]['artists'] = get_candidate_html_data(similar_artists_df, user_name)
            user_data[user_name]['time'] = '{:.2f}'.format(time() - ts)
        current_app.logger.info('candidate_set generated for \"{}\"'.format(user_name))

    try:
        save_candidate_sets(top_artists_candidate_set_df, similar_artists_candidate_set_df)
    except Py4JJavaError as err:
        current_app.logger.error('{}\nAborting...'.format(str(err.java_exception)), exc_info=True)
        sys.exit(-1)

    if SAVE_CANDIDATE_HTML:
        try:
            save_candidate_html(user_data)
        except SQLException as err:
            current_app.logger.error('Could not save candidate HTML\n{}'.format(str(err)), exc_info=True)
            sys.exit(-1)
