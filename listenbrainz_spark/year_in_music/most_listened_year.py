from more_itertools import chunked

from listenbrainz_spark.path import RELEASE_GROUP_METADATA_CACHE_DATAFRAME
from listenbrainz_spark.postgres import create_release_metadata_cache
from listenbrainz_spark.utils import read_files_from_HDFS
from listenbrainz_spark.year_in_music.utils import setup_listens_for_year
from listenbrainz_spark.stats import run_query

USERS_PER_MESSAGE = 1000


def get_most_listened_year(year):
    setup_listens_for_year(year)

    create_release_metadata_cache()
    read_files_from_HDFS(RELEASE_GROUP_METADATA_CACHE_DATAFRAME).createOrReplaceTempView("releases_all")

    data = run_query(_get_releases_with_date()).collect()
    for entries in chunked(data, USERS_PER_MESSAGE):
        yield {
            "type": "year_in_music_most_listened_year",
            "year": year,
            "data": [e.asDict(recursive=True) for e in entries]
        }


def _get_releases_with_date():
    return """
        WITH listen_year AS (
        SELECT user_id
             , rel.first_release_date_year AS year
             , count(*) AS listen_count
          FROM listens_of_year l
          JOIN releases_all rel
            ON l.release_mbid = rel.release_mbid
      GROUP BY user_id
             , rel.first_release_date_year
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
