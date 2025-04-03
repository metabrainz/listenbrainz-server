import logging
from operator import itemgetter
import math
from typing import List, Tuple
from pyspark.sql.dataframe import DataFrame
from numpy import ndarray

from pyspark.mllib.linalg.distributed import CoordinateMatrix, MatrixEntry
from pyspark.ml.stat import Correlation
from pyspark.sql.functions import struct, collect_list

import listenbrainz_spark
from listenbrainz_spark import SparkSessionNotInitializedException, utils, path
from listenbrainz_spark.exceptions import PathNotFoundException, FileNotFetchedException


logger = logging.getLogger(__name__)


def create_messages(similar_users_df: DataFrame) -> dict:
    """
    Iterate over the similar_users_df to create a message of the following format for sending using the request consumer

        {
            'type': 'similar_users',
            'data': [
                'user_1': {
                    'user_2': 0.5,
                    'user_3': 0.7,
                },
                'user_2': {
                    'user_1': 0.5
                }
                ...
            ]
        }
    """
    itr = similar_users_df.toLocalIterator()
    message = {}
    for row in itr:
        message[row.user_id] = {
            user.other_user_id: user.similarity
            for user in row.similar_users
        }
    yield {
        'type': 'similar_users',
        'data': message
    }


def threshold_similar_users(matrix: ndarray, max_num_users: int) -> List[Tuple[int, int, float]]:
    """ Determine the minimum and maximum values in the matriz, scale
        the result to the range of [0.0 - 1.0] and limit each user to max of
        max_num_users other users.
    """
    rows, cols = matrix.shape
    similar_users = list()

    for x in range(rows):
        row = []
        for y in range(cols):
            value = float(matrix[x, y])
            if x == y or math.isnan(value) or value < 0:
                continue
            row.append((x, y, value))
        similar_users.extend(sorted(row, key=itemgetter(2), reverse=True)[:max_num_users])

    return similar_users


def get_vectors_df(playcounts_df):
    """
    Each row of playcounts_df has the following columns: recording_id, spark_user_id and a play count denoting how many times
    a user has played that recording. However, the correlation matrix requires a dataframe having a column of user
    vectors. Spark has various representations built-in for storing sparse matrices. Of these, two are Coordinate
    Matrix and Indexed Row Matrix. A coordinate matrix stores the matrix as tuples of (i, j, x) where matrix[i, j] = x.
    An Indexed Row Matrix stores it as tuples of row index and vectors.

    Our playcounts_df is similar in structure to a coordinate matrix. We begin with mapping each row of the
    playcounts_df to a MatrixEntry and then create a matrix of these entries. The recording_ids are rows, user_ids are
    columns and the playcounts are the values in the matrix. We convert the coordinate matrix to indexed row matrix
    form. Spark ML and MLlib have different representations of vectors, hence we need to manually convert between the
    two. Finally, we take the rows and create a dataframe from them.
    """
    tuple_mapped_rdd = playcounts_df.rdd.map(lambda x: MatrixEntry(x["recording_id"], x["spark_user_id"], x["playcount"]))
    coordinate_matrix = CoordinateMatrix(tuple_mapped_rdd)
    indexed_row_matrix = coordinate_matrix.toIndexedRowMatrix()
    vectors_mapped_rdd = indexed_row_matrix.rows.map(lambda r: (r.index, r.vector.asML()))
    return listenbrainz_spark.session.createDataFrame(vectors_mapped_rdd, ['index', 'vector'])


def get_similar_users_df(max_num_users: int):
    logger.info('Start generating similar user matrix')

    try:
        playcounts_df = utils.read_files_from_HDFS(path.USER_SIMILARITY_PLAYCOUNTS_DATAFRAME)
        users_df = utils.read_files_from_HDFS(path.USER_SIMILARITY_USERS_DATAFRAME)
    except PathNotFoundException as err:
        logger.error(str(err), exc_info=True)
        raise
    except FileNotFetchedException as err:
        logger.error(str(err), exc_info=True)
        raise

    vectors_df = get_vectors_df(playcounts_df)

    similarity_matrix = Correlation.corr(vectors_df, 'vector', 'pearson').first()['pearson(vector)'].toArray()
    similar_users = threshold_similar_users(similarity_matrix, max_num_users)

    # Due to an unresolved bug in Spark (https://issues.apache.org/jira/browse/SPARK-10925), we cannot join twice on
    # the same dataframe. Hence, we create a modified dataframe with the columns renamed.
    other_users_df = users_df\
        .withColumnRenamed('spark_user_id', 'other_spark_user_id')\
        .withColumnRenamed('user_id', 'other_user_id')

    similar_users_df = listenbrainz_spark.session.createDataFrame(
        similar_users,
        ['spark_user_id', 'other_spark_user_id', 'similarity']
    )\
        .join(users_df, 'spark_user_id', 'inner')\
        .join(other_users_df, 'other_spark_user_id', 'inner')\
        .select('user_id', struct('other_user_id', 'similarity').alias('similar_user'))\
        .groupBy('user_id')\
        .agg(collect_list('similar_user').alias('similar_users'))

    logger.info('Finishing generating similar user matrix')

    return similar_users_df


def main(max_num_users: int):
    similar_users_df = get_similar_users_df(max_num_users)
    return create_messages(similar_users_df)
