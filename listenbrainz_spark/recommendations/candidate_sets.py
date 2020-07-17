import os
import sys
import uuid
import logging
from time import time
from datetime import datetime
from collections import defaultdict
from py4j.protocol import Py4JJavaError

import listenbrainz_spark
from listenbrainz_spark import stats, utils, path
from listenbrainz_spark.recommendations.utils import (save_html,
                                                      check_html_files_dir_path,
                                                      HTML_FILES_PATH)
from listenbrainz_spark.exceptions import (SparkSessionNotInitializedException,
                                           ViewNotRegisteredException,
                                           PathNotFoundException,
                                           FileNotFetchedException)

from flask import current_app
import pyspark.sql.functions as func
from pyspark.sql.window import Window
from pyspark.sql.functions import col, row_number

# Candidate Set HTML is generated if set to true.
SAVE_CANDIDATE_HTML = True

# Some useful dataframe fields/columns.
# top_artist_df:
#   [
#       'top_artist_credit_id',
#       'top_artist_name',
#       'user_name'
#   ]
#
# top_artist_candidate_set_df:
#   [
#       'user_id',
#       'recording_id'
#   ]
#
# top_artist_candidate_set_df_html:
#   [
#       'top_artist_credit_id',
#       'top_artist_name',
#       'mb_artist_credit_id',
#       'mb_artist_credit_mbids',
#       'mb_recording_mbid',
#       'msb_artist_credit_name_matchable',
#       'msb_recording_name_matchable',
#       'recording_id',
#       'user_name',
#       'user_id'
#   ]
#
# similar_artist_df:
#   [
#       'similar_artist_credit_id',
#       'similar_artist_name'
#       'user_name'
#   ]
#
# similar_artist_candidate_set_df:
#   [
#       'user_id',
#       'recording_id'
#   ]
#
# similar_artist_candidate_set_df_html:
#   [
#       'similar_artist_credit_id',
#       'similar_artist_name',
#       'mb_artist_credit_id',
#       'mb_artist_credit_mbids',
#       'mb_recording_mbid',
#       'msb_artist_credit_name_matchable',
#       'msb_recording_name_matchable',
#       'recording_id',
#       'user_name',
#       'user_id'
#   ]


def get_dates_to_generate_candidate_sets(mapped_listens_df, recommendation_generation_window):
    """ Get window to fetch listens to generate candidate sets.

        Args:
            mapped_listens_df (dataframe): listens mapped with msid_mbid_mapping. Refer to create_dataframe.py
                                           for dataframe columns.
            recommendation_generation_window (int): recommendations to be generated on history of given number of days.

        Returns:
            from_date (datetime): Date from which start fetching listens.
            to_date (datetime): Date upto which fetch listens.
    """
    # get timestamp of latest listen in HDFS
    to_date = mapped_listens_df.select(func.max('listened_at').alias('listened_at')).collect()[0].listened_at
    from_date = stats.adjust_days(to_date, recommendation_generation_window).replace(hour=0, minute=0, second=0)
    return from_date, to_date


def get_listens_to_fetch_top_artists(mapped_listens_df, from_date, to_date):
    """ Get listens of past X days to fetch top artists where X = RECOMMENDATION_GENERATION_WINDOW.

        Args:
            mapped_listens_df (dataframe): listens mapped with msid_mbid_mapping.
            from_date (datetime): Date from which start fetching listens.
            to_date (datetime): Date upto which fetch listens.

        Returns:
            mapped_listens_subset (dataframe): A subset of mapped_listens_df containing user history.
    """
    mapped_listens_subset = mapped_listens_df.filter(mapped_listens_df.listened_at.between(from_date, to_date))
    return mapped_listens_subset


