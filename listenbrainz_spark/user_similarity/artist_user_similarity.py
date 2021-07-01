import logging

from pyspark.ml.stat import Correlation
from pyspark.sql import DataFrame

import listenbrainz_spark
from listenbrainz_spark.path import LISTENBRAINZ_DATA_DIRECTORY, MBID_MSID_MAPPING
from listenbrainz_spark.recommendations.dataframe_utils import get_dates_to_train_data, \
    get_listens_for_training_model_window, get_mapped_artist_and_recording_mbids
from listenbrainz_spark.user_similarity.utils import get_vectors_df, threshold_similar_users, create_messages
from listenbrainz_spark.utils import read_files_from_HDFS
from listenbrainz_spark.utils.mapping import get_unique_rows_from_mapping

logger = logging.getLogger(__name__)


def main(train_model_window: int, minimum_listens_threshold: int, max_num_users: int):
    listenbrainz_spark.init_spark_session('Create artist dataframes')
    to_date, from_date = get_dates_to_train_data(train_model_window)

    partial_listens_df = get_listens_for_training_model_window(to_date, from_date, LISTENBRAINZ_DATA_DIRECTORY)
    logger.info('Listen count from %s to %s: %d', from_date, to_date, partial_listens_df.count())

    logger.info('Loading mapping from HDFS...')
    msid_mbid_mapping_df = get_unique_rows_from_mapping(read_files_from_HDFS(MBID_MSID_MAPPING))
    logger.info('Number of distinct rows in the mapping: %d', msid_mbid_mapping_df.count())

    logger.info('Mapping listens...')
    mapped_listens_df: DataFrame = get_mapped_artist_and_recording_mbids(partial_listens_df, msid_mbid_mapping_df)
    mapped_listens_df.createOrReplaceTempView('mapped_listens_artist_similarity')

    listens_query = """
        WITH listens_intermediate (
            SELECT user_name, explode(mb_artist_credit_mbids) as artist_mbid
            FROM mapped_listens_artist_similarity
            )
        SELECT artist_mbid, 
               user_name,
               count(artist_mbid) as listen_count,
               dense_rank() over(order by artist_mbid) as artist_id,
               dense_rank() over(order by user_name) as user_id
        FROM listens_intermediate
        WHERE user_name IN (
            SELECT user_name 
            FROM mapped_listens_artist_similarity
            GROUP BY user_name 
            HAVING count(*) > {threshold}
        ) 
        GROUP BY user_name, artist_mbid
    """.format(threshold=minimum_listens_threshold)

    results_df: DataFrame = listenbrainz_spark.sql_context.sql(listens_query)
    results_df.createOrReplaceTempView('listens_artist_similarity')

    vectors_df = get_vectors_df(results_df, "artist_id", "user_id", "listen_count")
    similarity_matrix = Correlation.corr(vectors_df, 'vector', 'pearson').first()['pearson(vector)'].toArray()
    similar_users_thresholded = threshold_similar_users(similarity_matrix, max_num_users)

    similar_users_df: DataFrame = listenbrainz_spark.session.createDataFrame(
        similar_users_thresholded,
        ['user_id', 'other_user_id', 'similarity', 'global_similarity']
    )
    similar_users_df.createOrReplaceTempView('artist_similar_users')
    similar_users_query = """
        SELECT  users.user_name AS user_name,
                collect_list(
                    struct(others.user_name AS other_user_name, similarity, global_similarity)
                ) AS similar_users 
        FROM artist_similar_users
        JOIN listens_artist_similarity AS users
          ON users.user_id = artist_similar_users.user_id
        JOIN listens_artist_similarity AS others
          ON others.user_id = artist_similar_users.other_user_id
        GROUP BY users.user_name
    """
    similar_users_results = listenbrainz_spark.sql_context.sql(similar_users_query)
    return create_messages(similar_users_results)




