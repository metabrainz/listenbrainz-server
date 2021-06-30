import logging

from pyspark.sql.dataframe import DataFrame
from pyspark.ml.stat import Correlation
from pyspark.sql.functions import struct, collect_list

import listenbrainz_spark
from listenbrainz_spark import SparkSessionNotInitializedException, utils, path
from listenbrainz_spark.exceptions import PathNotFoundException, FileNotFetchedException
from listenbrainz_spark.user_similarity.utils import get_vectors_df, threshold_similar_users, create_messages

logger = logging.getLogger(__name__)


def main(max_num_users: int):

    logger.info('Start generating similar user matrix')
    try:
        listenbrainz_spark.init_spark_session('User Similarity')
    except SparkSessionNotInitializedException as err:
        logger.error(str(err), exc_info=True)
        raise

    try:
        playcounts_df = utils.read_files_from_HDFS(path.USER_SIMILARITY_PLAYCOUNTS_DATAFRAME)
        users_df = utils.read_files_from_HDFS(path.USER_SIMILARITY_USERS_DATAFRAME)
    except PathNotFoundException as err:
        logger.error(str(err), exc_info=True)
        raise
    except FileNotFetchedException as err:
        logger.error(str(err), exc_info=True)
        raise

    vectors_df = get_vectors_df(playcounts_df, "recording_id", "user_id", "count")
    similarity_matrix = Correlation.corr(vectors_df, 'vector', 'pearson').first()['pearson(vector)'].toArray()
    similar_users = threshold_similar_users(similarity_matrix, max_num_users)

    # Due to an unresolved bug in Spark (https://issues.apache.org/jira/browse/SPARK-10925), we cannot join twice on
    # the same dataframe. Hence, we create a modified dataframe with the columns renamed.
    other_users_df = users_df\
        .withColumnRenamed('user_id', 'other_user_id')\
        .withColumnRenamed('user_name', 'other_user_name')

    similar_users_df = listenbrainz_spark.session.createDataFrame(similar_users, ['user_id', 'other_user_id',
        'similarity', 'global_similarity'])\
        .join(users_df, 'user_id', 'inner')\
        .join(other_users_df, 'other_user_id', 'inner')\
        .select('user_name', struct('other_user_name', 'similarity', 'global_similarity').alias('similar_user'))\
        .groupBy('user_name')\
        .agg(collect_list('similar_user').alias('similar_users'))

    logger.info('Finishing generating similar user matrix')

    return create_messages(similar_users_df)
