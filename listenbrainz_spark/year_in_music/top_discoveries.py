from datetime import datetime, date, time

from more_itertools import chunked

from listenbrainz_spark.constants import LAST_FM_FOUNDING_YEAR
from listenbrainz_spark.path import RECORDING_ARTIST_DATAFRAME
from listenbrainz_spark.stats import run_query
from listenbrainz_spark.listens.data import get_listens_from_dump

USERS_PER_MESSAGE = 250
MAX_ARTIST_OCCURRENCE = 2
MAX_TRACKS_PER_PLAYLIST = 50


def generate_top_discoveries(year):
    create_tracks_of_the_year(year)

    query = f"""
        WITH intermediate AS (
            SELECT user_id
                 , t.recording_mbid
                 , score
                 , explode(ra.artist_mbids) AS artist_mbid
              FROM tracks_of_year t
              JOIN parquet.`{RECORDING_ARTIST_DATAFRAME}` ra
                ON ra.recording_mbid = t.recording_mbid
        ), artist_ranking AS (
            SELECT user_id
                 , recording_mbid
                 , score
                 , rank() OVER (PARTITION BY user_id, artist_mbid ORDER BY score DESC) AS per_artist_position
              FROM intermediate
        ), artist_limiting AS (
            -- need a group by to eliminate duplicate recording mbids in a playlist
            --, can happen when there are multiple artists for a recording
            SELECT user_id
                 , recording_mbid
                 , rank() over (PARTITION BY user_id ORDER BY RANDOM()) AS ranking
              FROM artist_ranking
             WHERE per_artist_position <= {MAX_ARTIST_OCCURRENCE}
          GROUP BY user_id
                 , recording_mbid
        )
            SELECT user_id
                 , collect_list(recording_mbid) AS recordings
              FROM artist_limiting
             WHERE ranking <= {MAX_TRACKS_PER_PLAYLIST}
          GROUP BY user_id
    """

    data = run_query(query).toLocalIterator()

    for entry in chunked(data, USERS_PER_MESSAGE):
        playlists = [row.asDict(recursive=True) for row in entry]
        yield {
            "slug": "top-discoveries",
            "year": year,
            "data": playlists,
            "type": "year_in_music_playlists"
        }

    yield {
        "slug": "top-discoveries",
        "year": year,
        "type": "year_in_music_playlists_end"
    }


def create_tracks_of_the_year(year):
    start = datetime(LAST_FM_FOUNDING_YEAR, 1, 1)
    end = datetime.combine(date(year, 12, 31), time.max)
    listens = get_listens_from_dump(start, end)
    listens.createOrReplaceTempView("listens_for_tracks_of_year")
    query = f"""
            SELECT user_id
                 , recording_mbid
                 , count(*) AS score
              FROM listens_for_tracks_of_year
             WHERE recording_mbid IS NOT NULL
          GROUP BY user_id
                 , recording_mbid
            HAVING date_part('YEAR', min(listened_at)) = {year}
               AND count(*) > 3
    """
    run_query(query).createOrReplaceTempView("tracks_of_year")
