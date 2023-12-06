from datetime import datetime, date, time

from listenbrainz_spark.stats import run_query
from listenbrainz_spark.utils import get_listens_from_dump


def setup_listens_for_year(year):
    start = datetime(year, 1, 1)
    end = datetime.combine(date(year, 12, 31), time.max)
    listens = get_listens_from_dump(start, end)
    listens.createOrReplaceTempView("listens_of_year")


def create_tracks_of_the_year(year):
    end = datetime.combine(date(year, 12, 31), time.max)
    listens = get_listens_from_dump(end=end)
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
    """
    run_query(query).createOrReplaceTempView("tracks_of_year")
