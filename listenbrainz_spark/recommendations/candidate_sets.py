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
from listenbrainz_spark.exceptions import SQLException, SparkSessionNotInitializedException, ViewNotRegisteredException, \
    PathNotFoundException, FileNotFetchedException

from flask import current_app
import pyspark.sql.functions as func
from pyspark.sql.window import Window
from pyspark.sql.functions import col, row_number
from pyspark.sql.utils import AnalysisException, ParseException

# Candidate Set HTML is generated if set to true.
SAVE_CANDIDATE_HTML = True

# Some useful dataframe fields/columns.
# top_artists_df:
#   [
#       'mb_artist_credit_id', 'msb_artist_credit_name_matchable', 'user_name'
#   ]
#
# top_artists_candidate_set_df:
#   [
#       'user_id', 'recording_id'
#   ]
#
# top_similar_artists_df:
#   [
#       'top_artist_credit_id', 'top_artist_name', 'similar_artist_credit_id', 'similar_artist_name'
#       'score', 'user_name', 'rank'
#   ]
#
# top_similar_artists_candidate_set_df:
#   [
#       'user_id', 'recording_id'
#   ]

def get_dates_to_generate_candidate_sets(mapped_df):
    """ Get window to fetch listens ti generate candidate sets.

        Args:
            mapped_df (dataframe): listens mapped with msid_mbid_mapping. Refer to candidate_sets.py
                                   for dataframe columns.

        Returns:
            from_date (datetime): Date from which start fetching listens.
            to_date (datetime): Date upto which fetch listens.
    """
    # get timestamp of latest listen in HDFS
    to_date = mapped_df.select(func.max('listened_at').alias('listened_at')).collect()[0].listened_at
    from_date = stats.adjust_days(to_date, config.RECOMMENDATION_GENERATION_WINDOW).replace(hour=0, minute=0, second=0)
    return from_date, to_date


def get_listens_to_fetch_top_artists(mapped_df, from_date, to_date):
    """ Get listens of past X days to fetch top artists where X = RECOMMENDATION_GENERATION_WINDOW.

        Args:
            mapped_df (dataframe): listens mapped with msid_mbid_mapping. Refer to candidate_sets.py
                                   for dataframe columns.
            from_date (datetime): Date from which start fetching listens.
            to_date (datetime): Date upto which fetch listens.

        Returns:
            mapped_listens_subset (dataframe): A subset of mapped_df containing user history.
    """
    mapped_listens_subset = mapped_df.filter(mapped_df.listened_at.between(from_date, to_date))
    return mapped_listens_subset


def get_top_artists(mapped_listens_subset):
    """ Get top artists listened to by users who have a listening history in
        the past X days where X = RECOMMENDATION_GENERATION_WINDOW.

        Args:
            df (dataframe): A subset of mapped_df containing user history.

        Returns:
            top_artists_df (dataframe): Top Y artists listened to by a user for all users where
                                        Y = TOP_ARTISTS_LIMIT
    """
    df = mapped_listens_subset.select('mb_artist_credit_id', 'msb_artist_credit_name_matchable', 'user_name') \
                              .groupBy('mb_artist_credit_id', 'msb_artist_credit_name_matchable', 'user_name') \
                              .agg(func.count('mb_artist_credit_id').alias('count'))

    window = Window.partitionBy('user_name').orderBy(col('count').desc())

    top_artists_df = df.withColumn('rank', row_number().over(window)) \
                       .where(col('rank') <= config.TOP_ARTISTS_LIMIT) \
                       .select('mb_artist_credit_id', 'msb_artist_credit_name_matchable', 'user_name')

    return top_artists_df


def get_top_similar_artists(top_artists_df, artists_relation_df):
    """ Get artists similar to top artists.

        Args:
            top_artists_df: Dataframe containing top artists listened to by users
            artist_relation_df: Dataframe containing artists and similar artists.
                                For columns refer to artist_relation_schema in listenbrainz_spark/schema.py.

        Returns:
            top_similar_artists_df (dataframe): Top Z artists similar to top artists where
                                                Z = SIMILAR_ARTISTS_LIMIT.
    """
    condition = [top_artists_df.mb_artist_credit_id == artists_relation_df.id_0]

    df1 = top_artists_df.join(artists_relation_df, condition, 'inner') \
                        .select(col('id_0').alias('top_artist_credit_id'),
                                col('name_0').alias('top_artist_name'),
                                col('id_1').alias('similar_artist_credit_id'),
                                col('name_1').alias('similar_artist_name'),
                                'score',
                                'user_name')

    condition = [top_artists_df.mb_artist_credit_id == artists_relation_df.id_1]

    df2 = top_artists_df.join(artists_relation_df, condition, 'inner') \
                        .select(col('id_1').alias('top_artist_credit_id'),
                                col('name_1').alias('top_artist_name'),
                                col('id_0').alias('similar_artist_credit_id'),
                                col('name_0').alias('similar_artist_name'),
                                'score',
                                'user_name')

    similar_artists_df = df1.union(df2)

    window = Window.partitionBy('top_artist_credit_id', 'user_name')\
                   .orderBy(col('score').desc())

    top_similar_artists_df = similar_artists_df.withColumn('rank', row_number().over(window)) \
                                               .where(col('rank') <= config.SIMILAR_ARTISTS_LIMIT)\
                                               .select('top_artist_credit_id', 'top_artist_name',
                                                       'similar_artist_credit_id', 'similar_artist_name',
                                                       'score', 'user_name')

    return top_similar_artists_df


