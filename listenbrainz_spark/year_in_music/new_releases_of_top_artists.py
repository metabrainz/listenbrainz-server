from datetime import datetime
from data.model.new_releases_stat import NewReleasesStat

import listenbrainz_spark
from listenbrainz_spark import path
from listenbrainz_spark.stats import run_query
from listenbrainz_spark.utils import get_listens_from_new_dump
from listenbrainz_spark.year_in_music.utils import setup_2021_listens


def get_new_releases_of_top_artists():
    setup_2021_listens()
    _get_all_releases().createOrReplaceTempView("release")
    run_query(_get_top_50_artists()).createOrReplaceTempView("top_50_artists")
    run_query(_get_2021_releases()).createOrReplaceTempView("releases_2021")
    new_releases = run_query(_get_new_releases_of_top_artists()).toLocalIterator()
    for entry in new_releases:
        data = entry.asDict(recursive=True)
        yield NewReleasesStat(
            type="new_releases_of_top_artists",
            user_name=data["user_name"],
            data=data["new_releases"]
        ).dict(exclude_none=True)


def _get_all_releases():
    return listenbrainz_spark.sql_context.read.json(path.MUSICBRAINZ_RELEASE_DUMP_JSON_FILE)


def _get_top_50_artists():
    return """
        WITH intermediate_table as (
            SELECT user_name
                 , artist_name
                 , artist_credit_mbids
                 , count(*) as listen_count
              FROM listens_2021
             WHERE artist_credit_mbids IS NOT NULL  
          GROUP BY user_name
                 , artist_name
                 , artist_credit_mbids
        ), intermediate_table_2 AS (
            SELECT user_name
             , artist_name
             , artist_credit_mbids
             , listen_count
             , row_number() OVER(PARTITION BY user_name ORDER BY listen_count DESC) AS row_number
             FROM intermediate_table
        )
        SELECT user_name
             , artist_name
             , artist_credit_mbids
             , listen_count
          FROM intermediate_table_2
         WHERE row_number <= 50         
    """


def _get_2021_releases():
    return """
        WITH intermediate_table AS (
            SELECT title
                 , id
                 , explode(`artist-credit`) AS ac
                 , `release-group`.`first-release-date` AS first_release_date
                 , `release-group`.`primary-type` AS type
              FROM release
             WHERE substr(`release-group`.`first-release-date`, 1, 4) = '2021'
        )
        SELECT title
             , id AS release_id
             , first_release_date
             , type
             , collect_list(ac.artist.name) AS artist_credit_names
             , collect_list(ac.artist.id) AS artist_credit_mbids 
          FROM intermediate_table
      GROUP BY title
             , id
             , first_release_date
             , type
    """


def _get_new_releases_of_top_artists():
    return """
        SELECT user_name
             , collect_list(
                    struct(
                       title
                     , release_id
                     , first_release_date
                     , type
                     , releases_2021.artist_credit_mbids
                     , releases_2021.artist_credit_names
                    )
               ) AS new_releases
          FROM releases_2021
          JOIN top_50_artists 
            ON cardinality(array_intersect(releases_2021.artist_credit_mbids, top_50_artists.artist_credit_mbids)) > 0
      GROUP BY user_name     
    """
