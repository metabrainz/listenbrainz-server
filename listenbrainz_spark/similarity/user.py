import logging
from collections import defaultdict
from operator import itemgetter
import math
from typing import Iterable
from pyspark.sql import DataFrame, Window

from pyspark.mllib.linalg.distributed import CoordinateMatrix, MatrixEntry, RowMatrix
from pyspark.sql.functions import struct, collect_list, col, row_number

from listenbrainz_spark.path import USER_SIMILARITY_PLAYCOUNTS_DATAFRAME, USER_SIMILARITY_USERS_DATAFRAME
from listenbrainz_spark.utils import read_files_from_HDFS

logger = logging.getLogger(__name__)


def create_messages(similar_users_df: DataFrame) -> Iterable[dict]:
    """
    Iterate over the similar_users_df to create a message of the following format for sending using the request consumer

        {
            "type": "similar_users",
            "data": [
                "user_1": {
                    "user_2": 0.5,
                    "user_3": 0.7,
                },
                "user_2": {
                    "user_1": 0.5
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
        "type": "similar_users",
        "data": message
    }


def process_similarities(matrix: CoordinateMatrix, max_num_users: int) -> DataFrame:
    """ Post process the similarity matrix.

        Convert the coordinate matrix of column similarities to a DataFrame of top N similar columns.
    """
    df = matrix.entries.toDF()
    filtered_df = df.filter(col("value") > 0)

    # column similarities only contain pairs where i < j, add the symmetrically reverse pairs
    forward = filtered_df.select(
        col("i").alias("spark_user_id"),
        col("j").alias("other_spark_user_id"),
        col("value").alias("similarity")
    )
    backward = filtered_df.select(
        col("j").alias("spark_user_id"),
        col("i").alias("other_spark_user_id"),
        col("value").alias("similarity")
    )
    combined_df = forward.union(backward)

    window = Window.partitionBy("spark_user_id").orderBy(col("similarity").desc())
    ranked_df = combined_df.withColumn("rank", row_number().over(window))

    return ranked_df.filter(col("rank") <= max_num_users).drop("rank")


def get_row_matrix(playcounts_df) -> RowMatrix:
    """
    Each row of playcounts_df has the following columns: recording_id, spark_user_id and a play count denoting how many times
    a user has played that recording. However, the correlation matrix requires a dataframe having a column of user
    vectors. Spark has various representations built-in for storing sparse matrices. Of these, two are Coordinate
    Matrix and Row Matrix. A coordinate matrix stores the matrix as tuples of (i, j, x) where matrix[i, j] = x.
    A Row Matrix stores it as tuples of row index and vectors.

    Our playcounts_df is similar in structure to a coordinate matrix. We begin with mapping each row of the
    playcounts_df to a MatrixEntry and then create a matrix of these entries. The recording_ids are rows, user_ids are
    columns and the playcounts are the values in the matrix. We convert the coordinate matrix to a row matrix
    form to calculate column similarities.
    """
    tuple_mapped_rdd = playcounts_df.rdd.map(lambda x: MatrixEntry(x["recording_id"], x["spark_user_id"], x["playcount"]))
    coordinate_matrix = CoordinateMatrix(tuple_mapped_rdd)
    return coordinate_matrix.toRowMatrix()


def get_similar_users_df(max_num_users: int):
    logger.info("Start generating similar user matrix")

    playcounts_df = read_files_from_HDFS(USER_SIMILARITY_PLAYCOUNTS_DATAFRAME)
    users_df = read_files_from_HDFS(USER_SIMILARITY_USERS_DATAFRAME)

    row_matrix = get_row_matrix(playcounts_df)
    similarity_matrix = row_matrix.columnSimilarities()
    similarities_df = process_similarities(similarity_matrix, max_num_users)

    # Due to an unresolved bug in Spark (https://issues.apache.org/jira/browse/SPARK-10925), we cannot join twice on
    # the same dataframe. Hence, we create a modified dataframe with the columns renamed.
    other_users_df = users_df\
        .withColumnRenamed("spark_user_id", "other_spark_user_id")\
        .withColumnRenamed("user_id", "other_user_id")

    similar_users_df = similarities_df \
        .join(users_df, "spark_user_id", "inner") \
        .join(other_users_df, "other_spark_user_id", "inner") \
        .select("user_id", struct("other_user_id", "similarity").alias("similar_user")) \
        .groupBy("user_id") \
        .agg(collect_list("similar_user").alias("similar_users"))

    logger.info("Finishing generating similar user matrix")

    return similar_users_df


def main(max_num_users: int):
    similar_users_df = get_similar_users_df(max_num_users)
    return create_messages(similar_users_df)
