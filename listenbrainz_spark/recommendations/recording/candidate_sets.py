"""
This script is responsible for creating candidate sets for all users. Candidate sets are dataframes containing
(spark_user_id, recording_id). The generated candidate sets will be given as input to the recommender that will assign ratings
to the recordings in candidate sets. The general flow is as follows:

The listens of the last 7 days are filtered from mapped_listens_df and this is called the mapped_listens_subset_df.
Top X (an int supplied as an argument to the script) artists are fetched for each user from the mapped_listens_subset_df.
The top_artist_df is joined with recordings_df to get the dataframe of recordings belonging to the top artists. From this dataframe,
recordings listened to by the users in the last 7 days are filtered so that the recommendations don't contain
recordings that the user has listened to in the last week. The resultant dataframe is called the top_artists_candidate_set_df.

Artists similar to top artists are fetched from the artist_relations_df and the similar_artist_candidate_set_df is generated
in a manner similar to the generation of the top artist candidate set.

The top artist and similar artist candidate set dataframes are saved to HDFS. For HDFS path of dataframes refer to listenbrainz_spark/path.py

Note: users and recordings that are in candidate set but not in the training set will be discarded by the recommender.
"""

import uuid
import logging
import time
from datetime import datetime
from collections import defaultdict
from py4j.protocol import Py4JJavaError

import listenbrainz_spark
from listenbrainz_spark import stats, utils, path
from listenbrainz_spark.recommendations.utils import save_html
from listenbrainz_spark.exceptions import (SparkSessionNotInitializedException,
                                           ViewNotRegisteredException,
                                           PathNotFoundException,
                                           FileNotFetchedException,
                                           TopArtistNotFetchedException,
                                           SimilarArtistNotFetchedException,
                                           FileNotSavedException)

import pyspark.sql.functions as func
from pyspark.sql.window import Window
from pyspark.sql.functions import col, row_number
from pyspark.sql.types import StringType, ArrayType


logger = logging.getLogger(__name__)


# Some useful dataframe fields/columns.
# top_artist_df:
#   [
#       'top_artist_credit_id',
#       'top_artist_name',
#       'user_id'
#   ]
#
# top_artist_candidate_set_df:
#   [
#       'spark_user_id',
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
#       'user_id',
#       'spark_user_id'
#   ]
#
# similar_artist_df:
#   [
#       'similar_artist_credit_id',
#       'similar_artist_name'
#       'user_id'
#   ]
#
# similar_artist_candidate_set_df:
#   [
#       'spark_user_id',
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
#       'user_id',
#       'spark_user_id'
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
    from_date = stats.offset_days(to_date, recommendation_generation_window).replace(hour=0, minute=0, second=0)
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


def _is_empty_dataframe(df):
    """ Return True if the dataframe is empty, return False otherwise.
    """

    try:
        df.take(1)[0]
    except IndexError:
        return True

    return False


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
    df = mapped_listens_subset\
        .select(
            'artist_credit_id',
            'user_id'
        ) \
        .groupBy(
            'artist_credit_id',
            'user_id'
        ) \
        .agg(func.count('artist_credit_id').alias('total_count'))

    window = Window.partitionBy('user_id').orderBy(col('total_count').desc())

    top_artist_df = df.withColumn('rank', row_number().over(window)) \
                      .where(col('rank') <= top_artist_limit) \
                      .select(col('artist_credit_id').alias('top_artist_credit_id'),
                              col('user_id'))

    if users:
        top_artist_given_users_df = top_artist_df.select('top_artist_credit_id',
                                                         'user_id') \
                                                 .where(top_artist_df.user_id.isin(users))

        if _is_empty_dataframe(top_artist_given_users_df):
            logger.error('Top artists for {} not fetched'.format(users), exc_info=True)
            raise TopArtistNotFetchedException('Users inactive or data missing from msid->mbid mapping')

        return top_artist_given_users_df

    if _is_empty_dataframe(top_artist_df):
        logger.error('Top artists not fetched', exc_info=True)
        raise TopArtistNotFetchedException('Users inactive or data missing from msid->mbid mapping')

    return top_artist_df


