import math
from operator import itemgetter
from typing import List, Tuple

from numpy import ndarray
from pyspark.mllib.linalg.distributed import MatrixEntry, CoordinateMatrix
from pyspark.sql import DataFrame

import listenbrainz_spark


def get_vectors_df(playcounts_df: DataFrame, listen_id_col: str, user_id_col: str, count_id_col: str):
    """
    Transform the input dataframe into a vectors dataframe which can be given as input to Correlation matrix functions

    Args:
        playcounts_df: the input dataframe whose each represents an entry in correlation matrix
        listen_id_col: the name column to use as row index (eg: recording_id/artist_id)
        user_id_col: the name of column to use as column index (eg: user_id)
        count_id_col: the name to column to use as values in matrix (eg: count)

    Each row of playcounts_df has the following columns: recording_id/artist_id, user_id and a play count denoting
    how many times a user has played that recording/artist. However, the correlation matrix requires a dataframe
    having a column of user vectors. Spark has various representations built-in for storing sparse matrices.
    Of these, two are Coordinate Matrix and Indexed Row Matrix. A coordinate matrix stores the matrix as
    tuples of (i, j, x) where matrix[i, j] = x. An Indexed Row Matrix stores it as tuples of row index and vectors.

    Our playcounts_df is similar in structure to a coordinate matrix. We begin with mapping each row of the
    playcounts_df to a MatrixEntry and then create a matrix of these entries. The recording_ids are rows, user_ids are
    columns and the playcounts are the values in the matrix. We convert the coordinate matrix to indexed row matrix
    form. Spark ML and MLlib have different representations of vectors, hence we need to manually convert between the
    two. Finally, we take the rows and create a dataframe from them.
    """
    tuple_mapped_rdd = playcounts_df.rdd.map(lambda x: MatrixEntry(x[listen_id_col], x[user_id_col], x[count_id_col]))
    coordinate_matrix = CoordinateMatrix(tuple_mapped_rdd)
    indexed_row_matrix = coordinate_matrix.toIndexedRowMatrix()
    vectors_mapped_rdd = indexed_row_matrix.rows.map(lambda r: (r.index, r.vector.asML()))
    return listenbrainz_spark.session.createDataFrame(vectors_mapped_rdd, ['index', 'vector'])


def threshold_similar_users(matrix: ndarray, max_num_users: int) -> List[Tuple[int, int, float, float]]:
    """ Determine the minimum and maximum values in the matrix, scale
        the result to the range of [0.0 - 1.0] and limit each user to max of
        max_num_users other users.
    """
    rows, cols = matrix.shape
    similar_users = list()

    # Calculate the global similarity scale
    global_max_similarity = None
    global_min_similarity = None
    for x in range(rows):
        row = []

        # Calculate the minimum and maximum values for a user
        for y in range(cols):

            # Spark sometimes returns nan values and the way to get rid of them is to
            # cast to a float and discard values that are non a number
            value = float(matrix[x, y])
            if x == y or math.isnan(value):
                continue

            if global_max_similarity is None:
                global_max_similarity = value
                global_min_similarity = value

            global_max_similarity = max(value, global_max_similarity)
            global_min_similarity = min(value, global_min_similarity)

    global_similarity_range = global_max_similarity - global_min_similarity

    for x in range(rows):
        row = []
        max_similarity = None
        min_similarity = None

        # Calculate the minimum and maximum values for a user
        for y in range(cols):

            # Spark sometimes returns nan values and the way to get rid of them is to
            # cast to a float and discard values that are non a number
            value = float(matrix[x, y])
            if x == y or math.isnan(value):
                continue

            if max_similarity is None:
                max_similarity = value
                min_similarity = value

            max_similarity = max(value, max_similarity)
            min_similarity = min(value, min_similarity)

        if max_similarity is not None and min_similarity is not None:
            # Now apply the scale factor and flatten the results for a user
            similarity_range = max_similarity - min_similarity
            for y in range(cols):
                value = float(matrix[x, y])
                if x == y or math.isnan(value):
                    continue

                row.append((x,
                            y,
                            (value - min_similarity) / similarity_range,
                            (value - global_min_similarity) / global_similarity_range))

            similar_users.extend(sorted(row, key = itemgetter(2), reverse = True)[:max_num_users])

    return similar_users


def create_messages(similar_users_df: DataFrame) -> dict:
    """
    Iterate over the similar_users_df to create a message of the following format for sending using the request consumer

        {
            'type': 'similar_users',
            'data': [
                'user_1': {
                    'user_2': (0.5, 0.2),
                    'user_3': (0.7, 0.3),
                },
                'user_2': {
                    'user_1': (0.5, 0.2)
                }
                ...
            ]
        }
    """
    itr = similar_users_df.toLocalIterator()
    message = {}
    for row in itr:
        message[row.user_name] = {
            user.other_user_name: (user.similarity, user.global_similarity) for user in row.similar_users
        }
    yield {
        'type': 'similar_users',
        'data': message
    }
