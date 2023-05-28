from more_itertools import chunked

from listenbrainz_spark.path import MLHD_PLUS_DATA_DIRECTORY
from listenbrainz_spark.stats import run_query


STATS_PER_MESSAGE = 10000


def generate(name, query):
    """ Execute the given query and generate statistics. """
    itr = run_query(query).toLocalIterator()

    for rows in chunked(itr, STATS_PER_MESSAGE):
        entries = []
        for row in rows:
            entry = row.asDict(recursive=True)
            entries.append(entry)

        yield {
            "type": name,
            "data": entries
        }


def main():
    """ Generate popularity data for MLHD data. """
    table = f"parquet.`{MLHD_PLUS_DATA_DIRECTORY}`"

    queries = {
        "mlhd_popularity_recording": f"""
            SELECT recording_mbid
                 , count(*) AS total_listen_count
                 , count(distinct user_id) AS total_user_count
              FROM {table}
          GROUP BY recording_mbid
        """,
        "mlhd_popularity_artist": f"""
            WITH exploded_data AS (
                SELECT explode(artist_credit_mbids) AS artist_mbid
                     , user_id
                  FROM {table}
            )   SELECT artist_mbid
                     , count(*) AS total_listen_count
                     , count(distinct user_id) AS total_user_count
                  FROM exploded_data
              GROUP BY artist_mbid   
        """,
        "mlhd_popularity_release": f"""
            SELECT release_mbid
                 , count(*) AS total_listen_count
                 , count(distinct user_id) AS total_user_count
              FROM {table}
          GROUP BY release_mbid
        """,
        "mlhd_popularity_top_recording": f"""
            WITH exploded_data AS (
                SELECT explode(artist_credit_mbids) AS artist_mbid
                     , recording_mbid
                     , user_id
                  FROM {table}
            )   SELECT artist_mbid
                     , recording_mbid
                     , count(*) AS total_listen_count
                     , count(distinct user_id) AS total_user_count
                  FROM exploded_data
              GROUP BY artist_mbid
                     , recording_mbid
        """,
        "mlhd_popularity_top_release": f"""
            WITH exploded_data AS (
                SELECT explode(artist_credit_mbids) AS artist_mbid
                     , release_mbid
                     , user_id
                  FROM {table}
            )   SELECT artist_mbid
                     , release_mbid
                     , count(*) AS total_listen_count
                     , count(distinct user_id) AS total_user_count
                  FROM exploded_data
              GROUP BY artist_mbid
                     , release_mbid
        """
    }

    for name, query in queries.items():
        yield generate(name, query)