def filter_top_artists_from_similar_artists(similar_artist_df, top_artist_df):
    """ Filter artists from similar artist dataframe for a user who have already made it to
        top artist dataframe.

        Args:
            similar_artist_df: Similar artist dataframe.
            top_artist_df: Top artist dataframe.

        Returns:
            res_df: Similar artist dataframe that does not contain top artists.
    """

    df = top_artist_df.select(col('top_artist_credit_id').alias('artist_credit_id'),
                              col('user_id').alias('user'))

    condition = [
        similar_artist_df.similar_artist_credit_id == df.artist_credit_id,
        similar_artist_df.user_id == df.user
    ]

    res_df = similar_artist_df.join(df, condition, 'left') \
                              .select('top_artist_credit_id',
                                      'similar_artist_credit_id',
                                      'user_id') \
                              .where(col('artist_credit_id').isNull() & col('user').isNull())

    return res_df


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
                               col('id_1').alias('similar_artist_credit_id'),
                               'score',
                               'user_id')

    condition = [top_artist_df.top_artist_credit_id == artist_relation_df.id_1]

    df2 = top_artist_df.join(artist_relation_df, condition, 'inner') \
                       .select(col('id_1').alias('top_artist_credit_id'),
                               col('id_0').alias('similar_artist_credit_id'),
                               'score',
                               'user_id')

    df = df1.union(df2)

    window = Window.partitionBy('top_artist_credit_id', 'user_id')\
                   .orderBy(col('score').desc())

    similar_artist_df_html = df.withColumn('rank', row_number().over(window)) \
                               .where(col('rank') <= similar_artist_limit)\
                               .select('top_artist_credit_id',
                                       'similar_artist_credit_id',
                                       'user_id')

    similar_artist_df_html = filter_top_artists_from_similar_artists(similar_artist_df_html, top_artist_df)

    # Two or more artists can have same similar artist(s) leading to non-unique recordings
    # therefore we have filtered the distinct similar artists.
    similar_artist_df = similar_artist_df_html.select('similar_artist_credit_id',
                                                      'user_id') \
                                              .distinct()

    if _is_empty_dataframe(similar_artist_df):
        logger.error('Similar artists not generated.', exc_info=True)
        raise SimilarArtistNotFetchedException('Artists missing from artist relation')

    return similar_artist_df, similar_artist_df_html


def filter_last_x_days_recordings(candidate_set_df, mapped_listens_subset):
    """ Filter recordings from candidate set that the user has listened in the last X
        days where X = RECOMMENDATION_GENERATION_WINDOW.

        Args:
            candidate_set_df: top/similar artist candidate set.
            mapped_listens_subset: dataframe containing user listening history of last X days.

        Returns:
            candidate_set without recordings of last X days of a user for all users.
    """
    df = mapped_listens_subset.select(
        col('recording_mbid').alias('recording_mbid2'),
        col('user_id').alias('user')
    ).distinct()

    condition = [
        candidate_set_df.recording_mbid == df.recording_mbid2,
        candidate_set_df.user_id == df.user
    ]

    filtered_df = candidate_set_df \
        .join(df, condition, 'left') \
        .select('*') \
        .where(df.recording_mbid2.isNull() & df.user.isNull())

    return filtered_df.drop('recording_mbid2', 'user')


