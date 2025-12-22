from more_itertools import chunked

from listenbrainz_spark.path import RECORDING_RECORDING_GENRE_DATAFRAME
from listenbrainz_spark.postgres.tag import create_genre_cache
from listenbrainz_spark.stats import run_query
from listenbrainz_spark.utils import read_files_from_HDFS
from listenbrainz_spark.year_in_music.utils import setup_listens_for_year

TOP_GENRES_PER_MONTH = 10
USERS_PER_MESSAGE = 1000


def get_genre_activity(year):
    """ Get genre activity by month for Year in Music """
    setup_listens_for_year(year)
    create_genre_cache()
    
    genres_df = read_files_from_HDFS(RECORDING_RECORDING_GENRE_DATAFRAME)
    genres_df.createOrReplaceTempView("genres")

    data = run_query(_get_genre_activity_query()).collect()
    for entries in chunked(data, USERS_PER_MESSAGE):
        yield {
            "type": "year_in_music_genre_activity",
            "year": year,
            "data": [e.asDict(recursive=True) for e in entries]
        }


def _get_genre_activity_query():
    return f"""
        WITH genre_listens AS (
            SELECT l.user_id,
                   g.genre,
                   HOUR(l.listened_at) AS hour,
                   COUNT(*) AS listen_count
              FROM listens_of_year l
              LEFT JOIN genres g ON l.recording_mbid = g.recording_mbid
             WHERE g.genre IS NOT NULL
          GROUP BY l.user_id, g.genre, MONTH(l.listened_at)
        ),
        top_genres AS (
            SELECT user_id,
                   genre,
                   hour,
                   listen_count,
                   ROW_NUMBER() OVER (
                       PARTITION BY user_id, hour
                       ORDER BY listen_count DESC
                   ) AS rank
              FROM genre_listens
        ),
        filtered_genres AS (
            SELECT user_id, genre, hour, listen_count
              FROM top_genres
             WHERE rank <= {TOP_GENRES_PER_MONTH}
        )
        SELECT user_id,
               SORT_ARRAY(
                   COLLECT_LIST(
                       STRUCT(genre, hour, listen_count)
                   )
               ) AS data
          FROM filtered_genres
      GROUP BY user_id
    """
