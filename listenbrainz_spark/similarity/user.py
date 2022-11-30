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
from listenbrainz_spark.stats import run_query

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
            user.other_user_id: (user.local_similarity, user.global_similarity)
            for user in row.similar_users
        }
    yield {
        'type': 'similar_users',
        'data': message
    }


def threshold_similar_users(similar_table: str, user_table: str, max_num_users: int) -> DataFrame:
    """ Determine the minimum and maximum values in the matriz, scale
        the result to the range of [0.0 - 1.0] and limit each user to max of
        max_num_users other users.
    """
    query = f"""
        WITH similar_users AS (
            SELECT i AS spark_user_id
                 , j AS other_spark_user_id
                 , value AS score
              FROM {similar_table}
        ), intermediate AS (
            SELECT u1.user_id AS user_id
                 , u2.user_id AS other_user_id
                 , su.score / (max(su.score) OVER w - min(su.score) OVER w) AS local_similarity
                 , su.score AS global_similarity
              FROM similar_users su
              JOIN {user_table} u1
                ON su.spark_user_id = u1.spark_user_id
              JOIN {user_table} u2
                ON su.other_spark_user_id = u2.spark_user_id
            WINDOW w AS (PARTITION BY u1.user_id ROWS BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING)
        ), threshold AS (
            SELECT user_id
                 , other_user_id
                 , local_similarity
                 , global_similarity
                 , row_number() OVER w AS rnum
              FROM intermediate
            WINDOW w AS (PARTITION BY user_id ORDER BY local_similarity DESC)
        )   SELECT user_id
                 , array_sort(
                        collect_list(
                            struct(
                                other_user_id
                              , local_similarity
                              , global_similarity
                            )
                        )
                     , (left, right) -> CASE
                                        WHEN left.local_similarity > right.local_similarity THEN -1
                                        WHEN left.local_similarity < right.local_similarity THEN  1
                                        ELSE 0
                                        END
                        -- sort in descending order of local similarity              
                   ) AS similar_users
              FROM threshold
             WHERE rnum <= {max_num_users}
          GROUP BY user_id
     """
    return run_query(query)


def get_users_matrix(playcounts_df):
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
    return indexed_row_matrix


def get_similar_users_df(max_num_users: int):
    logger.info('Start generating similar user matrix')
    listenbrainz_spark.init_spark_session('User Similarity')

    similar_table = "user_similarity_matrix"
    user_table = "user_similarity_users"

    playcounts_df = utils.read_files_from_HDFS(path.USER_SIMILARITY_PLAYCOUNTS_DATAFRAME)
    users_df = utils.read_files_from_HDFS(path.USER_SIMILARITY_USERS_DATAFRAME)
    users_df.createOrReplaceTempView(user_table)

    user_matrix = get_users_matrix(playcounts_df)
    similarity_matrix = user_matrix.columnSimilarities()
    similarity_matrix\
        .entries\
        .toDF()\
        .createOrReplaceTempView(similar_table)
    similar_users = threshold_similar_users(similar_table, user_table, max_num_users)

    logger.info('Finishing generating similar user matrix')

    return similar_users


def main(max_num_users: int):
    similar_users = get_similar_users_df(max_num_users)
    return create_messages(similar_users)