def get_top_artists(mapped_listens_subset, top_artist_limit, users):
    """ Get top artists listened to by users who have a listening history in
        the past X days where X = RECOMMENDATION_GENERATION_WINDOW.

        Args:
            df (dataframe): A subset of mapped_listens_df containing user history.
            top_artist_limit (int): number of top artist to calculate
            users: list of users to generate candidate sets.

        Returns:
            if users is an empty list:
                top_artist_df (dataframe): Top Y artists listened to by a user for all users where
                                           Y = TOP_ARTISTS_LIMIT
            else:
                top_artist_given_users_df (dataframe): Top Y artists listened to by a user for given users where
                                                       Y = TOP_ARTISTS_LIMIT
    """
    df = mapped_listens_subset.select('mb_artist_credit_id',
                                      'msb_artist_credit_name_matchable',
                                      'user_name') \
                              .groupBy('mb_artist_credit_id',
                                       'msb_artist_credit_name_matchable',
                                       'user_name') \
                              .agg(func.count('mb_artist_credit_id').alias('total_count'))

    window = Window.partitionBy('user_name').orderBy(col('total_count').desc())

    top_artist_df = df.withColumn('rank', row_number().over(window)) \
                      .where(col('rank') <= top_artist_limit) \
                      .select(col('mb_artist_credit_id').alias('top_artist_credit_id'),
                              col('msb_artist_credit_name_matchable').alias('top_artist_name'),
                              col('user_name'),
                              col('total_count'))
    if users:
        top_artist_given_users_df = top_artist_df.select('top_artist_credit_id',
                                                         'top_artist_name',
                                                         'user_name',
                                                         'total_count') \
                                                 .where(top_artist_df.user_name.isin(users))
        return top_artist_given_users_df

    return top_artist_df


def get_similar_artists(top_artist_df, artist_relation_df, similar_artist_limit):
    """ Get artists similar to top artists.

        Args:
            top_artist_df: Dataframe containing top artists listened to by users
            artist_relation_df: Dataframe containing artists and similar artists.
                                For columns refer to artist_relation_schema in listenbrainz_spark/schema.py.
            similar_artist_limit (int): number of similar artist to calculate

        Returns:
            similar_artist_df (dataframe): Top Z artists similar to top artists where
                                           Z = SIMILAR_ARTISTS_LIMIT.
    """
    condition = [top_artist_df.top_artist_credit_id == artist_relation_df.id_0]

    df1 = top_artist_df.join(artist_relation_df, condition, 'inner') \
                       .select(col('id_0').alias('top_artist_credit_id'),
                               col('name_0').alias('top_artist_name'),
                               col('id_1').alias('similar_artist_credit_id'),
                               col('name_1').alias('similar_artist_name'),
                               'score',
                               'user_name')

    condition = [top_artist_df.top_artist_credit_id == artist_relation_df.id_1]

    df2 = top_artist_df.join(artist_relation_df, condition, 'inner') \
                       .select(col('id_1').alias('top_artist_credit_id'),
                               col('name_1').alias('top_artist_name'),
                               col('id_0').alias('similar_artist_credit_id'),
                               col('name_0').alias('similar_artist_name'),
                               'score',
                               'user_name')

    df = df1.union(df2)

    window = Window.partitionBy('top_artist_credit_id', 'user_name')\
                   .orderBy(col('score').desc())

    similar_artist_df = df.withColumn('rank', row_number().over(window)) \
                          .where(col('rank') <= similar_artist_limit)\
                          .select('similar_artist_credit_id',
                                  'similar_artist_name',
                                  'user_name') \
                          .distinct()

    return similar_artist_df


def get_top_artist_candidate_set(top_artist_df, recordings_df, users_df):
    """ Get recording ids that belong to top artists.

        Args:
            top_artist_df: Dataframe containing top artists listened to by users.
            recordings_df: Dataframe containing distinct recordings and corresponding
                           mbids and names.
            users_df: Dataframe containing user names and user ids.

        Returns:
            top_artist_candidate_set_df (dataframe): recording ids that belong to top artists
                                                     corresponding to user ids.
            top_artists_candidate_set_df_html (dataframe): top artist info required for html file
    """
    condition = [
        top_artist_df.top_artist_credit_id == recordings_df.mb_artist_credit_id,
        top_artist_df.top_artist_name == recordings_df.msb_artist_credit_name_matchable
    ]

    df = top_artist_df.join(recordings_df, condition, 'inner')

    top_artist_candidate_set_df_html = df.join(users_df, 'user_name', 'inner') \
                                         .select('top_artist_credit_id',
                                                 'top_artist_name',
                                                 'mb_artist_credit_id',
                                                 'mb_artist_credit_mbids',
                                                 'mb_recording_mbid',
                                                 'msb_artist_credit_name_matchable',
                                                 'msb_recording_name_matchable',
                                                 'recording_id',
                                                 'user_name',
                                                 'user_id')

    top_artist_candidate_set_df = top_artist_candidate_set_df_html.select('recording_id', 'user_id', 'user_name')

    return top_artist_candidate_set_df, top_artist_candidate_set_df_html