def get_top_artist_candidate_set(top_artist_df, recordings_df, users_df, mapped_listens_subset):
    """ Get recording ids that belong to top artists.

        Args:
            top_artist_df: Dataframe containing top artists listened to by users.
            recordings_df: Dataframe containing distinct recordings and corresponding
                           mbids and names.
            users_df: Dataframe containing user names and user ids.
            mapped_listens_subset: dataframe containing user listening history of last X days .

        Returns:
            top_artist_candidate_set_df (dataframe): recording ids that belong to top artists
                                                     corresponding to user ids.
            top_artists_candidate_set_df_html (dataframe): top artist info required for html file
    """
    condition = [
        top_artist_df.top_artist_credit_id == recordings_df.artist_credit_id
    ]

    df = top_artist_df.join(recordings_df, condition, 'inner')

    top_artist_candidate_set_df_html = df.join(users_df, 'user_id', 'inner') \
                  .select('top_artist_credit_id',
                          'artist_credit_id',
                          'recording_mbid',
                          'recording_id',
                          'user_id',
                          'spark_user_id')

    # top_artist_candidate_set_df_html = filter_last_x_days_recordings(joined_df, mapped_listens_subset)

    top_artist_candidate_set_df = top_artist_candidate_set_df_html.select('recording_id', 'spark_user_id', 'user_id')

    return top_artist_candidate_set_df, top_artist_candidate_set_df_html


def get_similar_artist_candidate_set(similar_artist_df, recordings_df, users_df, mapped_listens_subset):
    """ Get recording ids that belong to similar artists.

        Args:
            similar_artist_df: Dataframe containing artists similar to top artists.
            recordings_df: Dataframe containing distinct recordings and corresponding
                           mbids and names.
            users_df: Dataframe containing user names and user ids.
            mapped_listens_subset: dataframe containing user listening history of last X days .

        Returns:
            similar_artist_candidate_set_df (dataframe): recording ids that belong to similar artists
                                                         corresponding to user ids.
            similar_artist_candidate_set_df_html (dataframe): similar artist info for html file
    """
    condition = [
        similar_artist_df.similar_artist_credit_id == recordings_df.artist_credit_id
    ]

    df = similar_artist_df.join(recordings_df, condition, 'inner')

    similar_artist_candidate_set_df_html = df.join(users_df, 'user_id', 'inner') \
                  .select('similar_artist_credit_id',
                          'artist_credit_id',
                          'recording_mbid',
                          'recording_id',
                          'user_id',
                          'spark_user_id')

    # similar_artist_candidate_set_df_html = filter_last_x_days_recordings(joined_df, mapped_listens_subset)

    similar_artist_candidate_set_df = similar_artist_candidate_set_df_html.select('recording_id', 'spark_user_id', 'user_id')

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
        utils.save_parquet(top_artist_candidate_set_df, path.RECOMMENDATION_RECORDING_TOP_ARTIST_CANDIDATE_SET)
    except FileNotSavedException as err:
        logger.error(str(err), exc_info=True)
        raise

    try:
        utils.save_parquet(similar_artist_candidate_set_df, path.RECOMMENDATION_RECORDING_SIMILAR_ARTIST_CANDIDATE_SET)
    except FileNotSavedException as err:
        logger.error(str(err), exc_info=True)
        raise


