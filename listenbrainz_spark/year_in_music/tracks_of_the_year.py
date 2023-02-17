from datetime import datetime, date, time

from more_itertools import chunked

from listenbrainz_spark.stats import run_query
from listenbrainz_spark.utils import get_listens_from_dump


ENTRIES_PER_MESSAGE = 100000

def calculate_tracks_of_the_year(year):
    """ Calculate all tracks a user has listened to in the given year. """
    get_listens_from_dump().createOrReplaceTempView("listens")

    start = datetime.combine(date(year, 1, 1), time.min)
    end = datetime.combine(date(year, 12, 31), time.max)

    query = f"""
        SELECT user_id
             , recording_name
             , recording_mbid
             , artist_name
             , artist_credit_mbids
             , count(*) AS listen_count
          FROM listens
         WHERE listened_at >= to_timestamp('{start}')
           AND listened_at <= to_timestamp('{end}')
           AND recording_mbid IS NOT NULL
      GROUP BY user_id
             , recording_name
             , recording_mbid
             , artist_name
             , artist_credit_mbids
    """
    data = run_query(query).toLocalIterator()

    yield {
        "type": "year_in_music_tracks_of_the_year_start",
        "year": year,
    }

    for entries in chunked(data, ENTRIES_PER_MESSAGE):
        yield {
            "type": "year_in_music_tracks_of_the_year_data",
            "year": year,
            "data": [e.asDict() for e in entries]
        }

    yield {
        "type": "year_in_music_tracks_of_the_year_end",
        "year": year,
    }