def get_similar_artist_candidate_set(similar_artist_df, recordings_df, users_df):
    """ Get recording ids that belong to similar artists.

        Args:
            similar_artist_df: Dataframe containing artists similar to top artists.
            recordings_df: Dataframe containing distinct recordings and corresponding
                           mbids and names.
            users_df: Dataframe containing user names and user ids.

        Returns:
            similar_artist_candidate_set_df (dataframe): recording ids that belong to similar artists
                                                         corresponding to user ids.
            similar_artist_candidate_set_df_html (dataframe): similar artist info for html file
    """
    condition = [
        similar_artist_df.similar_artist_credit_id == recordings_df.mb_artist_credit_id,
        similar_artist_df.similar_artist_name == recordings_df.msb_artist_credit_name_matchable
    ]

    df = similar_artist_df.join(recordings_df, condition, 'inner')

    similar_artist_candidate_set_df_html = df.join(users_df, 'user_name', 'inner') \
                                             .select('similar_artist_credit_id',
                                                     'similar_artist_name',
                                                     'mb_artist_credit_id',
                                                     'mb_artist_credit_mbids',
                                                     'mb_recording_mbid',
                                                     'msb_artist_credit_name_matchable',
                                                     'msb_recording_name_matchable',
                                                     'recording_id',
                                                     'user_name',
                                                     'user_id')

    similar_artist_candidate_set_df = similar_artist_candidate_set_df_html.select('recording_id', 'user_id', 'user_name')

    return similar_artist_candidate_set_df, similar_artist_candidate_set_df_html


def save_candidate_sets(top_artist_candidate_set_df, similar_artist_candidate_set_df):
    """ Save candidate sets to HDFS.

        Args:
            top_artist_candidate_set_df (dataframe): recording ids that belong to top artists
                                                     corresponding to user ids.
            similar_artist_candidate_set_df (dataframe): recording ids that belong to similar artists
                                                         corresponding to user ids.
    """
    try:
        top_artist_candidate_set_df.take(1)[0]
    except IndexError:
        current_app.logger.error('Cannot save empty top artist candidate set', exc_info=True)
        sys.exit(-1)

    try:
        similar_artist_candidate_set_df.take(1)[0]
    except IndexError:
        current_app.logger.error('Cannot save empty similar artist candidate set', exc_info=True)
        sys.exit(-1)

    try:
        utils.save_parquet(top_artist_candidate_set_df, path.TOP_ARTIST_CANDIDATE_SET)
    except FileNotSavedException as err:
        current_app.logger.error(str(err), exc_info=True)
        sys.exit(-1)

    try:
        utils.save_parquet(similar_artist_candidate_set_df, path.SIMILAR_ARTIST_CANDIDATE_SET)
    except FileNotSavedException as err:
        current_app.logger.error(str(err), exc_info=True)
        sys.exit(-1)


def get_candidate_html_data(similar_artist_candidate_set_df_html, top_artist_candidate_set_df_html,
                            top_artist_df, similar_artist_df):

    """ Get artists and recordings associated with users for HTML. The function is invoked
        when candidate set HTML is to be generated.

        Args:
            similar_artist_candidate_set_df_html (dataframe): similar artists and related info.
            top_artist_candidate_set_df_html (dataframe): top artists and related info.
            top_artist_df (dataframe) : top artists listened to by users.
            similar_artist_df (dataframe): artists similar to top artists.

        Returns:
            user_data: Dictionary can be depicted as:
                {
                    'user 1' : {
                        'top_artist': [],
                        'top_similar_artist': [],
                        'top_artist_candidate_set': [],
                        'top_similar_artist_candidate_set': []
                    }
                    .
                    .
                    .
                }
    """
    user_data = defaultdict(list)
    for row in top_artist_df.collect():
        user_data[row.user_name] = defaultdict(list)
        data = (
            row.top_artist_name,
            row.top_artist_credit_id,
            row.total_count
        )
        user_data[row.user_name]['top_artist'].append(data)

    for row in similar_artist_df.collect():
        data = (
            row.similar_artist_name,
            row.similar_artist_credit_id
        )
        user_data[row.user_name]['similar_artist'].append(data)

    for row in top_artist_candidate_set_df_html.collect():
        data = (
            row.top_artist_credit_id,
            row.top_artist_name,
            row.mb_artist_credit_id,
            row.mb_artist_credit_mbids,
            row.mb_recording_mbid,
            row.msb_artist_credit_name_matchable,
            row.msb_recording_name_matchable,
            row.recording_id
        )
        user_data[row.user_name]['top_artist_candidate_set'].append(data)

    for row in similar_artist_candidate_set_df_html.collect():
        data = (
            row.similar_artist_credit_id,
            row.similar_artist_name,
            row.mb_artist_credit_id,
            row.mb_artist_credit_mbids,
            row.mb_recording_mbid,
            row.msb_artist_credit_name_matchable,
            row.msb_recording_name_matchable,
            row.recording_id
        )
        user_data[row.user_name]['similar_artist_candidate_set'].append(data)

    return user_data