def get_top_artists_candidate_set(top_artists_df, recordings_df, users_df):
    """ Get recording ids that belong to top artists.

        Args:
            top_artists_df: Dataframe containing top artists listened to by users.
            recordings_df: Dataframe containing distinct recordings and corresponding
                           mbids and names.
            users_df: Dataframe containing user names and user ids.

        Returns:
            top_artists_candidate_set_df (dataframe): recording ids that belong to top artists
                                                      corresponding to user ids.
    """
    condition = ['mb_artist_credit_id', 'msb_artist_credit_name_matchable']

    df = top_artists_df.join(recordings_df, condition, 'inner')

    top_artists_candidate_set_df = df.join(users_df, 'user_name', 'inner')\
                                     .select('recording_id', 'user_id', 'user_name')

    return top_artists_candidate_set_df


def get_top_similar_artists_candidate_set(top_similar_artists_df, recordings_df, users_df):
    """ Get recording ids that belong to similar artists.

        Args:
            top_similar_artists_df: Dataframe containing artists similar to top artists.
            recordings_df: Dataframe containing distinct recordings and corresponding
                           mbids and names.
            users_df: Dataframe containing user names and user ids.

        Returns:
            top_similar_artists_candidate_set_df (dataframe): recording ids that belong to similar artists
                                                              corresponding to user ids.
    """
    condition = [
                    top_similar_artists_df.similar_artist_credit_id == recordings_df.mb_artist_credit_id,
                    top_similar_artists_df.similar_artist_name == recordings_df.msb_artist_credit_name_matchable
    ]

    df = top_similar_artists_df.join(recordings_df, condition, 'inner')

    top_similar_artists_candidate_set_df = df.join(users_df, 'user_name', 'inner')\
                                             .select('recording_id', 'user_id', 'user_name')

    return top_similar_artists_candidate_set_df


def save_candidate_sets(top_artists_candidate_set_df, top_similar_artists_candidate_set_df):
    """ Save candidate sets to HDFS.

        Args:
            top_artists_candidate_set_df (dataframe): recording ids that belong to top artists
                                                      corresponding to user ids.
            top_similar_artists_candidate_set_df (dataframe): recording ids that belong to similar artists
                                                              corresponding to user ids.
    """
    utils.save_parquet(top_artists_candidate_set_df, path.TOP_ARTIST_CANDIDATE_SET)
    utils.save_parquet(top_similar_artists_candidate_set_df, path.SIMILAR_ARTIST_CANDIDATE_SET)


def get_candidate_html_data(top_similar_artists_df):
    """ Get top and similar artists associated to users. The function is invoked
        when candidate set HTML is to be generated.

        Args:
            top_similar_artists_df: Dataframe containing artists similar to top artists

        Returns:
            user_data: Dictionary can be depicted as:
                {
                    'user 1' : ['top_artist 1', 'similar_artist 1', 'score'],
                    .
                    .
                    .
                    'user n' : ['top_artist Y', 'similar_artist Z' ... 'score'],
                }
    """
    user_data = defaultdict(list)
    for row in top_similar_artists_df.collect():
        user_data[row.user_name].append((row.top_artist_name, row.similar_artist_name, row.score))
    return user_data


def save_candidate_html(user_data, total_time):
    """ Save user data to an HTML file.

        Args:
            user_data (dict): Top and similar artists associated to users.
            total_time (str): time taken to generate candidate_sets
    """
    date = datetime.utcnow().strftime('%Y-%m-%d')
    candidate_html = 'Candidate-{}-{}.html'.format(uuid.uuid4(), date)
    context = {
        'user_data': user_data,
        'total_time': total_time,
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
    time_initial = time()
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

    from_date, to_date = get_dates_to_generate_candidate_sets(mapped_df)

    current_app.logger.info('Fetching listens to get top artists...')
    mapped_listens_subset = get_listens_to_fetch_top_artists(mapped_df, from_date, to_date)

    current_app.logger.info('Fetching top artists...')
    top_artists_df = get_top_artists(mapped_listens_subset)

    current_app.logger.info('Preparing top artists candidate set...')
    top_artists_candidate_set_df = get_top_artists_candidate_set(top_artists_df, recordings_df, users_df)

    current_app.logger.info('Fetching similar artists...')
    top_similar_artists_df = get_top_similar_artists(top_artists_df, artists_relation_df)

    current_app.logger.info('Preparing similar artists candidate set...')
    top_similar_artists_candidate_set_df = get_top_similar_artists_candidate_set(top_similar_artists_df, recordings_df, users_df)

    try:
        current_app.logger.info('Saving candidate sets...')
        save_candidate_sets(top_artists_candidate_set_df, top_similar_artists_candidate_set_df)
        current_app.logger.info('Done!')
    except Py4JJavaError as err:
        current_app.logger.error('{}\nAborting...'.format(str(err.java_exception)), exc_info=True)
        sys.exit(-1)

    # time taken to generate candidate_sets
    total_time = '{:.2f}'.format((time() - time_initial) / 60)
    if SAVE_CANDIDATE_HTML:
        user_data = get_candidate_html_data(top_similar_artists_df)
        current_app.logger.info('Saving HTML...')
        save_candidate_html(user_data, total_time)
        current_app.logger.info('Done!')

    message =  [{
        'type': 'cf_recording_candidate_sets',
        'candidate_sets_upload_time': str(datetime.utcnow()),
        'total_time': total_time,
        'from_date': str(from_date),
        'to_date': str(to_date)
    }]

    return message
