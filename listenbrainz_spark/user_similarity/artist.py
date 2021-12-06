import logging

from pyspark.ml.stat import Correlation

import listenbrainz_spark
from listenbrainz_spark.recommendations.dataframe_utils import get_dates_to_train_data
from listenbrainz_spark.utils import get_listens_from_new_dump
from listenbrainz_spark.user_similarity.utils import get_vectors_df, threshold_similar_users, create_messages


logger = logging.getLogger(__name__)


def main(train_model_window: int, minimum_listens_threshold: int, max_num_users: int):
    listenbrainz_spark.init_spark_session("Create artist dataframes")
    to_date, from_date = get_dates_to_train_data(train_model_window)

    listens_df = get_listens_from_new_dump(from_date, to_date)
    logger.info("Listen count from %s to %s: %d", from_date, to_date, listens_df.count())
    listens_df.createOrReplaceTempView("listens_artist_similarity")

    listens_query = f"""
        WITH mapped_listens AS (
            SELECT user_name
                 , artist_credit_mbids
              FROM listens_artist_similarity
             WHERE artist_credit_mbids IS NOT NULL
        ), users_above_threshold AS (
            SELECT user_name 
              FROM mapped_listens
          GROUP BY user_name 
            HAVING count(*) > {minimum_listens_threshold}            
        ), exploded_listens AS (
            SELECT user_name
                 , explode(artist_credit_mbids) as artist_mbid
              FROM mapped_listens
             WHERE user_name IN (SELECT * FROM users_above_threshold)
        )
        SELECT artist_mbid
             , user_name
             , count(artist_mbid) AS listen_count
             , dense_rank() OVER (ORDER BY artist_mbid) AS artist_id
             , dense_rank() OVER (ORDER BY user_name) AS user_id
          FROM exploded_listens
      GROUP BY user_name
             , artist_mbid
    """

    results_df = listenbrainz_spark.sql_context.sql(listens_query)
    results_df.createOrReplaceTempView("listens_artist_similarity")

    vectors_df = get_vectors_df(results_df, "artist_id", "user_id", "listen_count")
    similarity_matrix = Correlation.corr(vectors_df, "vector", "pearson").first()["pearson(vector)"].toArray()
    similar_users_thresholded = threshold_similar_users(similarity_matrix, max_num_users)

    similar_users_df = listenbrainz_spark.session.createDataFrame(
        similar_users_thresholded,
        ["user_id", "other_user_id", "similarity", "global_similarity"]
    )
    similar_users_df.createOrReplaceTempView("artist_similar_users")
    similar_users_query = """
        WITH users AS (
              SELECT DISTINCT 
                     user_name
                   , user_id 
                FROM listens_artist_similarity
        )
        SELECT users.user_name AS user_name
             , collect_list(
                    struct(others.user_name AS other_user_name, similarity, global_similarity)
               ) AS similar_users 
          FROM artist_similar_users
          JOIN users
            ON users.user_id = artist_similar_users.user_id
          JOIN users AS others
            ON others.user_id = artist_similar_users.other_user_id
      GROUP BY users.user_name
    """
    similar_users_results = listenbrainz_spark.sql_context.sql(similar_users_query)
    return create_messages(similar_users_results, "artist")
