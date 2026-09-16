from more_itertools import chunked

from listenbrainz_spark.path import RECORDING_ARTIST_DATAFRAME
from listenbrainz_spark.year_in_music.utils import setup_listens_for_year
from listenbrainz_spark.stats import run_query
from listenbrainz_spark.utils import read_files_from_HDFS

USERS_PER_MESSAGE = 500


def get_artist_evolution_activity(year):
    setup_listens_for_year(year)

    recording_df = read_files_from_HDFS(RECORDING_ARTIST_DATAFRAME)
    recording_df.createOrReplaceTempView("recording_artist")

    data = run_query(_get_artist_evolution_query()).collect()
    for entries in chunked(data, USERS_PER_MESSAGE):
        yield {
            "type": "year_in_music_artist_evolution_activity",
            "year": year,
            "data": [e.asDict(recursive=True) for e in entries]
        }


def _get_artist_evolution_query():
    return """
        WITH artist_listens AS (
            SELECT l.user_id
                 , month(l.listened_at) AS time_unit
                 , artist_element.artist_mbid AS artist_mbid
                 , artist_element.artist_credit_name AS artist_name
                 , COUNT(*) AS listen_count
              FROM listens_of_year l
              JOIN recording_artist ra ON l.recording_mbid = ra.recording_mbid
            LATERAL VIEW explode(ra.artists) AS artist_element
          GROUP BY l.user_id
                 , month(l.listened_at)
                 , artist_element.artist_mbid
                 , artist_element.artist_credit_name
        )
        SELECT user_id
             , sort_array(
                  collect_list(
                       struct(
                              time_unit
                            , artist_mbid
                            , artist_name
                            , listen_count
                       )
                   ), false
               ) AS data
          FROM artist_listens
      GROUP BY user_id
    """
