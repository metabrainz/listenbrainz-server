from more_itertools import chunked

from listenbrainz_spark.path import RECORDING_RECORDING_GENRE_DATAFRAME, RECORDING_ARTIST_GENRE_DATAFRAME, \
    RECORDING_RELEASE_GROUP_GENRE_DATAFRAME
from listenbrainz_spark.postgres.tag import create_genre_cache
from listenbrainz_spark.stats import run_query
from listenbrainz_spark.year_in_music.utils import setup_listens_for_year

TOP_GENRES_COUNT = 25
USERS_PER_MESSAGE = 1000


def get_top_genres(year):
    """ Get top genres for the user for top genre and cover art shareable image """
    setup_listens_for_year(year)
    create_genre_cache()

    data = run_query(_get_query()).collect()
    for entries in chunked(data, USERS_PER_MESSAGE):
        yield {
            "type": "year_in_music_top_genres",
            "year": year,
            "data": [e.asDict(recursive=True) for e in entries]
        }


def _get_query():
    return f"""
        WITH all_genres AS (
            -- Recording genres (priority 1 - highest)
            SELECT l.user_id
                 , l.recording_mbid
                 , r.genre
                 , r.genre_count
                 , 1 AS priority
              FROM listens_of_year l
              JOIN parquet.`{RECORDING_RECORDING_GENRE_DATAFRAME}` r
                ON l.recording_mbid = r.recording_mbid
             WHERE l.recording_mbid IS NOT NULL
         UNION ALL
            -- Artist genres (priority 2)
            SELECT l.user_id
                 , l.recording_mbid
                 , a.genre
                 , a.genre_count
                 , 2 AS priority
              FROM listens_of_year l
              JOIN parquet.`{RECORDING_ARTIST_GENRE_DATAFRAME}` a
                ON l.recording_mbid = a.recording_mbid
             WHERE l.recording_mbid IS NOT NULL
         UNION ALL
            -- Release group genres (priority 3 - lowest)
            SELECT l.user_id
                 , l.recording_mbid
                 , rr.genre
                 , rr.genre_count
                 , 3 AS priority
              FROM listens_of_year l
              JOIN parquet.`{RECORDING_RELEASE_GROUP_GENRE_DATAFRAME}` rr
                ON l.recording_mbid = rr.recording_mbid
             WHERE l.recording_mbid IS NOT NULL
        ), prioritized AS (
            -- For each (user, recording, genre), keep only the highest priority source
            SELECT user_id
                 , recording_mbid
                 , genre
                 , genre_count
              FROM (
                  SELECT user_id
                       , recording_mbid
                       , genre
                       , genre_count
                       , ROW_NUMBER() OVER (
                           PARTITION BY user_id, recording_mbid, genre
                           ORDER BY priority ASC
                         ) AS rn
                    FROM all_genres
              ) ranked
             WHERE rn = 1
        ), together AS (
            -- Aggregate by user and genre, summing counts across all listens
            SELECT user_id
                 , genre
                 , SUM(genre_count) AS genre_count
              FROM prioritized
          GROUP BY user_id
                 , genre
        ), percentage AS (
           SELECT user_id
                , genre
                , genre_count
                , float((genre_count * 100.0) / SUM(genre_count) OVER(PARTITION BY user_id)) AS genre_count_percent
                , RANK() OVER (PARTITION BY user_id ORDER BY genre_count DESC) AS ranking
             FROM together
        )
           SELECT user_id
                , sort_array(
                    collect_list(
                      struct(
                        genre_count,
                        genre,
                        genre_count_percent
                      )
                    ),
                    false
                  ) AS data
             FROM percentage
            WHERE ranking <= {TOP_GENRES_COUNT}
         GROUP BY user_id
    """
