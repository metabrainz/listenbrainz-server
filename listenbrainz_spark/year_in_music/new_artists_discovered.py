from datetime import datetime, date, time

from listenbrainz_spark.constants import LAST_FM_FOUNDING_YEAR
from listenbrainz_spark.stats import run_query
from listenbrainz_spark.listens.data import get_listens_from_dump


def get_new_artists_discovered_count(year):
    """ Count the number of artists a user has listened to for the first time in the given year. """
    start = datetime.combine(date(LAST_FM_FOUNDING_YEAR, 1, 1), time.min)
    end = datetime.combine(date(year, 12, 31), time.max)
    get_listens_from_dump(start, end).createOrReplaceTempView("artists_discovery_listens")

    data = run_query(_get_new_discovered_artists_count(year)).collect()
    yield {
        "type": "year_in_music_new_artists_discovered_count",
        "year": year,
        "data": data[0]["new_artists_discovered_count"]
    }


def _get_new_discovered_artists_count(year):
    # for A ft. B, both A and B will be counted separately.
    return f"""
          WITH separate_artists AS (
            SELECT user_id
                 , listened_at
                 , explode(artist_credit_mbids) AS artist_mbid
              FROM artists_discovery_listens
         ), discovered_artists AS (
            SELECT user_id
                 , artist_mbid
              FROM separate_artists
          GROUP BY user_id
                 , artist_mbid
            HAVING date_part('YEAR', min(listened_at)) = {year}
        ), discovered_artists_count AS ( 
            SELECT user_id
                 , count(artist_mbid) AS artist_count
              FROM discovered_artists
          GROUP BY user_id     
        )      
            SELECT to_json(
                        map_from_entries(
                            collect_list(
                                struct(user_id, artist_count)
                            )
                        )
                    ) AS new_artists_discovered_count
              FROM discovered_artists_count
    """