def get_candidate_html_data(similar_artist_candidate_set_df_html, top_artist_candidate_set_df_html,
                            top_artist_df, similar_artist_df_html):

    """ Get artists and recordings associated with users for HTML. The function is invoked
        when candidate set HTML is to be generated.

        Args:
            similar_artist_candidate_set_df_html (dataframe): similar artists and related info.
            top_artist_candidate_set_df_html (dataframe): top artists and related info.
            top_artist_df (dataframe) : top artists listened to by users.
            similar_artist_df_html (dataframe): similar artists and corresponding top artists

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

        if row.user_id not in user_data:
            user_data[row.user_id] = defaultdict(list)

        data = (
            row.top_artist_credit_id
        )
        user_data[row.user_id]['top_artist'].append(data)

    for row in similar_artist_df_html.collect():
        data = (
            row.top_artist_credit_id,
            row.similar_artist_credit_id
        )
        user_data[row.user_id]['similar_artist'].append(data)

    for row in top_artist_candidate_set_df_html.collect():
        data = (
            row.top_artist_credit_id,
            row.artist_credit_id,
            row.recording_mbid,
            row.recording_id
        )
        user_data[row.user_id]['top_artist_candidate_set'].append(data)

    for row in similar_artist_candidate_set_df_html.collect():
        data = (
            row.similar_artist_credit_id,
            row.artist_credit_id,
            row.recording_mbid,
            row.recording_id
        )
        user_data[row.user_id]['similar_artist_candidate_set'].append(data)

    return user_data


def save_candidate_html(user_data, total_time, from_date, to_date):
    """ Save user data to an HTML file.

        Args:
            user_data (dict): Top and similar artists associated to users.
            total_time (str): time taken to generate candidate_sets
    """
    date = datetime.utcnow().strftime('%Y-%m-%d-%H:%M')
    candidate_html = 'Candidate-{}-{}.html'.format(date, uuid.uuid4())
    context = {
        'user_data': user_data,
        'total_time': total_time,
        'from_date': from_date,
        'to_date': to_date
    }
    save_html(candidate_html, context, 'candidate.html')


def main(recommendation_generation_window=None, top_artist_limit=None, similar_artist_limit=None,
         users=None, html_flag=False):

    time_initial = time.monotonic()
    try:
        listenbrainz_spark.init_spark_session('Candidate_set')
    except SparkSessionNotInitializedException as err:
        logger.error(str(err), exc_info=True)
        raise

    try:
        mapped_listens_df = utils.read_files_from_HDFS(path.RECOMMENDATION_RECORDING_MAPPED_LISTENS)
        recordings_df = utils.read_files_from_HDFS(path.RECOMMENDATION_RECORDINGS_DATAFRAME)
        users_df = utils.read_files_from_HDFS(path.RECOMMENDATION_RECORDING_USERS_DATAFRAME)
        artist_relation_df = utils.read_files_from_HDFS(path.SIMILAR_ARTIST_DATAFRAME_PATH)
    except PathNotFoundException as err:
        logger.error(str(err), exc_info=True)
        raise
    except FileNotFetchedException as err:
        logger.error(str(err), exc_info=True)
        raise

    logger.info('Fetching listens to get top artists...')
    if recommendation_generation_window is not None:
        logger.info('Recommendation generation window is specified, calculating subset of listens')
        from_date, to_date = get_dates_to_generate_candidate_sets(mapped_listens_df, recommendation_generation_window)
        mapped_listens_df = get_listens_to_fetch_top_artists(mapped_listens_df, from_date, to_date)
    else:
        from_date, to_date = None, None

    logger.info('Fetching top artists...')
    top_artist_df = get_top_artists(mapped_listens_df, top_artist_limit, users)

    logger.info('Preparing top artists candidate set...')
    top_artist_candidate_set_df, top_artist_candidate_set_df_html = get_top_artist_candidate_set(top_artist_df, recordings_df,
                                                                                                 users_df, mapped_listens_df)

    logger.info('Fetching similar artists...')
    similar_artist_df, similar_artist_df_html = get_similar_artists(top_artist_df, artist_relation_df, similar_artist_limit)

    logger.info('Preparing similar artists candidate set...')
    similar_artist_candidate_set_df, similar_artist_candidate_set_df_html = get_similar_artist_candidate_set(
                                                                                similar_artist_df,
                                                                                recordings_df,
                                                                                users_df,
                                                                                mapped_listens_df)

    logger.info('Saving candidate sets...')
    save_candidate_sets(top_artist_candidate_set_df, similar_artist_candidate_set_df)
    logger.info('Done!')

    # time taken to generate candidate_sets
    total_time = '{:.2f}'.format((time.monotonic() - time_initial) / 60)
    if html_flag:
        user_data = get_candidate_html_data(similar_artist_candidate_set_df_html, top_artist_candidate_set_df_html,
                                            top_artist_df, similar_artist_df_html)

        logger.info('Saving HTML...')
        save_candidate_html(user_data, total_time, from_date, to_date)
        logger.info('Done!')

    message = [{
        'type': 'cf_recommendations_recording_candidate_sets',
        'candidate_sets_upload_time': str(datetime.utcnow()),
        'total_time': total_time,
        'from_date': str(from_date),
        'to_date': str(to_date)
    }]

    return message
