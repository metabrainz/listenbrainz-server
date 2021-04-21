"""
This script is responsible for creating candidate sets for all users. Candidate sets are dataframes containing
(user_id, recording_id). The generated candidate sets will be given as input to the recommender that will assign ratings
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


def convert_string_datatype_to_array(df):
    """ Convert string datatype col to array<string> datatype.
    """
    def convert_to_list(x):
        res = []
        res.append(x)
        return res

    convert_to_list_udf = func.udf(convert_to_list, ArrayType(StringType()))
    res_df = df.withColumn("mb_artist_credit_mbids", convert_to_list_udf(col("mbids")))

    return res_df


def explode_artist_collaborations(df):
    """ artist_mbids is a list of artist mbid of artists to which a track belongs.
        Explode the artist_mbids list and get the indivial artist mbid.

        For Example:
            Before:
            -----------------------
            |  artist_credit_mbids|
            -----------------------
            |               [a, b]|
            -----------------------

            After:
            -----------------------
            |  artist_credit_mbids|
            -----------------------
            |                    a|
            -----------------------
            |                    b|
            -----------------------

        Args:
            df: A dataframe

        Returns:
            df with columns ['mb_artist_credit_mbids', 'user_name']
    """
    df = df.select(col('mb_artist_credit_mbids'),
                   col('user_name')) \
           .where(func.size('mb_artist_credit_mbids') > 1) \
           .withColumn('mb_artist_credit_mbids', func.explode('mb_artist_credit_mbids')) \
           .select(col('mb_artist_credit_mbids').alias('mbids'),
                   col('user_name'))

    res_df = convert_string_datatype_to_array(df).select(col('mb_artist_credit_mbids'),
                                                         col('user_name'))

    return res_df


def append_artists_from_collaborations(top_artist_df):
    """ Append artist info rows (artist_mbid, artist_credit_id, etc) of artists that belong
        to an artist collaboration to top artist dataframe.

        Example:
            Before:
            ----------------------------------------
            | artist_credit_id| artist_credit_mbids|
            ----------------------------------------
            |                1|              [a, b]|
            ----------------------------------------

            After:
            ----------------------------------------
            | artist_credit_id| artist_credit_mbids|
            ----------------------------------------
            |                1|              [a, b]|
            ----------------------------------------
            |                2|                 [a]|
            ----------------------------------------
            |                3|                 [b]|
            ----------------------------------------
    """
    df = explode_artist_collaborations(top_artist_df)

    msid_mbid_mapping_df = utils.read_files_from_HDFS(path.MBID_MSID_MAPPING)

    # get artist credit id corresponding to artist mbid.
    res_df = msid_mbid_mapping_df.join(df, 'mb_artist_credit_mbids', 'inner') \
                                 .select(col('mb_artist_credit_mbids'),
                                         col('mb_artist_credit_id').alias('top_artist_credit_id'),
                                         col('msb_artist_credit_name_matchable').alias('top_artist_name'),
                                         col('user_name')) \
                                 .distinct()

    # append the exploded df to top artist df
    top_artist_df = top_artist_df.union(res_df) \
                                 .select('top_artist_credit_id',
                                         'top_artist_name',
                                         'user_name') \
                                 .distinct()
    # using distinct for extra care since pyspark union ~ SQL union all.

    return top_artist_df


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
                                      'mb_artist_credit_mbids',
                                      'user_name') \
                              .groupBy('mb_artist_credit_id',
                                       'msb_artist_credit_name_matchable',
                                       'mb_artist_credit_mbids',
                                       'user_name') \
                              .agg(func.count('mb_artist_credit_id').alias('total_count'))

    window = Window.partitionBy('user_name').orderBy(col('total_count').desc())

    top_artist_df = df.withColumn('rank', row_number().over(window)) \
                      .where(col('rank') <= top_artist_limit) \
                      .select(col('mb_artist_credit_mbids'),
                              col('mb_artist_credit_id').alias('top_artist_credit_id'),
                              col('msb_artist_credit_name_matchable').alias('top_artist_name'),
                              col('user_name'))

    top_artist_df = append_artists_from_collaborations(top_artist_df)

    if users:
        top_artist_given_users_df = top_artist_df.select('top_artist_credit_id',
                                                         'top_artist_name',
                                                         'user_name') \
                                                 .where(top_artist_df.user_name.isin(users))

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
                              col('user_name').alias('user'))

    condition = [
        similar_artist_df.similar_artist_credit_id == df.artist_credit_id,
        similar_artist_df.user_name == df.user
    ]

    res_df = similar_artist_df.join(df, condition, 'left') \
                              .select('top_artist_credit_id',
                                      'top_artist_name',
                                      'similar_artist_credit_id',
                                      'similar_artist_name',
                                      'user_name') \
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

    similar_artist_df_html = df.withColumn('rank', row_number().over(window)) \
                               .where(col('rank') <= similar_artist_limit)\
                               .select('top_artist_credit_id',
                                       'top_artist_name',
                                       'similar_artist_credit_id',
                                       'similar_artist_name',
                                       'user_name')

    similar_artist_df_html = filter_top_artists_from_similar_artists(similar_artist_df_html, top_artist_df)

    # Two or more artists can have same similar artist(s) leading to non-unique recordings
    # therefore we have filtered the distinct similar artists.
    similar_artist_df = similar_artist_df_html.select('similar_artist_credit_id',
                                                      'similar_artist_name',
                                                      'user_name') \
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
    df = mapped_listens_subset.select(col('mb_recording_mbid').alias('recording_mbid'),
                                      col('user_name').alias('user')) \
                              .distinct()

    condition = [
        candidate_set_df.mb_recording_mbid == df.recording_mbid,
        candidate_set_df.user_name == df.user
    ]

    filtered_df = candidate_set_df.join(df, condition, 'left') \
                                  .select('*') \
                                  .where(col('recording_mbid').isNull() & col('user').isNull())

    return filtered_df.drop('recording_mbid', 'user')


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
        top_artist_df.top_artist_credit_id == recordings_df.mb_artist_credit_id
    ]

    df = top_artist_df.join(recordings_df, condition, 'inner')

    joined_df = df.join(users_df, 'user_name', 'inner') \
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

    top_artist_candidate_set_df_html = filter_last_x_days_recordings(joined_df, mapped_listens_subset)

    top_artist_candidate_set_df = top_artist_candidate_set_df_html.select('recording_id', 'user_id', 'user_name')

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
        similar_artist_df.similar_artist_credit_id == recordings_df.mb_artist_credit_id
    ]

    df = similar_artist_df.join(recordings_df, condition, 'inner')

    joined_df = df.join(users_df, 'user_name', 'inner') \
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

    similar_artist_candidate_set_df_html = filter_last_x_days_recordings(joined_df, mapped_listens_subset)

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

        if row.user_name not in user_data:
            user_data[row.user_name] = defaultdict(list)

        data = (
            row.top_artist_name,
            row.top_artist_credit_id
        )
        user_data[row.user_name]['top_artist'].append(data)

    for row in similar_artist_df_html.collect():
        data = (
            row.top_artist_name,
            row.top_artist_credit_id,
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

    from_date, to_date = get_dates_to_generate_candidate_sets(mapped_listens_df, recommendation_generation_window)

    logger.info('Fetching listens to get top artists...')
    mapped_listens_subset = get_listens_to_fetch_top_artists(mapped_listens_df, from_date, to_date)

    logger.info('Fetching top artists...')
    top_artist_df = get_top_artists(mapped_listens_subset, top_artist_limit, users)

    logger.info('Preparing top artists candidate set...')
    top_artist_candidate_set_df, top_artist_candidate_set_df_html = get_top_artist_candidate_set(top_artist_df, recordings_df,
                                                                                                 users_df, mapped_listens_subset)

    logger.info('Fetching similar artists...')
    similar_artist_df, similar_artist_df_html = get_similar_artists(top_artist_df, artist_relation_df, similar_artist_limit)

    logger.info('Preparing similar artists candidate set...')
    similar_artist_candidate_set_df, similar_artist_candidate_set_df_html = get_similar_artist_candidate_set(
                                                                                similar_artist_df,
                                                                                recordings_df,
                                                                                users_df,
                                                                                mapped_listens_subset)

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
