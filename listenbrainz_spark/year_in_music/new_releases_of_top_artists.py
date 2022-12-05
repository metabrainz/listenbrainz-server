from data.model.new_releases_stat import NewReleasesStat

from listenbrainz_spark.stats import run_query
from listenbrainz_spark.year_in_music.utils import setup_listens_for_year, setup_all_releases


def get_new_releases_of_top_artists(year):
    setup_listens_for_year(year)
    setup_all_releases()
    run_query(_get_top_50_artists()).createOrReplaceTempView("top_50_artists")
    run_query(_get_releases_for_year(year)).createOrReplaceTempView("releases_of_year")
    new_releases = run_query(_get_new_releases_of_top_artists()).toLocalIterator()
    for entry in new_releases:
        data = entry.asDict(recursive=True)
        yield NewReleasesStat(
            type="new_releases_of_top_artists",
            year=year,
            user_id=data["user_id"],
            data=data["new_releases"]
        ).dict(exclude_none=True)


def _get_top_50_artists():
    return """
        WITH intermediate_table as (
            SELECT user_id
                 , artist_name
                 , artist_credit_mbids
                 , count(*) as listen_count
              FROM listens_of_year
             WHERE artist_credit_mbids IS NOT NULL
          GROUP BY user_id
                 , artist_name
                 , artist_credit_mbids
        ), intermediate_table_2 AS (
            SELECT user_id
             , artist_name
             , artist_credit_mbids
             , listen_count
             , row_number() OVER(PARTITION BY user_id ORDER BY listen_count DESC) AS row_number
             FROM intermediate_table
        )
        SELECT user_id
             , artist_name
             , artist_credit_mbids
             , listen_count
          FROM intermediate_table_2
         WHERE row_number <= 50
    """


def _get_releases_for_year(year):
    return f"""
        WITH intermediate_table AS (
            SELECT title
                 , id
                 , explode(`artist-credit`) AS ac
                 , `release-group`.`first-release-date` AS first_release_date
                 , `release-group`.`primary-type` AS type
              FROM release
             WHERE substr(`release-group`.`first-release-date`, 1, 4) = '{year}'
        )
        SELECT title
             , id AS release_mbid
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
        SELECT user_id
             , collect_set(
                    struct(
                       title
                     , release_mbid
                     , first_release_date
                     , type
                     , releases_of_year.artist_credit_mbids
                     , releases_of_year.artist_credit_names
                    )
               ) AS new_releases
          FROM releases_of_year
          JOIN top_50_artists
            ON cardinality(array_intersect(releases_of_year.artist_credit_mbids, top_50_artists.artist_credit_mbids)) > 0
      GROUP BY user_id
    """
