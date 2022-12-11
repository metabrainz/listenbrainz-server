from more_itertools import chunked

from listenbrainz_spark.year_in_music.utils import setup_listens_for_year, setup_all_releases
from listenbrainz_spark.stats import run_query

USERS_PER_MESSAGE = 1000


def get_most_listened_year(year):
    setup_listens_for_year(year)
    setup_all_releases()
    data = run_query(_get_releases_with_date()).collect()
    for entries in chunked(data, USERS_PER_MESSAGE):
        yield {
            "type": "year_in_music_most_listened_year",
            "year": year,
            "data": [e.asDict(recursive=True) for e in entries]
        }


def _get_releases_with_date():
    return """
        WITH release_date AS (
            SELECT title
                 , id AS release_mbid
                 , int(substr(`release-group`.`first-release-date`, 1, 4)) AS year
              FROM release
             WHERE substr(`release-group`.`first-release-date`, 1, 4) != '????'
               AND substr(`release-group`.`first-release-date`, 1, 4) != ''
        ), listen_year AS (
        SELECT user_id
             , collect_list(release_date.release_mbid) AS release_mbids
             , release_date.year
             , count(*) AS listen_count
          FROM listens_of_year l
          JOIN release_date
            ON l.release_mbid = release_date.release_mbid
      GROUP BY user_id
             , release_date.year
        )
        SELECT user_id
             , map_from_entries(
                     collect_list(
                         struct(year, listen_count)
                     )
               ) AS data
          FROM listen_year
      GROUP BY user_id
    """