def save_candidate_html(user_data, total_time, from_date, to_date):
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
        'from_date': from_date,
        'to_date': to_date
    }
    save_html(candidate_html, context, 'candidate.html')


def main(recommendation_generation_window=None, top_artist_limit=None, similar_artist_limit=None, users=None):

    time_initial = time()
    try:
        listenbrainz_spark.init_spark_session('Candidate_set')
    except SparkSessionNotInitializedException as err:
        current_app.logger.error(str(err), exc_info=True)
        sys.exit(-1)

    try:
        mapped_listens_df = utils.read_files_from_HDFS(path.MAPPED_LISTENS)
        recordings_df = utils.read_files_from_HDFS(path.RECORDINGS_DATAFRAME_PATH)
        users_df = utils.read_files_from_HDFS(path.USERS_DATAFRAME_PATH)
        artist_relation_df = utils.read_files_from_HDFS(path.SIMILAR_ARTIST_DATAFRAME_PATH)
    except PathNotFoundException as err:
        current_app.logger.error(str(err), exc_info=True)
        sys.exit(-1)
    except FileNotFetchedException as err:
        current_app.logger.error(str(err), exc_info=True)
        sys.exit(-1)

    from_date, to_date = get_dates_to_generate_candidate_sets(mapped_listens_df, recommendation_generation_window)

    current_app.logger.info('Fetching listens to get top artists...')
    mapped_listens_subset = get_listens_to_fetch_top_artists(mapped_listens_df, from_date, to_date)

    current_app.logger.info('Fetching top artists...')
    top_artist_df = get_top_artists(mapped_listens_subset, top_artist_limit, users)

    current_app.logger.info('Preparing top artists candidate set...')
    top_artist_candidate_set_df, top_artist_candidate_set_df_html = get_top_artist_candidate_set(top_artist_df, recordings_df,
                                                                                                 users_df)

    current_app.logger.info('Fetching similar artists...')
    similar_artist_df = get_similar_artists(top_artist_df, artist_relation_df, similar_artist_limit)

    current_app.logger.info('Preparing similar artists candidate set...')
    similar_artist_candidate_set_df, similar_artist_candidate_set_df_html = get_similar_artist_candidate_set(similar_artist_df,
                                                                                                             recordings_df,
                                                                                                             users_df)
    try:
        current_app.logger.info('Saving candidate sets...')
        save_candidate_sets(top_artist_candidate_set_df, similar_artist_candidate_set_df)
        current_app.logger.info('Done!')
    except Py4JJavaError as err:
        current_app.logger.error('{}\nAborting...'.format(str(err.java_exception)), exc_info=True)
        sys.exit(-1)

    # time taken to generate candidate_sets
    total_time = '{:.2f}'.format((time() - time_initial) / 60)
    if SAVE_CANDIDATE_HTML:
        user_data = get_candidate_html_data(similar_artist_candidate_set_df_html, top_artist_candidate_set_df_html,
                                            top_artist_df, similar_artist_df)

        dir_exists = check_html_files_dir_path()
        if not dir_exists:
            os.mkdir(HTML_FILES_PATH)

        current_app.logger.info('Saving HTML...')
        save_candidate_html(user_data, total_time, from_date, to_date)
        current_app.logger.info('Done!')

    message = [{
        'type': 'cf_recording_candidate_sets',
        'candidate_sets_upload_time': str(datetime.utcnow()),
        'total_time': total_time,
        'from_date': str(from_date),
        'to_date': str(to_date)
    }]

    return message
